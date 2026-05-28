// esbuild's `loader: { '.md': 'text' }` injects markdown files as default-export strings.
declare module '*.md' {
  const content: string;
  export default content;
}
