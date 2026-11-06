import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import { Platform } from 'react-native';

import { ApiError, createEntry, type NewEntry, type Source } from './api';
import type { ServerSettings } from './settings';

// 로컬 우선 저장 (develop_plan Step 4)
// 1. 입력 중인 내용은 타이핑할 때마다 draft로 저장
// 2. 저장 → UUID 생성 → outbox에 넣기 → 입력창 비우기
// 3. outbox를 서버로 전송. 성공하면 제거, 실패하면 남겨두고 나중에 재시도
// 서버 POST가 멱등이므로 재시도해도 중복이 생기지 않는다.

const DRAFT_KEY = 'zf:draft';
const OUTBOX_KEY = 'zf:outbox';

export const source: Source = Platform.OS === 'ios' || Platform.OS === 'android' ? Platform.OS : 'web';

export async function loadDraft(): Promise<string> {
  return (await AsyncStorage.getItem(DRAFT_KEY)) ?? '';
}

export async function saveDraft(text: string): Promise<void> {
  if (text) await AsyncStorage.setItem(DRAFT_KEY, text);
  else await AsyncStorage.removeItem(DRAFT_KEY);
}

export async function loadOutbox(): Promise<NewEntry[]> {
  const raw = await AsyncStorage.getItem(OUTBOX_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as NewEntry[];
  } catch {
    return [];
  }
}

async function writeOutbox(items: NewEntry[]): Promise<void> {
  await AsyncStorage.setItem(OUTBOX_KEY, JSON.stringify(items));
}

/** 시간대가 붙은 ISO 문자열 (예: 2026-11-06T14:00:00.000+09:00). 쓴 순간의 기기 시각. */
function nowWithOffset(): string {
  const d = new Date();
  const offsetMin = -d.getTimezoneOffset();
  const sign = offsetMin >= 0 ? '+' : '-';
  const abs = Math.abs(offsetMin);
  const pad = (n: number, w = 2) => String(n).padStart(w, '0');
  const local = new Date(d.getTime() + offsetMin * 60_000);
  return (
    `${local.getUTCFullYear()}-${pad(local.getUTCMonth() + 1)}-${pad(local.getUTCDate())}` +
    `T${pad(local.getUTCHours())}:${pad(local.getUTCMinutes())}:${pad(local.getUTCSeconds())}` +
    `.${pad(local.getUTCMilliseconds(), 3)}${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}

/** 기록을 outbox에 넣고 draft를 비운다. 서버 전송은 flush가 맡는다. */
export async function enqueue(content: string): Promise<NewEntry> {
  const entry: NewEntry = {
    id: Crypto.randomUUID(),
    content,
    source,
    written_at: nowWithOffset(),
  };
  const items = await loadOutbox();
  await writeOutbox([...items, entry]);
  await saveDraft('');
  return entry;
}

let flushing: Promise<FlushResult> | null = null;

export type FlushResult = { sent: number; remaining: number; error?: string };

/** outbox를 서버로 보낸다. 동시에 여러 번 불려도 한 번만 돈다. */
export function flushOutbox(settings: ServerSettings): Promise<FlushResult> {
  if (!flushing) {
    flushing = doFlush(settings).finally(() => {
      flushing = null;
    });
  }
  return flushing;
}

async function doFlush(settings: ServerSettings): Promise<FlushResult> {
  let sent = 0;
  let error: string | undefined;
  for (const entry of await loadOutbox()) {
    try {
      await createEntry(settings, entry);
      sent += 1;
      // 보낸 것만 제거한다. 그 사이 새로 들어온 기록은 남는다.
      await writeOutbox((await loadOutbox()).filter((e) => e.id !== entry.id));
    } catch (e) {
      error =
        e instanceof ApiError && e.status === 401
          ? '토큰이 맞지 않습니다. 설정을 확인하세요.'
          : '서버에 연결할 수 없습니다. 기록은 기기에 남아 있고 나중에 다시 보냅니다.';
      break; // 순서를 지키기 위해 여기서 멈추고 나중에 재시도
    }
  }
  return { sent, remaining: (await loadOutbox()).length, error };
}
