import { z } from 'zod';
import { generate, getDefaults } from '../gemini-client.js';
import { getBundle, renderBundleMarkdown } from '../bundle.js';
import WRITE_SECTION_TEMPLATE from '../prompts/write-section.md';
import { validation } from '../errors.js';

export const SourceExcerpt = z.object({
  source_id: z.string(),
  author: z.string().optional(),
  year: z.union([z.string(), z.number()]).optional(),
  page: z.union([z.string(), z.number()]).optional(),
  excerpt: z.string(),
});
export type SourceExcerpt = z.infer<typeof SourceExcerpt>;

export const BannedTerm = z.object({
  term: z.string(),
  reason: z.string().optional(),
});
export type BannedTerm = z.infer<typeof BannedTerm>;

export const WriteSectionInput = z.object({
  section_brief: z.string().min(1),
  sources: z.array(SourceExcerpt),
  evidence_ownership: z.record(z.string(), z.unknown()),
  banned_terms: z.array(BannedTerm).default([]),
  target_language: z.string().min(1),
  prior_sections_summary: z.string().optional().default(''),
  citation_style: z.enum(['inline-parenthetical', 'chicago', 'mla', 'apa']),
});
export type WriteSectionInput = z.infer<typeof WriteSectionInput>;

export const SelfReviewScores = z.object({
  style: z.number(),
  language: z.number(),
  anti_ai: z.number(),
  repetition: z.number(),
  hebrew_grammar: z.number().optional(),
  language_purity: z.number().optional(),
});

export const ParagraphOut = z.object({
  text: z.string(),
  citations: z.array(z.string()),
  self_review_scores: SelfReviewScores,
});

export const WriteSectionOutput = z.object({
  paragraphs: z.array(ParagraphOut),
});

function fill(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, k: string) => vars[k] ?? '');
}

function extractJson(text: string): unknown {
  // Strip markdown fence if present.
  const fence = /```(?:json)?\s*\n([\s\S]*?)\n```/i.exec(text);
  const body = fence ? fence[1] : text;
  return JSON.parse(body);
}

export async function runWriteSection(rawInput: unknown): Promise<z.infer<typeof WriteSectionOutput>> {
  const parsed = WriteSectionInput.safeParse(rawInput);
  if (!parsed.success) {
    throw validation('Invalid input to gemini_write_section', { issues: parsed.error.issues }) as unknown as Error;
  }
  const input = parsed.data;
  const bundle = await getBundle(input.target_language);
  const defaults = await getDefaults('write_section');

  const system = fill(WRITE_SECTION_TEMPLATE, {
    calibration_bundle: renderBundleMarkdown(bundle),
    section_brief: input.section_brief,
    evidence_ownership: JSON.stringify(input.evidence_ownership, null, 2),
    sources: JSON.stringify(input.sources, null, 2),
    banned_terms: JSON.stringify(input.banned_terms, null, 2),
    prior_sections_summary: input.prior_sections_summary || '(no prior sections)',
    citation_style: input.citation_style,
  });

  const result = await generate({
    system,
    user: 'Draft the section now. Return JSON only.',
    model: defaults.model,
    thinking_budget: defaults.thinking_budget,
    response_mime_type: 'application/json',
  });

  let json: unknown;
  try {
    json = extractJson(result.text);
  } catch (e) {
    throw validation('Gemini returned non-JSON for write_section', {
      raw: result.text.slice(0, 1000),
      error: e instanceof Error ? e.message : String(e),
    }) as unknown as Error;
  }

  const out = WriteSectionOutput.safeParse(json);
  if (!out.success) {
    throw validation('Gemini write_section JSON failed schema validation', {
      issues: out.error.issues,
      raw: JSON.stringify(json).slice(0, 1000),
    }) as unknown as Error;
  }
  return out.data;
}

export const WRITE_SECTION_INPUT_SHAPE = {
  section_brief: { type: 'string' as const, description: 'Outline + brief for the section.' },
  sources: { type: 'array' as const, description: 'Source excerpts available for citation.' },
  evidence_ownership: {
    type: 'object' as const,
    description: 'Mapping of paragraph slot to allowed source_ids.',
  },
  banned_terms: { type: 'array' as const, description: 'Terms forbidden in the output.' },
  target_language: { type: 'string' as const, description: 'ISO/local language code, e.g. "hebrew".' },
  prior_sections_summary: { type: 'string' as const, description: 'Short summary of prior sections.' },
  citation_style: {
    type: 'string' as const,
    enum: ['inline-parenthetical', 'chicago', 'mla', 'apa'],
    description: 'Citation format.',
  },
};
