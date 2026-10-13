import { writeFileSync } from 'node:fs';
import { listSessions, newSessionPath, type Message } from './session.js';
import type { AgentConfig } from './config.js';

export type CommandContext = { config: AgentConfig; messages: Message[]; sessionPath: string; reset: () => void; totalTokens: { input: number; output: number } };
export async function dispatch(line: string, ctx: CommandContext): Promise<boolean> {
  const [command, ...rest] = line.trim().split(/\s+/); const arg = rest.join(' ');
  if (command === '/help') { console.log('/model [modelo]  /new  /session  /export [arquivo]  /help  /quit'); return true; }
  if (command === '/model') { if (arg) ctx.config.model = arg; console.log(`Modelo: ${ctx.config.model}`); return true; }
  if (command === '/new') { ctx.messages.length = 0; ctx.reset(); console.log('Nova sessão iniciada.'); return true; }
  if (command === '/session') { console.log(`Sessão: ${ctx.sessionPath}\nMensagens: ${ctx.messages.length}\nTokens: ${ctx.totalTokens.input} entrada / ${ctx.totalTokens.output} saída`); return true; }
  if (command === '/export') { const path = arg || `session-${Date.now()}.md`; writeFileSync(path, ctx.messages.map((m) => `## ${m.role}\n\n${m.content}`).join('\n\n---\n\n')); console.log(`Exportado para ${path}`); return true; }
  if (command === '/sessions') { console.log(listSessions(ctx.config.sessionDir).join('\n') || 'Nenhuma sessão.'); return true; }
  return false;
}
