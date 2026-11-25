import type { ServerSettings } from './settings';

export type Source = 'web' | 'ios' | 'android';

export type NewEntry = {
  id: string;
  content: string;
  source: Source;
  written_at: string;
  /** 이어 쓰기: 이 기록이 이어지는 옛 기록 id */
  continues?: string[];
};

/** 이어진 기록을 그 자리에서 보여주기 위한 최소한 */
export type EntryRef = { id: string; content: string; written_at: string };

/** 기록에 붙은 이름 (지금 이름) */
export type NamingRef = { id: string; label: string };

export type Entry = Omit<NewEntry, 'continues'> & {
  created_at: string;
  namings: NamingRef[];
  /** 이 기록이 이어 쓴 옛 기록 */
  continues: EntryRef[];
  /** 이 기록에 이어 쓴 새 기록 */
  continued_by: EntryRef[];
};

/** 이름의 변천. 오래된 것부터, 마지막이 지금 이름 */
export type NamingVersion = { label: string; created_at: string };

export type Naming = NamingRef & { created_at: string; versions: NamingVersion[] };

export type NamingDetail = Naming & { entries: Entry[] };

export type EntryPage = { items: Entry[]; next_cursor: string | null };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(settings: ServerSettings, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${settings.serverUrl}/api${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${settings.token}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // 본문이 JSON이 아니면 상태 코드만
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function listEntries(settings: ServerSettings, cursor?: string | null): Promise<EntryPage> {
  const qs = cursor ? `?cursor=${encodeURIComponent(cursor)}` : '';
  return request(settings, `/entries${qs}`);
}

/** 멱등: 같은 id로 다시 보내도 서버에는 하나만 저장된다. */
export function createEntry(settings: ServerSettings, entry: NewEntry): Promise<Entry> {
  return request(settings, '/entries', { method: 'POST', body: JSON.stringify(entry) });
}

// ---- 이름 (Step 7). 이름 붙이기는 서버에 바로 반영한다 (오프라인이면 안내만) ----

export function listNamings(settings: ServerSettings): Promise<Naming[]> {
  return request(settings, '/namings');
}

export function getNaming(settings: ServerSettings, namingId: string): Promise<NamingDetail> {
  return request(settings, `/namings/${namingId}`);
}

/** 같은 이름이 있으면 그 이름에, 없으면 새 이름을 만들어 붙인다. 붙은 뒤의 기록을 돌려준다. */
export function attachNaming(settings: ServerSettings, entryId: string, label: string): Promise<Entry> {
  return request(settings, `/entries/${entryId}/namings`, { method: 'POST', body: JSON.stringify({ label }) });
}

export function detachNaming(settings: ServerSettings, entryId: string, namingId: string): Promise<Entry> {
  return request(settings, `/entries/${entryId}/namings/${namingId}`, { method: 'DELETE' });
}

/** 이름 바꾸기. 덮어쓰지 않고 새 버전이 쌓인다. 다른 이름과 겹치면 409. */
export function renameNaming(settings: ServerSettings, namingId: string, label: string): Promise<Naming> {
  return request(settings, `/namings/${namingId}/versions`, { method: 'POST', body: JSON.stringify({ label }) });
}

// ---- 이어지는 기록 (Step 8 검색 계층). AI가 글을 만들지 않고, 의미가 가까운 옛 기록을 옆에 놓을 뿐이다 ----

/** 점수는 기록끼리의 거리일 뿐, 화면에 보여주지 않는다 (P1, P4) */
export type RelatedEntry = { entry: Entry; similarity: number; recency: number; shared_naming: boolean; score: number };

/** 이 기록보다 먼저 쓴 기록 중 의미가 가까운 것. 없으면 빈 목록 (P3) */
export function getRelated(settings: ServerSettings, entryId: string, limit = 3): Promise<RelatedEntry[]> {
  return request(settings, `/entries/${entryId}/context?limit=${limit}`);
}

/** 이름 관련 실패를 짧은 안내로 */
export function namingErrorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 409) return '이미 있는 이름이에요.';
    if (e.status === 401) return '토큰이 맞지 않아요. 설정을 확인해 주세요.';
    if (e.status === 422) return '이름은 1~80자로 적어 주세요.';
    return e.message;
  }
  return '연결이 끊겨 있어요. 연결되면 다시 해 주세요.';
}
