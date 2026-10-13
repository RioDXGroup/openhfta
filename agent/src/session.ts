import { appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

export type Message = { role: 'user' | 'assistant' | 'system'; content: string };
export function initSessionDir(dir: string) { if (!existsSync(dir)) mkdirSync(dir, { recursive: true }); }
export function saveMessage(path: string, message: Message) { appendFileSync(path, JSON.stringify({ timestamp: new Date().toISOString(), message }) + '\n'); }
export function loadSession(path: string): Message[] {
  if (!existsSync(path)) return [];
  return readFileSync(path, 'utf8').split('\n').filter(Boolean).flatMap((line) => {
    try { return [JSON.parse(line).message as Message]; } catch { return []; }
  });
}
export function newSessionPath(dir: string) { return join(dir, `${new Date().toISOString().replace(/[:.]/g, '-')}.jsonl`); }
export function listSessions(dir: string) { return existsSync(dir) ? readdirSync(dir).filter((name) => name.endsWith('.jsonl')).sort() : []; }
