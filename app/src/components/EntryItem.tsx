import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import {
  attachNaming,
  detachNaming,
  namingErrorMessage,
  type Entry,
  type Naming,
  type NamingRef,
  type NewEntry,
  type Source,
} from '@/lib/api';
import type { ServerSettings } from '@/lib/settings';
import { useColors } from '@/lib/theme';

export type Row = (Entry | (NewEntry & { namings?: NamingRef[] })) & { pending: boolean };

const SOURCE_LABEL: Record<Source, string> = { web: '웹', ios: 'iPhone', android: 'Android' };

export function formatTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

type Props = {
  item: Row;
  expanded: boolean;
  onToggle: () => void;
  /** 자동완성용. 이미 있는 이름 */
  namings: Naming[];
  getSettings: () => ServerSettings | null;
  /** 이름을 붙이거나 뗀 뒤의 기록 */
  onEntryChange: (entry: Entry) => void;
  /** 새 이름이 생겼을 수 있으니 이름 목록을 다시 읽으라는 신호 */
  onNamingsChange?: () => void;
};

/** 기록 하나. 누르면 그 자리에서 펼쳐지고, 펼친 곳에서 이름을 붙인다 (UI_CONCEPT §4-3, §4-4). */
export function EntryItem({ item, expanded, onToggle, namings, getSettings, onEntryChange, onNamingsChange }: Props) {
  const c = useColors();
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const attached = useMemo(() => item.namings ?? [], [item.namings]);

  // 이미 쓴 이름을 고를 수 있게. AI가 아니라 단순한 글자 비교다 (P2)
  const suggestions = useMemo(() => {
    const q = label.trim().toLowerCase();
    const taken = new Set(attached.map((n) => n.id));
    return namings
      .filter((n) => !taken.has(n.id) && (!q || n.label.toLowerCase().includes(q)))
      .filter((n) => n.label.toLowerCase() !== q)
      .slice(0, 5);
  }, [label, namings, attached]);

  async function run(action: (s: ServerSettings) => Promise<Entry>) {
    const s = getSettings();
    if (!s || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      onEntryChange(await action(s));
      onNamingsChange?.();
      return true;
    } catch (e) {
      setMessage(namingErrorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function attach(value: string) {
    const v = value.trim();
    if (!v) return;
    if (await run((s) => attachNaming(s, item.id, v))) setLabel('');
  }

  return (
    <View style={[styles.row, { borderColor: c.border }]}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        accessibilityHint={expanded ? '접기' : '펼쳐서 이름 붙이기'}
        onPress={onToggle}>
        <Text style={[styles.meta, { color: c.muted }]}>
          {formatTime(item.written_at)}
          {item.pending ? ' · 기기에만 저장됨' : ''}
          {expanded ? ` · ${SOURCE_LABEL[item.source]}` : ''}
        </Text>
        <Text style={[styles.content, { color: c.text }]}>{item.content}</Text>
      </Pressable>

      {attached.length > 0 && (
        <View style={styles.names}>
          {attached.map((n) => (
            <View key={n.id} style={styles.nameChip}>
              <Pressable
                accessibilityRole="link"
                accessibilityHint="이 이름의 기록 모아 보기"
                onPress={() => router.push({ pathname: '/names/[id]', params: { id: n.id } })}
                hitSlop={6}>
                <Text style={[styles.name, { color: c.text }]}>{n.label}</Text>
              </Pressable>
              {expanded && (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`${n.label} 떼기`}
                  onPress={() => run((s) => detachNaming(s, item.id, n.id))}
                  hitSlop={8}>
                  <Text style={[styles.detach, { color: c.muted }]}>×</Text>
                </Pressable>
              )}
            </View>
          ))}
        </View>
      )}

      {expanded &&
        (item.pending ? (
          <Text style={[styles.hint, { color: c.muted }]}>서버에 올라간 뒤에 이름을 붙일 수 있어요.</Text>
        ) : (
          <View style={styles.namer}>
            <TextInput
              style={[styles.nameInput, { color: c.text, borderColor: c.border, backgroundColor: c.surface }]}
              value={label}
              onChangeText={(v) => {
                setLabel(v);
                setMessage(null);
              }}
              onSubmitEditing={() => attach(label)}
              placeholder="이름 붙이기"
              placeholderTextColor={c.muted}
              accessibilityLabel="이 기록에 붙일 이름"
              maxLength={80}
              returnKeyType="done"
              editable={!busy}
            />
            {suggestions.length > 0 && (
              <View style={styles.suggestions}>
                {suggestions.map((n) => (
                  <Pressable
                    key={n.id}
                    accessibilityRole="button"
                    accessibilityLabel={`${n.label} 붙이기`}
                    onPress={() => attach(n.label)}
                    style={[styles.suggestion, { borderColor: c.border }]}>
                    <Text style={[styles.suggestionText, { color: c.muted }]}>{n.label}</Text>
                  </Pressable>
                ))}
              </View>
            )}
            {message && <Text style={[styles.hint, { color: c.warn }]}>{message}</Text>}
          </View>
        ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { paddingVertical: 14, borderTopWidth: StyleSheet.hairlineWidth, gap: 6 },
  meta: { fontSize: 12, marginBottom: 4 },
  content: { fontSize: 16, lineHeight: 24 },
  names: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  nameChip: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  name: { fontSize: 14, fontWeight: '500' },
  detach: { fontSize: 16, lineHeight: 18, paddingHorizontal: 2 },
  namer: { gap: 8, marginTop: 4 },
  nameInput: { borderWidth: 1, borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12, fontSize: 14 },
  suggestions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  suggestion: { borderWidth: 1, borderRadius: 999, paddingVertical: 4, paddingHorizontal: 10 },
  suggestionText: { fontSize: 13 },
  hint: { fontSize: 12 },
});
