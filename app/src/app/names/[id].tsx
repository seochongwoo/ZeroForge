import { Stack, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useMemo, useRef, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { EntryItem } from '@/components/EntryItem';
import { DateDivider, toStream } from '@/components/Stream';
import {
  getNaming,
  listNamings,
  namingErrorMessage,
  renameNaming,
  type Entry,
  type Naming,
  type NamingDetail,
} from '@/lib/api';
import { loadSettings, type ServerSettings } from '@/lib/settings';
import { COLUMN_MAX, fonts, noOutline, useColors } from '@/lib/theme';

/** 이름이 바뀐 날: "11월 7일" (올해가 아니면 연도도) */
function formatDate(iso: string): string {
  const d = new Date(iso);
  const year = d.getFullYear() === new Date().getFullYear() ? '' : `${d.getFullYear()}년 `;
  return `${year}${d.getMonth() + 1}월 ${d.getDate()}일`;
}

/** 이름별 모아 보기: 이름의 변천 + 이 이름이 붙은 기록 (UI_CONCEPT §4-4) */
export default function NamingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const c = useColors();
  const settingsRef = useRef<ServerSettings | null>(null);

  const [naming, setNaming] = useState<NamingDetail | null>(null);
  const [namings, setNamings] = useState<Naming[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const s = settingsRef.current;
    if (!s || !id) return;
    try {
      const [detail, all] = await Promise.all([getNaming(s, id), listNamings(s)]);
      setNaming(detail);
      setNamings(all);
      setMessage(null);
    } catch (e) {
      setMessage(namingErrorMessage(e));
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      (async () => {
        settingsRef.current = await loadSettings();
        await load();
      })();
    }, [load]),
  );

  async function onRename() {
    const s = settingsRef.current;
    const label = draft.trim();
    if (!s || !naming || !label || busy) return;
    if (label === naming.label) {
      setRenaming(false);
      return;
    }
    setBusy(true);
    try {
      await renameNaming(s, naming.id, label);
      setRenaming(false);
      await load();
    } catch (e) {
      setMessage(namingErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  // 이 화면에서 이름을 떼면 목록에서도 빠진다
  const onEntryChange = useCallback(
    (updated: Entry) => {
      setNaming((prev) => {
        if (!prev) return prev;
        const stillHere = updated.namings.some((n) => n.id === prev.id);
        return {
          ...prev,
          entries: stillHere
            ? prev.entries.map((e) => (e.id === updated.id ? updated : e))
            : prev.entries.filter((e) => e.id !== updated.id),
        };
      });
    },
    [],
  );

  const stream = useMemo(() => toStream((naming?.entries ?? []).map((e) => ({ ...e, pending: false }))), [naming]);

  const versions = naming?.versions ?? [];
  const older = versions.slice(0, -1);
  const current = versions[versions.length - 1];

  const header = naming ? (
    <View style={styles.header}>
      {/* 이름의 변천: 옛 이름은 지우지 않고 줄을 긋는다 */}
      <View style={styles.history} accessibilityLabel={`이름의 변천: ${versions.map((v) => v.label).join(', ')}`}>
        {older.map((v, i) => (
          <View key={`${v.created_at}-${i}`} style={styles.version}>
            <Text style={[styles.oldLabel, { color: c.muted, fontFamily: fonts.sans }]}>{v.label}</Text>
            <Text style={[styles.date, { color: c.muted }]}>{formatDate(v.created_at)}</Text>
          </View>
        ))}
        {current && (
          <View style={styles.version}>
            <Text style={[styles.currentLabel, { color: c.ink, fontFamily: fonts.sans }]}>{current.label}</Text>
            <Text style={[styles.date, { color: c.muted }]}>{formatDate(current.created_at)}</Text>
          </View>
        )}
      </View>

      {renaming ? (
        <View style={styles.renameRow}>
          <TextInput
            style={[styles.input, noOutline, { color: c.ink, borderColor: c.muted, backgroundColor: c.surface }]}
            value={draft}
            onChangeText={(v) => {
              setDraft(v);
              setMessage(null);
            }}
            onSubmitEditing={onRename}
            autoFocus
            maxLength={80}
            accessibilityLabel="새 이름"
            returnKeyType="done"
          />
          <Pressable accessibilityRole="button" onPress={onRename} disabled={busy} hitSlop={8}>
            <Text style={[styles.action, { color: c.ink }]}>바꾸기</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => setRenaming(false)} hitSlop={8}>
            <Text style={[styles.action, { color: c.muted }]}>그만두기</Text>
          </Pressable>
        </View>
      ) : (
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            setDraft(naming.label);
            setRenaming(true);
          }}
          hitSlop={8}>
          <Text style={[styles.action, { color: c.muted }]}>이름 바꾸기</Text>
        </Pressable>
      )}
      {renaming && (
        <Text style={[styles.hint, { color: c.muted }]}>지금 이름은 지워지지 않고 변천으로 남아요.</Text>
      )}
      {message && <Text style={[styles.hint, { color: c.muted }]}>{message}</Text>}
    </View>
  ) : undefined;

  return (
    <View style={[styles.screen, { backgroundColor: c.paper }]}>
      <Stack.Screen options={{ title: naming?.label ?? '이름' }} />
      <View style={styles.column}>
        {!naming && message && <Text style={[styles.hint, { color: c.muted, marginTop: 16 }]}>{message}</Text>}
        <FlatList
          data={stream}
          keyExtractor={(s) => s.key}
          ListHeaderComponent={header}
          keyboardShouldPersistTaps="handled"
          extraData={[expandedId, namings]}
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
                onEntryChange={onEntryChange}
                onNamingsChange={load}
              />
            )
          }
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  column: { flex: 1, width: '100%', maxWidth: COLUMN_MAX, alignSelf: 'center', paddingHorizontal: 16 },
  header: { paddingVertical: 20, gap: 12 },
  history: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-end', columnGap: 16, rowGap: 8 },
  version: { gap: 2 },
  oldLabel: { fontSize: 16, textDecorationLine: 'line-through' },
  currentLabel: { fontSize: 22, fontWeight: '600' },
  date: { fontSize: 13 },
  renameRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  input: { flex: 1, borderWidth: 1, borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12, fontSize: 15 },
  action: { fontSize: 14 },
  hint: { fontSize: 13 },
});
