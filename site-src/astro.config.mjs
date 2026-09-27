import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://hirethomas-inc.github.io',
  output: 'static',
  build: { format: 'file' },
  vite: { plugins: [tailwindcss()] },
});
