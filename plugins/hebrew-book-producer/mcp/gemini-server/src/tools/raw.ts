import { z } from 'zod';
import { generate, getDefaults } from '../gemini-client.js';
import { validation } from '../errors.js';

export const RawInput = z.object({
  system: z.string(),
  prompt: z.string().min(1),
  model: z.string().optional(),
  thinking_budget: z.number().int().optional(),
  temperature: z.number().optional(),
  max_output_tokens: z.number().int().positive().optional(),
});

export const RawOutput = z.object({
  text: z.string(),
  finish_reason: z.string(),
  usage: z.object({
    input_tokens: z.number(),
    output_tokens: z.number(),
    cached_tokens: z.number().optional(),
  }),
});

export async function runRaw(rawInput: unknown): Promise<z.infer<typeof RawOutput>> {
  const parsed = RawInput.safeParse(rawInput);
  if (!parsed.success) {
    throw validation('Invalid input to gemini_raw', { issues: parsed.error.issues }) as unknown as Error;
  }
  const input = parsed.data;
  const defaults = await getDefaults('raw');
  const model = input.model ?? defaults.model;
  const thinkingBudget = input.thinking_budget ?? defaults.thinking_budget;

  const result = await generate({
    system: input.system,
    user: input.prompt,
    model,
    thinking_budget: thinkingBudget,
    temperature: input.temperature,
    max_output_tokens: input.max_output_tokens,
  });

  return {
    text: result.text,
    finish_reason: result.finishReason,
    usage: result.usage,
  };
}
