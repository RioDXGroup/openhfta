import { OpenRouter } from '@openrouter/agent';
import { stepCountIs, maxCost } from '@openrouter/agent/stop-conditions';
import type { AgentConfig } from './config.js';
import { tools } from './tools/index.js';

export type AgentEvent =
  | { type: 'text'; delta: string }
  | { type: 'tool_call'; name: string; callId: string; args: Record<string, unknown> }
  | { type: 'tool_result'; name: string; callId: string; output: string };

export async function runAgent(config: AgentConfig, input: string | Array<{ role: string; content: string }>, onEvent: (event: AgentEvent) => void) {
  const client = new OpenRouter({ apiKey: config.apiKey });
  const result = client.callModel({
    model: config.model,
    instructions: config.systemPrompt.replace('{cwd}', process.cwd()),
    input: input as never,
    tools,
    stopWhen: [stepCountIs(config.maxSteps), maxCost(config.maxCost)],
  });
  const textByItem = new Map<string, number>();
  const names = new Map<string, string>();
  for await (const item of result.getItemsStream()) {
    if (item.type === 'message') {
      const text = item.content?.filter((part): part is { type: 'output_text'; text: string } => 'text' in part).map((part) => part.text).join('') ?? '';
      const previous = textByItem.get(item.id) ?? 0;
      if (text.length > previous) { onEvent({ type: 'text', delta: text.slice(previous) }); textByItem.set(item.id, text.length); }
    } else if (item.type === 'function_call') {
      names.set(item.callId, item.name);
      if (item.status === 'completed') onEvent({ type: 'tool_call', name: item.name, callId: item.callId, args: JSON.parse(item.arguments || '{}') });
    } else if (item.type === 'function_call_output') {
      onEvent({ type: 'tool_result', name: names.get(item.callId) ?? 'unknown', callId: item.callId, output: typeof item.output === 'string' ? item.output : JSON.stringify(item.output) });
    }
  }
  const response = await result.getResponse();
  return { text: response.outputText ?? '', usage: response.usage };
}
