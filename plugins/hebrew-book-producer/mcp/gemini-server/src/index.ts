/**
 * hebrew-book-producer Gemini MCP server.
 *
 * Routes the plugin's prose phases (drafting, synthesis, edits, calibration
 * samples) to Gemini. Claude Code spawns this server via the plugin manifest;
 * subagents inherit access to its tools.
 *
 * Five tools (uniform signatures with academic-writer; defaults differ):
 *   - gemini_write_section
 *   - gemini_synthesize
 *   - gemini_edit
 *   - gemini_calibrate_sample
 *   - gemini_raw
 *
 * Defaults to Gemini 2.5 Flash for write_section/edit/synthesize/calibrate;
 * Pro for raw.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

import { runWriteSection, WriteSectionInput } from './tools/write_section.js';
import { runSynthesize, SynthesizeInput } from './tools/synthesize.js';
import { runEdit, EditInput } from './tools/edit.js';
import { runCalibrateSample, CalibrateSampleInput } from './tools/calibrate_sample.js';
import { runRaw, RawInput } from './tools/raw.js';
import { isStructuredError } from './bundle.js';
import { resolveApiKey } from './gemini-client.js';
import { noCredentials, toToolResult, type StructuredError } from './errors.js';

function wrap<T>(
  run: (input: unknown) => Promise<T>,
): (input: unknown) => Promise<{
  content: Array<{ type: 'text'; text: string }>;
  isError?: boolean;
}> {
  return async (input: unknown) => {
    const key = await resolveApiKey();
    if (!key) return toToolResult(noCredentials());
    try {
      const result = await run(input);
      return {
        content: [
          { type: 'text', text: JSON.stringify(result) },
        ],
      };
    } catch (err) {
      if (isStructuredError(err)) return toToolResult(err);
      const fallback: StructuredError = {
        code: 'api_error',
        message: err instanceof Error ? err.message : String(err),
      };
      return toToolResult(fallback);
    }
  };
}

async function main(): Promise<void> {
  const server = new McpServer({
    name: 'hebrew-book-producer-gemini',
    version: '0.1.0',
  });

  server.registerTool(
    'gemini_write_section',
    {
      description:
        'Draft a full book section (all paragraphs) of Hebrew non-fiction prose via Gemini, with built-in self-review against author voice, Hebrew literary register, anti-AI markers, and burstiness/rhythm. Returns paragraphs with citations and self-review scores. The calling agent (book-writer) runs Sefaria source verification and the deterministic Hebrew-typography / niqqud / connectives skills after this tool returns.',
      inputSchema: WriteSectionInput.shape,
    },
    wrap(runWriteSection),
  );

  server.registerTool(
    'gemini_synthesize',
    {
      description:
        'Cross-chapter polish pass over a full Hebrew book draft. Improves transitions, removes cross-chapter repetition, smooths voice drift. Never touches Sefaria citations, primary-source quoted material, or footnote markers.',
      inputSchema: SynthesizeInput.shape,
    },
    wrap(runSynthesize),
  );

  server.registerTool(
    'gemini_edit',
    {
      description:
        'Apply a single edit instruction to an existing Hebrew passage in the author\'s voice. Preserves Sefaria citations and primary-source quotations verbatim. Used by literary-synthesizer, linguistic-editor, and proofreader to execute Claude-planned rewrites.',
      inputSchema: EditInput.shape,
    },
    wrap(runEdit),
  );

  server.registerTool(
    'gemini_calibrate_sample',
    {
      description:
        'Produce one calibration paragraph of Hebrew non-fiction prose from a topic brief for side-by-side voice comparison. Used by voice-calibrator before approving Gemini for a new language.',
      inputSchema: CalibrateSampleInput.shape,
    },
    wrap(runCalibrateSample),
  );

  server.registerTool(
    'gemini_raw',
    {
      description:
        'Escape-hatch tool: send an arbitrary system+prompt to Gemini. Bypasses the calibration bundle. Intended for one-off generations (e.g. lector-synthesizer\'s appraisal sections built from notes) or cross-plugin pings.',
      inputSchema: RawInput.shape,
    },
    wrap(runRaw),
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

void z;

main().catch((err: unknown) => {
  const msg = err instanceof Error ? err.message : String(err);
  process.stderr.write(`[gemini-mcp] fatal: ${msg}\n`);
  process.exit(1);
});
