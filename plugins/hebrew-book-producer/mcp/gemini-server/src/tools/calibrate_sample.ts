import { z } from 'zod';
import { generate, getDefaults } from '../gemini-client.js';
import { getBundle, renderBundleMarkdown } from '../bundle.js';
import { validation } from '../errors.js';

export const CalibrateSampleInput = z.object({
  topic_brief: z.string().min(1),
  target_language: z.string().min(1),
});

export const CalibrateSampleOutput = z.object({
  paragraph: z.string(),
});

const SYSTEM_HEADER = `You are producing a single calibration paragraph for a Humanities researcher's voice calibration gate. The orchestrator will compare your paragraph against a Claude-written paragraph side-by-side. Match the AUTHOR_VOICE and style fingerprint exactly. Do not include citations. One paragraph only — no headings, no commentary.`;

function extractJsonOrText(text: string): { paragraph: string } {
  const fence = /```(?:json)?\s*\n([\s\S]*?)\n```/i.exec(text);
  const body = fence ? fence[1] : text;
  try {
    const parsed: unknown = JSON.parse(body);
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'paragraph' in parsed &&
      typeof (parsed as { paragraph: unknown }).paragraph === 'string'
    ) {
      return { paragraph: (parsed as { paragraph: string }).paragraph };
    }
  } catch {
    // not JSON — treat the full text as the paragraph
  }
  return { paragraph: text.trim() };
}

export async function runCalibrateSample(rawInput: unknown): Promise<z.infer<typeof CalibrateSampleOutput>> {
  const parsed = CalibrateSampleInput.safeParse(rawInput);
  if (!parsed.success) {
    throw validation('Invalid input to gemini_calibrate_sample', { issues: parsed.error.issues }) as unknown as Error;
  }
  const input = parsed.data;
  const bundle = await getBundle(input.target_language);
  const defaults = await getDefaults('calibrate_sample');

  const system = [
    SYSTEM_HEADER,
    '## Calibration',
    renderBundleMarkdown(bundle),
  ].join('\n\n');

  const userPrompt = `Topic brief:\n\n${input.topic_brief}\n\nReturn JSON: {"paragraph": "..."}.`;

  const result = await generate({
    system,
    user: userPrompt,
    model: defaults.model,
    thinking_budget: defaults.thinking_budget,
    response_mime_type: 'application/json',
  });

  const parsedOut = extractJsonOrText(result.text);
  const out = CalibrateSampleOutput.safeParse(parsedOut);
  if (!out.success) {
    throw validation('Gemini calibrate_sample failed schema', {
      issues: out.error.issues,
    }) as unknown as Error;
  }
  return out.data;
}
