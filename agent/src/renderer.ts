import type { AgentEvent } from './agent.js';
const reset = '\x1b[0m'; const gray = '\x1b[90m'; const green = '\x1b[32m'; const bold = '\x1b[1m';
export function render(event: AgentEvent) {
  if (event.type === 'text') process.stdout.write(event.delta);
  if (event.type === 'tool_call') console.log(`\n${green}●${reset} ${bold}${event.name}${reset} ${gray}${JSON.stringify(event.args)}${reset}`);
  if (event.type === 'tool_result') console.log(`${gray}└ ${event.output.split('\n')[0].slice(0, 100)}${reset}`);
}
