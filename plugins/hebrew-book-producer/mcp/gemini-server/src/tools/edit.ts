import { z } from 'zod';
import { generate, getDefaults } from '../gemini-client.js';
import { getBundle, renderBundleMarkdown } from '../bundle.js';
import EDIT_TEMPLATE from '../prompts/edit.md';
import { validation } from '../errors.js';

export const EditInput = z.object({
  existing_text: z.string().min(1),
  edit_instruction: z.string().min(1),
  target_language: z.string().min(1),
});

export const EditOutput = z.object({
  revised_text: z.string(),
});

function fill(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, k: string) => vars[k] ?? '');
}

function extractJson(text: string): unknown {
  const fence = /```(?:json)?\s*\n([\s\S]*?)\n```/i.exec(text);
  const body = fence ? fence[1] : text;
  return JSON.parse(body);
}

export async function runEdit(rawInput: unknown): Promise<z.infer<typeof EditOutput>> {
  const parsed = EditInput.safeParse(rawInput);
  if (!parsed.success) {
    throw validation('Invalid input to gemini_edit', { issues: parsed.error.issues }) as unknown as Error;
  }
  const input = parsed.data;
  const bundle = await getBundle(input.target_language);
  const defaults = await getDefaults('edit');

  const system = fill(EDIT_TEMPLATE, {
    calibration_bundle: renderBundleMarkdown(bundle),
    existing_text: input.existing_text,
    edit_instruction: input.edit_instruction,
  });

  const result = await generate({
    system,
    user: 'Apply the edit now. Return JSON only.',
    model: defaults.model,
    thinking_budget: defaults.thinking_budget,
    response_mime_type: 'application/json',
  });

  let json: unknown;
  try {
    json = extractJson(result.text);
  } catch (e) {
    throw validation('Gemini returned non-JSON for edit', {
      raw: result.text.slice(0, 1000),
      error: e instanceof Error ? e.message : String(e),
    }) as unknown as Error;
  }

  const out = EditOutput.safeParse(json);
  if (!out.success) {
    throw validation('Gemini edit JSON failed schema validation', {
      issues: out.error.issues,
    }) as unknown as Error;
  }
  return out.data;
}
