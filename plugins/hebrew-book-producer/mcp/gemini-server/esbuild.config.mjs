#!/usr/bin/env node
import { build } from 'esbuild';
import { mkdirSync } from 'node:fs';

mkdirSync('./dist', { recursive: true });

await build({
  entryPoints: ['./src/index.ts'],
  outfile: './dist/index.js',
  bundle: true,
  format: 'esm',
  platform: 'node',
  target: 'node20',
  minify: false,
  sourcemap: true,
  external: ['@modelcontextprotocol/sdk', '@google/genai'],
  loader: { '.md': 'text' },
  banner: {
    js: '#!/usr/bin/env node',
  },
});

console.log('Built dist/index.js');
