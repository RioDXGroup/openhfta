import { readFile } from 'node:fs/promises';
import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';

export const fileReadTool = tool({
  name: 'file_read',
  description: 'Lê um arquivo local de forma somente leitura, com limite de linhas.',
  inputSchema: z.object({ path: z.string(), offset: z.number().optional(), limit: z.number().optional() }),
  execute: async ({ path, offset = 1, limit = 2000 }) => {
    try {
      const lines = (await readFile(path, 'utf8')).split('\n');
      const start = Math.max(0, offset - 1);
      const end = Math.min(lines.length, start + Math.min(limit, 2000));
      return { content: lines.slice(start, end).join('\n'), totalLines: lines.length, truncated: end < lines.length, nextOffset: end + 1 };
    } catch (error) { return { error: error instanceof Error ? error.message : String(error) }; }
  },
});
