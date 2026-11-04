/**
 * Calibration bundle loader for hebrew-book-producer.
 *
 * Reads:
 *   - AUTHOR_VOICE.md (project root) — author voice profile, including the
 *     `## Writer Configuration` block consumed by the orchestrator.
 *   - skills/hebrew-connectives/references/connectives-table.md (plugin) —
 *     the Hebrew connectives table; the equivalent of academic-writer's
 *     `words.md`. Rendered as the HEBREW CONNECTIVES section.
 *
 * Notes on what is intentionally NOT loaded:
 *   - No JSON style fingerprint: AUTHOR_VOICE.md in this plugin doesn't carry
 *     a fenced JSON fingerprint block. We leave `fingerprint = ''` so the
 *     bundle renderer simply omits the section.
 *   - No anti-AI markdown reference under skills/*\/references/: the canonical
 *     Hebrew anti-AI rules live in Trove's `hebrew-anti-ai-markers`
 *     chapter, cached by the SessionStart hook under `.ctx/`. The calling
 *     agent injects that material into the section/chapter brief; the MCP
 *     server doesn't bundle it.
 *
 * Cache lifetime == server process lifetime (~ Claude Code session).
 */
import { readFile } from 'node:fs/promises';
import * as path from 'node:path';
import { bundleLoadFailed, type StructuredError } from './errors.js';

export interface CalibrationBundle {
  voice: string;
  fingerprint: string;
  connectives: string;
  antiAi: string;
  rubric: string;
  targetLanguage: string;
}

const cache = new Map<string, CalibrationBundle>();

function projectDir(): string {
  return process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
}

function pluginRoot(): string {
  const fromEnv = process.env.CLAUDE_PLUGIN_ROOT;
  if (fromEnv) return fromEnv;
  // dist/index.js lives at <plugin>/mcp/gemini-server/dist/index.js
  // plugin root is three levels up.
  return path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..', '..');
}

async function readOptional(filePath: string): Promise<string> {
  try {
    return await readFile(filePath, 'utf8');
  } catch {
    return '';
  }
}

function lang(t: string): string {
  return (t || 'hebrew').toLowerCase().trim();
}

export async function getBundle(targetLanguage: string): Promise<CalibrationBundle> {
  const key = lang(targetLanguage);
  const hit = cache.get(key);
  if (hit) return hit;

  const project = projectDir();
  const plugin = pluginRoot();

  try {
    const [voice, connectives] = await Promise.all([
      readOptional(path.join(project, 'AUTHOR_VOICE.md')),
      readOptional(
        path.join(plugin, 'skills', 'hebrew-connectives', 'references', 'connectives-table.md'),
      ),
    ]);

    const bundle: CalibrationBundle = {
      voice,
      fingerprint: '',
      connectives,
      antiAi: '',
      rubric: '',
      targetLanguage: key,
    };
    cache.set(key, bundle);
    return bundle;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw bundleLoadFailed(`Failed to load calibration bundle for ${key}: ${message}`) as unknown as Error;
  }
}

/**
 * Render the calibration bundle into a single markdown block to inject into
 * the system prompt template.
 */
export function renderBundleMarkdown(b: CalibrationBundle): string {
  const sections: string[] = [];
  sections.push(`<!-- target_language: ${b.targetLanguage} -->`);
  if (b.voice) sections.push('## AUTHOR VOICE\n\n' + b.voice);
  if (b.fingerprint)
    sections.push('## STYLE FINGERPRINT (JSON)\n\n```json\n' + b.fingerprint + '\n```');
  if (b.rubric) sections.push('## STYLE FINGERPRINT RUBRIC\n\n' + b.rubric);
  if (b.connectives) sections.push('## HEBREW CONNECTIVES\n\n' + b.connectives);
  if (b.antiAi) sections.push('## ANTI-AI PATTERNS\n\n' + b.antiAi);
  return sections.join('\n\n---\n\n');
}

/** Test/escape-hatch: forget cached bundles. */
export function clearBundleCache(): void {
  cache.clear();
}

export function isStructuredError(e: unknown): e is StructuredError {
  return (
    typeof e === 'object' &&
    e !== null &&
    'code' in e &&
    typeof (e as { code: unknown }).code === 'string'
  );
}
