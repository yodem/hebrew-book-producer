import { z } from 'zod';
import { generate, getDefaults } from '../gemini-client.js';
import { getBundle, renderBundleMarkdown } from '../bundle.js';
import SYNTHESIZE_TEMPLATE from '../prompts/synthesize.md';
import { validation } from '../errors.js';

export const SynthesizeInput = z.object({
  full_draft: z.string().min(1),
  target_language: z.string().min(1),
});

export const SynthesizeOutput = z.object({
  revised_draft: z.string(),
  change_log: z.array(z.string()),
});

function fill(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, k: string) => vars[k] ?? '');
}

function extractJson(text: string): unknown {
  const fence = /```(?:json)?\s*\n([\s\S]*?)\n```/i.exec(text);
  const body = fence ? fence[1] : text;
  return JSON.parse(body);
}

export async function runSynthesize(rawInput: unknown): Promise<z.infer<typeof SynthesizeOutput>> {
  const parsed = SynthesizeInput.safeParse(rawInput);
  if (!parsed.success) {
    throw validation('Invalid input to gemini_synthesize', { issues: parsed.error.issues }) as unknown as Error;
  }
  const input = parsed.data;
  const bundle = await getBundle(input.target_language);
  const defaults = await getDefaults('synthesize');

  const system = fill(SYNTHESIZE_TEMPLATE, {
    calibration_bundle: renderBundleMarkdown(bundle),
    full_draft: input.full_draft,
  });

  const result = await generate({
    system,
    user: 'Synthesize now. Return JSON only.',
    model: defaults.model,
    thinking_budget: defaults.thinking_budget,
    response_mime_type: 'application/json',
  });

  let json: unknown;
  try {
    json = extractJson(result.text);
  } catch (e) {
    throw validation('Gemini returned non-JSON for synthesize', {
      raw: result.text.slice(0, 1000),
      error: e instanceof Error ? e.message : String(e),
    }) as unknown as Error;
  }

  const out = SynthesizeOutput.safeParse(json);
  if (!out.success) {
    throw validation('Gemini synthesize JSON failed schema validation', {
      issues: out.error.issues,
    }) as unknown as Error;
  }
  return out.data;
}
