import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { loadConfig } from './config.js';
import { runAgent } from './agent.js';
import { dispatch, type CommandContext } from './commands.js';
import { initSessionDir, loadSession, newSessionPath, saveMessage, type Message } from './session.js';
import { render } from './renderer.js';

async function main() {
  const config = loadConfig();
  initSessionDir(config.sessionDir);
  const ctx: CommandContext = { config, messages: [], sessionPath: newSessionPath(config.sessionDir), reset: () => { ctx.sessionPath = newSessionPath(config.sessionDir); }, totalTokens: { input: 0, output: 0 } };
  ctx.messages.push(...loadSession(ctx.sessionPath));
  const rl = createInterface({ input, output });
  console.log(`OpenHFTA Agent · ${config.model}`);
  console.log('Digite /help para comandos ou /quit para sair.\n');
  try {
    while (true) {
      const line = (await rl.question('> ')).trim();
      if (!line) continue;
      if (line === '/quit' || line === '/exit') break;
      if (line.startsWith('/')) { if (!(await dispatch(line, ctx))) console.log('Comando desconhecido. Use /help.'); continue; }
      const message: Message = { role: 'user', content: line };
      ctx.messages.push(message); saveMessage(ctx.sessionPath, message);
      try {
        const result = await runAgent(config, ctx.messages, render);
        const answer: Message = { role: 'assistant', content: result.text };
        ctx.messages.push(answer); saveMessage(ctx.sessionPath, answer); console.log();
        ctx.totalTokens.input += result.usage?.inputTokens ?? 0; ctx.totalTokens.output += result.usage?.outputTokens ?? 0;
      } catch (error) { console.error(`\nErro: ${error instanceof Error ? error.message : String(error)}`); }
    }
  } finally { rl.close(); }
}
main().catch((error) => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
