import type { ServerSettings } from './settings';

export type Source = 'web' | 'ios' | 'android';

export type NewEntry = {
  id: string;
  content: string;
  source: Source;
  written_at: string;
};

export type Entry = NewEntry & { created_at: string };

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
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
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
