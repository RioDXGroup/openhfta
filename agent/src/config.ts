import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export interface DisplayConfig {
  toolDisplay: 'emoji' | 'grouped' | 'minimal' | 'hidden';
  reasoning: boolean;
  inputStyle: 'plain' | 'bordered' | 'block';
}

export interface AgentConfig {
  apiKey: string;
  model: string;
  apiUrl: string;
  systemPrompt: string;
  maxSteps: number;
  maxCost: number;
  sessionDir: string;
  display: DisplayConfig;
}

const defaults: AgentConfig = {
  apiKey: '',
  model: 'google/gemma-4-26b-a4b-it',
  apiUrl: 'http://localhost:8000',
  systemPrompt: [
    'Você é o analista do OpenHFTA, especializado em antenas e propagação de ondas curtas HF.',
    'O OpenHFTA calcula padrões de elevação de antenas HF sobre perfis de terreno; não é um analisador VHF/UHF de linha de visada.',
    'Explique resultados de antenas, frequências HF e perfis de terreno em português claro.',
    'Quando o usuário escrever 20m, trate como a banda de 20 metros, aproximadamente 14,2 MHz.',
    'Use a ferramenta openhfta_analyze quando o usuário pedir uma análise.',
    'Explique também o relevo, desníveis, declives e a linha de visada aproximada do terreno.',
    'Ao comparar alturas ou antenas, diga qual cenário é mais interessante para o objetivo e justifique com os dados do padrão e do terreno.',
    'Em HF, terreno bloqueando a linha de visada não significa automaticamente falha: considere difração habilitada, padrão, distância e limitações do modelo.',
    'Não invente medições: diferencie dados calculados, hipóteses e limitações.',
    'Para leigos, explique primeiro o significado prático e depois os números.',
    'O diretório de trabalho é {cwd}.',
  ].join('\n'),
  maxSteps: 8,
  maxCost: 0.25,
  sessionDir: '.sessions',
  display: { toolDisplay: 'grouped', reasoning: false, inputStyle: 'plain' },
};

export function loadConfig(overrides: Partial<AgentConfig> = {}): AgentConfig {
  let config = { ...defaults };
  const configPath = resolve('agent.config.json');
  if (existsSync(configPath)) {
    const file = JSON.parse(readFileSync(configPath, 'utf8')) as Partial<AgentConfig>;
    config = { ...config, ...file, display: { ...config.display, ...file.display } };
  }
  if (process.env.OPENROUTER_API_KEY) config.apiKey = process.env.OPENROUTER_API_KEY;
  if (process.env.AGENT_MODEL) config.model = process.env.AGENT_MODEL;
  if (process.env.AGENT_API_URL) config.apiUrl = process.env.AGENT_API_URL;
  if (process.env.AGENT_MAX_STEPS) config.maxSteps = Number(process.env.AGENT_MAX_STEPS);
  if (process.env.AGENT_MAX_COST) config.maxCost = Number(process.env.AGENT_MAX_COST);
  config = { ...config, ...overrides, display: { ...config.display, ...overrides.display } };
  if (!config.apiKey) throw new Error('OPENROUTER_API_KEY é obrigatório.');
  return config;
}
