import NetInfo from '@react-native-community/netinfo';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AppState,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { listEntries, type Entry, type NewEntry } from '@/lib/api';
import { enqueue, flushOutbox, loadDraft, loadOutbox, saveDraft } from '@/lib/outbox';
import { loadSettings, type ServerSettings } from '@/lib/settings';
import { useColors } from '@/lib/theme';

type Row = (Entry | NewEntry) & { pending: boolean };

function formatTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function WriteScreen() {
  const c = useColors();
  const inputRef = useRef<React.ComponentRef<typeof TextInput>>(null);
  const typedRef = useRef(false);
  const settingsRef = useRef<ServerSettings | null>(null);

  const [text, setText] = useState('');
  const [entries, setEntries] = useState<Entry[]>([]);
  const [pending, setPending] = useState<NewEntry[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const loadingMore = useRef(false);

  // 작성 중이던 내용 복원. 이미 타이핑을 시작했다면 덮어쓰지 않는다.
  useEffect(() => {
    loadDraft().then((d) => {
      if (!typedRef.current && d) setText(d);
    });
  }, []);

  const refreshPending = useCallback(async () => setPending(await loadOutbox()), []);

  const reloadFirstPage = useCallback(async () => {
    const s = settingsRef.current;
    if (!s) return;
    try {
      const page = await listEntries(s);
      setEntries(page.items);
      setCursor(page.next_cursor);
    } catch {
      // 오프라인이어도 쓰기는 계속된다. 안내는 sync가 맡는다.
    }
  }, []);

  const sync = useCallback(async () => {
    const s = settingsRef.current;
    if (!s) return;
    const result = await flushOutbox(s);
    setNotice(result.error ?? null);
    await refreshPending();
    await reloadFirstPage();
  }, [refreshPending, reloadFirstPage]);

  // 설정 화면에서 돌아올 때마다 설정을 다시 읽는다
  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        await refreshPending();
        const s = await loadSettings();
        if (!active) return;
        settingsRef.current = s;
        if (!s) {
          router.push('/settings');
          return;
        }
        // 설정 화면에서 돌아왔을 때도 바로 쓸 수 있게 (autoFocus는 첫 마운트에만 동작한다)
        inputRef.current?.focus();
        await sync();
      })();
      return () => {
        active = false;
      };
    }, [refreshPending, sync]),
  );

  // 재시도 시점: 앱이 다시 열릴 때, 네트워크가 돌아왔을 때 (그리고 다음 저장 때)
  useEffect(() => {
    const appSub = AppState.addEventListener('change', (state) => {
      if (state === 'active') sync();
    });
    const netUnsub = NetInfo.addEventListener((state) => {
      if (state.isConnected) sync();
    });
    return () => {
      appSub.remove();
      netUnsub();
    };
  }, [sync]);

  function onChangeText(value: string) {
    typedRef.current = true;
    setText(value);
    saveDraft(value);
  }

  async function onSave() {
    if (!text.trim()) return;
    const content = text;
    setText('');
    await enqueue(content);
    await refreshPending();
    inputRef.current?.focus();
    sync();
  }

  async function loadMore() {
    const s = settingsRef.current;
    if (!s || !cursor || loadingMore.current) return;
    loadingMore.current = true;
    try {
      const page = await listEntries(s, cursor);
      setEntries((prev) => [...prev, ...page.items.filter((e) => !prev.some((p) => p.id === e.id))]);
      setCursor(page.next_cursor);
    } catch {
      // 다음 스크롤 때 다시 시도
    } finally {
      loadingMore.current = false;
    }
  }

  // 서버 기록 + 아직 outbox에 있는 기록을 함께 보여준다
  const rows: Row[] = useMemo(() => {
    const serverIds = new Set(entries.map((e) => e.id));
    const local = pending.filter((p) => !serverIds.has(p.id)).map((p) => ({ ...p, pending: true }));
    const remote = entries.map((e) => ({ ...e, pending: false }));
    return [...local.reverse(), ...remote];
  }, [entries, pending]);

  const canSave = text.trim().length > 0;

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: c.bg }]}>
      <View style={styles.column}>
        <View style={styles.topBar}>
          <Text style={[styles.brand, { color: c.muted }]}>ZeroForge</Text>
          <Pressable accessibilityRole="button" onPress={() => router.push('/settings')} hitSlop={12}>
            <Text style={[styles.link, { color: c.muted }]}>설정</Text>
          </Pressable>
        </View>

        <TextInput
          ref={inputRef}
          style={[styles.input, { color: c.text, borderColor: c.border, backgroundColor: c.surface }]}
          value={text}
          onChangeText={onChangeText}
          placeholder="지금 떠오르는 것을, 아무리 짧아도"
          placeholderTextColor={c.muted}
          multiline
          autoFocus
          textAlignVertical="top"
        />
        <View style={styles.actions}>
          {notice ? <Text style={[styles.notice, { color: c.warn }]}>{notice}</Text> : <View />}
          <Pressable
            accessibilityRole="button"
            onPress={onSave}
            disabled={!canSave}
            style={({ pressed }) => [
              styles.button,
              { backgroundColor: c.accent, opacity: !canSave ? 0.35 : pressed ? 0.7 : 1 },
            ]}>
            <Text style={[styles.buttonText, { color: c.onAccent }]}>저장</Text>
          </Pressable>
        </View>

        <FlatList
          style={styles.list}
          data={rows}
          keyExtractor={(r) => r.id}
          onEndReached={loadMore}
          onEndReachedThreshold={0.5}
          keyboardShouldPersistTaps="handled"
          renderItem={({ item }) => (
            <View style={[styles.row, { borderColor: c.border }]}>
              <Text style={[styles.meta, { color: c.muted }]}>
                {formatTime(item.written_at)}
                {item.pending ? ' · 기기에만 저장됨' : ''}
              </Text>
              <Text style={[styles.content, { color: c.text }]}>{item.content}</Text>
            </View>
          )}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  column: { flex: 1, width: '100%', maxWidth: 680, alignSelf: 'center', paddingHorizontal: 16 },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  brand: { fontSize: 14, letterSpacing: 0.5 },
  link: { fontSize: 14 },
  input: {
    minHeight: 120,
    maxHeight: 280,
    borderWidth: 1,
    borderRadius: 10,
    padding: 14,
    fontSize: 17,
    lineHeight: 26,
  },
  actions: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12, paddingVertical: 10 },
  notice: { flex: 1, fontSize: 13 },
  button: { borderRadius: 8, paddingVertical: 10, paddingHorizontal: 22 },
  buttonText: { fontSize: 16, fontWeight: '600' },
  list: { flex: 1 },
  row: { paddingVertical: 14, borderTopWidth: StyleSheet.hairlineWidth, gap: 4 },
  meta: { fontSize: 12 },
  content: { fontSize: 16, lineHeight: 24 },
});
