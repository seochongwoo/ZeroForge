import NetInfo from '@react-native-community/netinfo';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AppState,
  FlatList,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EntryItem, type Row } from '@/components/EntryItem';
import { NameIndex } from '@/components/NameIndex';
import { DateDivider, toStream } from '@/components/Stream';
import { listEntries, listNamings, type Entry, type Naming, type NewEntry } from '@/lib/api';
import { enqueue, flushOutbox, loadDraft, loadOutbox, saveDraft } from '@/lib/outbox';
import { loadSettings, type ServerSettings } from '@/lib/settings';
import { COLUMN_MAX, fonts, noOutline, useColors, useLayout } from '@/lib/theme';

export default function WriteScreen() {
  const c = useColors();
  const layout = useLayout();
  const inputRef = useRef<React.ComponentRef<typeof TextInput>>(null);
  const typedRef = useRef(false);
  const settingsRef = useRef<ServerSettings | null>(null);

  const [text, setText] = useState('');
  const [entries, setEntries] = useState<Entry[]>([]);
  const [pending, setPending] = useState<NewEntry[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [namings, setNamings] = useState<Naming[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const loadingMore = useRef(false);
  const expandedRef = useRef<string | null>(null);
  useEffect(() => {
    expandedRef.current = expandedId;
  }, [expandedId]);

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

  const reloadNamings = useCallback(async () => {
    const s = settingsRef.current;
    if (!s) return;
    try {
      setNamings(await listNamings(s));
    } catch {
      // 자동완성이 없어도 이름은 붙일 수 있다
    }
  }, []);

  const sync = useCallback(async () => {
    const s = settingsRef.current;
    if (!s) return;
    const result = await flushOutbox(s);
    setNotice(result.error ?? null);
    await refreshPending();
    await reloadFirstPage();
    await reloadNamings();
  }, [refreshPending, reloadFirstPage, reloadNamings]);

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
        // 설정 화면에서 돌아왔을 때도 바로 쓸 수 있게 (autoFocus는 첫 마운트에만 동작한다).
        // 기록을 펼쳐 이름을 붙이던 중이면(이름 화면에서 돌아온 경우) 그대로 둔다
        if (!expandedRef.current) inputRef.current?.focus();
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

  const replaceEntry = useCallback((updated: Entry) => {
    setEntries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
  }, []);

  // 서버 기록 + 아직 outbox에 있는 기록을 함께 보여준다
  const rows: Row[] = useMemo(() => {
    const serverIds = new Set(entries.map((e) => e.id));
    const local = pending.filter((p) => !serverIds.has(p.id)).map((p) => ({ ...p, pending: true }));
    const remote = entries.map((e) => ({ ...e, pending: false }));
    return [...local.reverse(), ...remote];
  }, [entries, pending]);

  const canSave = text.trim().length > 0;
  const stream = useMemo(() => toStream(rows), [rows]);

  // 웹: Ctrl/⌘ + Enter로 남기기 (§4-1)
  function onKeyPress(e: { nativeEvent: { key: string; ctrlKey?: boolean; metaKey?: boolean } }) {
    const { key, ctrlKey, metaKey } = e.nativeEvent;
    if (key === 'Enter' && (ctrlKey || metaKey)) {
      (e as unknown as { preventDefault?: () => void }).preventDefault?.();
      onSave();
    }
  }

  const writeBox = (
    <>
      <TextInput
        ref={inputRef}
        style={[
          styles.input,
          layout.body,
          noOutline,
          { color: c.ink, borderColor: focused ? c.muted : c.rule, backgroundColor: c.surface, fontFamily: fonts.serif },
        ]}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        value={text}
        onChangeText={onChangeText}
        onKeyPress={onKeyPress}
        // 무엇을 쓸지는 내가 정한다: 질문·안내 문구를 띄우지 않는다 (§4-1)
        accessibilityLabel="쓰기"
        multiline
        autoFocus
        textAlignVertical="top"
      />
      <View style={styles.actions}>
        {notice ? <Text style={[styles.notice, { color: c.muted }]}>{notice}</Text> : <View />}
        <Pressable
          accessibilityRole="button"
          accessibilityHint={Platform.OS === 'web' ? 'Ctrl 또는 ⌘ + Enter' : undefined}
          onPress={onSave}
          disabled={!canSave}
          style={({ pressed }) => [
            styles.button,
            { backgroundColor: c.ink, opacity: !canSave ? 0.3 : pressed ? 0.7 : 1 },
          ]}>
          <Text style={[styles.buttonText, { color: c.paper }]}>남기기</Text>
        </Pressable>
      </View>
    </>
  );

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: c.paper }]}>
      <View style={[styles.frame, layout.sideNames && styles.framePadded]}>
        {/* 768px 이상: 왼쪽 칸에 이름. 오른쪽은 Step 8의 여백 주석 자리라 지금은 비워 둔다 */}
        {layout.sideNames && (
          <View style={{ width: layout.asideWidth }}>
            <NameIndex namings={namings} variant="column" />
          </View>
        )}
        <View style={styles.column}>
          <View style={styles.topBar}>
            <Pressable accessibilityRole="button" onPress={() => router.push('/settings')} hitSlop={12}>
              <Text style={[styles.link, { color: c.muted }]}>설정</Text>
            </Pressable>
          </View>

          <FlatList
            style={styles.list}
            // 흐름 옆의 스크롤 막대는 숨긴다. 휠·터치 스크롤은 그대로
            showsVerticalScrollIndicator={false}
            data={stream}
            keyExtractor={(s) => s.key}
            ListHeaderComponent={
              <View>
                {writeBox}
                {!layout.sideNames && <NameIndex namings={namings} variant="row" />}
              </View>
            }
            onEndReached={loadMore}
            onEndReachedThreshold={0.5}
            keyboardShouldPersistTaps="handled"
            extraData={[expandedId, namings, layout.sideNames]}
            renderItem={({ item: s }) =>
              s.kind === 'date' ? (
                <DateDivider label={s.label} />
              ) : (
                <EntryItem
                  item={s.row}
                  expanded={expandedId === s.row.id}
                  onToggle={() => setExpandedId((cur) => (cur === s.row.id ? null : s.row.id))}
                  namings={namings}
                  getSettings={() => settingsRef.current}
                  onEntryChange={replaceEntry}
                  onNamingsChange={reloadNamings}
                />
              )
            }
          />
        </View>
        {/* 데스크톱에서만 오른쪽도 같은 너비로 비워 본문을 화면 가운데에 둔다. 태블릿 폭에서는 본문에 자리를 준다 */}
        {layout.desktop && <View style={{ width: layout.asideWidth }} />}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  frame: { flex: 1, flexDirection: 'row', justifyContent: 'center', gap: 32 },
  framePadded: { paddingLeft: 16 },
  column: { flex: 1, maxWidth: COLUMN_MAX, paddingHorizontal: 16 },
  topBar: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', paddingVertical: 12 },
  link: { fontSize: 13 },
  input: {
    minHeight: 120,
    maxHeight: 320,
    borderWidth: 1,
    borderRadius: 8,
    padding: 14,
  },
  actions: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12, paddingVertical: 10 },
  notice: { flex: 1, fontSize: 13 },
  button: { borderRadius: 6, paddingVertical: 9, paddingHorizontal: 20 },
  buttonText: { fontSize: 15, fontWeight: '600' },
  list: { flex: 1 },
});
