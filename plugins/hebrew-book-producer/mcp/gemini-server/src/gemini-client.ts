/**
 * Thin wrapper around @google/genai that:
 *   - resolves API key from env (GOOGLE_API_KEY preferred, GEMINI_API_KEY
 *     fallback for back-compat with the legacy Python script) or
 *     `.book-producer/secrets.json`
 *   - resolves per-tool model defaults from `.book-producer/profile.json >
 *     gemini.models` (optional override)
 *   - splits unified `thinking_budget` into 2.5's `thinkingBudget` integer vs
 *     3.x's `thinkingLevel` categorical value
 *   - retries with exponential backoff on 5xx / 429 / network errors
 *
 * Defaults differ from academic-writer: hebrew-book-producer uses Gemini 2.5
 * Flash for write_section and edit (the legacy Python script default, and the
 * documented model in the plugin description).
 */
import { GoogleGenAI } from '@google/genai';
import { readFile } from 'node:fs/promises';
import * as path from 'node:path';
import {
  apiError,
  isRetryable,
  noCredentials,
  transient,
  type StructuredError,
} from './errors.js';

export type ToolName =
  | 'write_section'
  | 'synthesize'
  | 'edit'
  | 'calibrate_sample'
  | 'raw';

export interface ModelDefaults {
  model: string;
  thinking_budget: number;
}

const SPEC_DEFAULTS: Record<ToolName, ModelDefaults> = {
  write_section: { model: 'gemini-2.5-flash', thinking_budget: 4096 },
  synthesize: { model: 'gemini-2.5-flash', thinking_budget: 2048 },
  edit: { model: 'gemini-2.5-flash', thinking_budget: 2048 },
  calibrate_sample: { model: 'gemini-2.5-flash', thinking_budget: 1024 },
  raw: { model: 'gemini-2.5-pro', thinking_budget: -1 },
};

const RETRY_MAX_ATTEMPTS = 3;
const RETRY_BASE_MS = 1000;
const RETRY_FACTOR = 2;

let cachedKey: string | undefined | null = undefined; // undefined = uncached, null = checked-and-missing
let cachedDefaults: Partial<Record<ToolName, ModelDefaults>> | null = null;
let cachedClient: GoogleGenAI | null = null;

function projectDir(): string {
  return process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
}

async function readSecretsKey(): Promise<string | undefined> {
  const secretsPath = path.join(projectDir(), '.book-producer', 'secrets.json');
  try {
    const raw = await readFile(secretsPath, 'utf8');
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed === 'object' && parsed !== null) {
      const obj = parsed as Record<string, unknown>;
      const candidates = ['google_api_key', 'gemini_api_key', 'GOOGLE_API_KEY', 'GEMINI_API_KEY'];
      for (const k of candidates) {
        const v = obj[k];
        if (typeof v === 'string' && v.trim().length > 0) return v.trim();
      }
    }
  } catch {
    // missing/unreadable/invalid JSON — treat as no key
  }
  return undefined;
}

export async function resolveApiKey(): Promise<string | undefined> {
  if (cachedKey === null) return undefined;
  if (typeof cachedKey === 'string') return cachedKey;
  const google = (process.env.GOOGLE_API_KEY ?? '').trim();
  if (google) {
    cachedKey = google;
    return google;
  }
  const gemini = (process.env.GEMINI_API_KEY ?? '').trim();
  if (gemini) {
    cachedKey = gemini;
    return gemini;
  }
  const fromSecrets = await readSecretsKey();
  if (fromSecrets) {
    cachedKey = fromSecrets;
    return fromSecrets;
  }
  cachedKey = null;
  return undefined;
}

async function loadProfileModelDefaults(): Promise<Partial<Record<ToolName, ModelDefaults>>> {
  if (cachedDefaults) return cachedDefaults;
  const profilePath = path.join(projectDir(), '.book-producer', 'profile.json');
  try {
    const raw = await readFile(profilePath, 'utf8');
    try {
      const parsed: unknown = JSON.parse(raw);
      const extracted = extractGeminiModels(parsed);
      if (extracted) {
        cachedDefaults = extracted;
        return extracted;
      }
    } catch {
      // not valid JSON — ignore
    }
  } catch {
    // no profile.json — fall through to spec defaults
  }
  cachedDefaults = {};
  return cachedDefaults;
}

function extractGeminiModels(parsed: unknown): Partial<Record<ToolName, ModelDefaults>> | null {
  if (typeof parsed !== 'object' || parsed === null) return null;
  const root = parsed as Record<string, unknown>;
  const gemini = root['gemini'];
  const models =
    gemini && typeof gemini === 'object' && 'models' in (gemini as object)
      ? (gemini as { models: unknown }).models
      : root['gemini.models'];
  if (typeof models !== 'object' || models === null) return null;
  const out: Partial<Record<ToolName, ModelDefaults>> = {};
  for (const tool of Object.keys(SPEC_DEFAULTS) as ToolName[]) {
    const entry = (models as Record<string, unknown>)[tool];
    if (typeof entry === 'object' && entry !== null) {
      const e = entry as Record<string, unknown>;
      const model = typeof e['model'] === 'string' ? (e['model'] as string) : undefined;
      const tb =
        typeof e['thinking_budget'] === 'number'
          ? (e['thinking_budget'] as number)
          : typeof e['thinkingBudget'] === 'number'
            ? (e['thinkingBudget'] as number)
            : undefined;
      if (model || tb !== undefined) {
        out[tool] = {
          model: model ?? SPEC_DEFAULTS[tool].model,
          thinking_budget: tb ?? SPEC_DEFAULTS[tool].thinking_budget,
        };
      }
    }
  }
  return Object.keys(out).length > 0 ? out : null;
}

export async function getDefaults(tool: ToolName): Promise<ModelDefaults> {
  const overrides = await loadProfileModelDefaults();
  return overrides[tool] ?? SPEC_DEFAULTS[tool];
}

function thinkingLevelFromBudget(budget: number): 'low' | 'medium' | 'high' {
  if (budget < 0) return 'high';
  if (budget < 512) return 'low';
  if (budget < 4096) return 'medium';
  return 'high';
}

function isGemini3(model: string): boolean {
  return /^gemini-3(\.|-)/i.test(model);
}

interface ThinkingConfig {
  thinkingBudget?: number;
  thinkingLevel?: 'minimal' | 'low' | 'medium' | 'high';
}

export function buildThinkingConfig(model: string, budget: number): ThinkingConfig {
  if (isGemini3(model)) {
    if (budget < 0) return { thinkingLevel: 'high' };
    return { thinkingLevel: thinkingLevelFromBudget(budget) };
  }
  // 2.5 family — pass thinkingBudget as integer (-1 = dynamic)
  return { thinkingBudget: budget };
}

async function getClient(): Promise<GoogleGenAI> {
  if (cachedClient) return cachedClient;
  const key = await resolveApiKey();
  if (!key) throw noCredentials() as unknown as Error;
  cachedClient = new GoogleGenAI({ apiKey: key });
  return cachedClient;
}

export interface GenerateArgs {
  system: string;
  user: string;
  model: string;
  thinking_budget: number;
  temperature?: number;
  max_output_tokens?: number;
  response_mime_type?: string;
}

export interface GenerateResult {
  text: string;
  finishReason: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    cached_tokens?: number;
  };
}

interface MaybeHttpError {
  status?: number;
  statusCode?: number;
  code?: string;
  message?: string;
}

function readHttpStatus(e: unknown): number | undefined {
  if (typeof e !== 'object' || e === null) return undefined;
  const h = e as MaybeHttpError;
  return typeof h.status === 'number' ? h.status : typeof h.statusCode === 'number' ? h.statusCode : undefined;
}

function readErrCode(e: unknown): string | undefined {
  if (typeof e !== 'object' || e === null) return undefined;
  const h = e as MaybeHttpError;
  return typeof h.code === 'string' ? h.code : undefined;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((res) => setTimeout(res, ms));
}

export async function generate(args: GenerateArgs): Promise<GenerateResult> {
  const client = await getClient();
  const thinkingConfig = buildThinkingConfig(args.model, args.thinking_budget);

  const config: Record<string, unknown> = {
    systemInstruction: args.system,
    temperature: args.temperature ?? 1.0,
    thinkingConfig,
  };
  if (typeof args.max_output_tokens === 'number') {
    // Gemini 2.5 counts thinking tokens against maxOutputTokens. Tight budgets
    // can leave zero room for visible text. Ensure at least ~1024 tokens of
    // output headroom beyond the thinking budget.
    const tb = args.thinking_budget;
    const minHeadroom = 1024;
    const minRequired = tb > 0 ? tb + minHeadroom : minHeadroom;
    config['maxOutputTokens'] = Math.max(args.max_output_tokens, minRequired);
  }
  if (args.response_mime_type) {
    config['responseMimeType'] = args.response_mime_type;
  }

  let attempt = 0;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    attempt++;
    try {
      const resp = await client.models.generateContent({
        model: args.model,
        contents: args.user,
        config,
      });
      return normalizeResponse(resp);
    } catch (err) {
      const status = readHttpStatus(err);
      const code = readErrCode(err);
      const retryable = isRetryable(status, code);
      if (retryable && attempt < RETRY_MAX_ATTEMPTS) {
        const delay = RETRY_BASE_MS * Math.pow(RETRY_FACTOR, attempt - 1);
        await sleep(delay);
        continue;
      }
      const message = err instanceof Error ? err.message : String(err);
      const structured: StructuredError = retryable
        ? transient(`Gemini call failed after ${attempt} attempts: ${message}`, {
            status,
            code,
          })
        : apiError(`Gemini call failed: ${message}`, { status, code });
      throw structured as unknown as Error;
    }
  }
}

interface GenAiUsage {
  promptTokenCount?: number;
  candidatesTokenCount?: number;
  cachedContentTokenCount?: number;
}
interface GenAiCandidate {
  finishReason?: string;
}
interface GenAiResponse {
  text?: string;
  usageMetadata?: GenAiUsage;
  candidates?: GenAiCandidate[];
}

function normalizeResponse(resp: unknown): GenerateResult {
  const r = resp as GenAiResponse;
  const text = typeof r.text === 'string' ? r.text : '';
  const usage = r.usageMetadata ?? {};
  const finishReason =
    Array.isArray(r.candidates) && r.candidates[0]?.finishReason
      ? (r.candidates[0].finishReason as string)
      : 'STOP';
  return {
    text,
    finishReason,
    usage: {
      input_tokens: usage.promptTokenCount ?? 0,
      output_tokens: usage.candidatesTokenCount ?? 0,
      cached_tokens: usage.cachedContentTokenCount,
    },
  };
}
