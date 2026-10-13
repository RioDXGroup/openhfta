import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { tool } from '@openrouter/agent/tool';
import { z } from 'zod';

export const openhftaAnalyzeTool = tool({
  name: 'openhfta_analyze',
  description: 'Executa a análise determinística do OpenHFTA pela API local e retorna métricas do padrão e diagnósticos geométricos do terreno, incluindo relevo, declives e linha de visada aproximada.',
  inputSchema: z.object({
    profilePath: z.string().describe('Caminho absoluto ou relativo para um arquivo .PRO'),
    frequency: z.string().describe('Frequência, por exemplo 20m ou 14.2'),
    heights: z.string().optional().describe('Alturas em metros separadas por espaço, por exemplo 10 ou 10 20'),
    antennaType: z.string().optional().describe('Tipo: Dipole, 2-Ele, 3-Ele, 4-Ele, 5-Ele, 6-Ele ou 8-Ele'),
  }),
  execute: async ({ profilePath, frequency, heights = '10', antennaType = 'Dipole' }) => {
    try {
      const candidates = [resolve(process.cwd(), profilePath), resolve(process.cwd(), '..', profilePath)];
      const resolvedProfile = candidates.find((candidate) => existsSync(candidate));
      if (!resolvedProfile) return { error: `Perfil não encontrado: ${profilePath}` };
      const form = new FormData();
      form.append('profile', new Blob([await readFile(resolvedProfile)]), resolvedProfile.split('/').pop() ?? 'profile.PRO');
      form.append('frequency', frequency);
      form.append('units', 'meters');
      form.append('heights', heights);
      form.append('antenna_type', antennaType);
      const response = await fetch(`${process.env.AGENT_API_URL ?? 'http://localhost:8000'}/api/analyze`, { method: 'POST', body: form });
      const body = await response.json() as Record<string, unknown>;
      if (!response.ok) return { error: body.detail ?? `API retornou HTTP ${response.status}` };
      return {
        domain: 'HF terrain elevation-pattern analysis (OpenHFTA)',
        input_units: 'meters',
        configuration: body.configuration,
        profile: body.profile,
        metrics: body.metrics,
        interpretation: body.interpretation,
      };
    } catch (error) { return { error: error instanceof Error ? error.message : String(error) }; }
  },
});
