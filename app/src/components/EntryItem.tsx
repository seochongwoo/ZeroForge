import { router } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
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
import { finePointer, fonts, noOutline, useColors, useLayout } from '@/lib/theme';

export type Row = (Entry | (NewEntry & { namings?: NamingRef[] })) & {
  pending: boolean;
};

const SOURCE_LABEL: Record<Source, string> = {
  web: '웹',
  ios: 'iPhone',
  android: 'Android',
};

/** 시각은 기록을 펼쳤을 때만 (UI_CONCEPT §4-2) */
export function formatClock(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
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
  const layout = useLayout();
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const nameInputRef = useRef<React.ComponentRef<typeof TextInput>>(null);
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
    if (!s || busy) return false;
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
    // 고른 이름을 누르면 커서가 빠진다. 이어서 또 붙일 수 있게 되돌린다 (데스크톱만)
    if (finePointer) nameInputRef.current?.focus();
  }

  // 웹: Esc로 접기
  function onNameKeyPress(e: { nativeEvent: { key: string } }) {
    if (e.nativeEvent.key === 'Escape') onToggle();
  }

  const nameStyle = [styles.name, { color: c.ink, fontSize: layout.name, fontFamily: fonts.sans }];

  return (
    <View style={styles.row}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        accessibilityHint={expanded ? '접기' : '펼쳐서 이름 붙이기'}
        onPress={onToggle}>
        {expanded && (
          <Text style={[styles.meta, { color: c.muted }]}>
            {formatClock(item.written_at)} · {SOURCE_LABEL[item.source]}
          </Text>
        )}
        <Text style={[styles.content, layout.body, { color: c.ink, fontFamily: fonts.serif }]}>
          {item.pending && (
            // ○ = 아직 기기에만 있음. 경고색 없이 조용히 (§4-2)
            <Text style={{ color: c.muted }} accessibilityLabel="아직 기기에만 있음">
              {'○ '}
            </Text>
          )}
          {item.content}
        </Text>
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
                <Text style={nameStyle}>{n.label}</Text>
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
              ref={nameInputRef}
              // 펼치는 건 대개 이름을 붙이려는 것. 데스크톱에서는 바로 쓸 수 있게
              autoFocus={finePointer}
              onKeyPress={onNameKeyPress}
              // 붙인 뒤에도 커서를 그대로 둔다: 이름을 연달아 붙일 수 있게
              submitBehavior="submit"
              style={[
                styles.nameInput,
                noOutline,
                {
                  color: c.ink,
                  borderColor: focused ? c.muted : c.rule,
                  backgroundColor: c.surface,
                },
              ]}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              value={label}
              onChangeText={(v) => {
                setLabel(v);
                setMessage(null);
              }}
              onSubmitEditing={() => attach(label)}
              placeholder="이름"
              placeholderTextColor={c.muted}
              accessibilityLabel="이 기록에 붙일 이름"
              maxLength={80}
              returnKeyType="done"
            />
            {suggestions.length > 0 && (
              <View style={styles.suggestions}>
                {suggestions.map((n) => (
                  <Pressable
                    key={n.id}
                    accessibilityRole="button"
                    accessibilityLabel={`${n.label} 붙이기`}
                    onPress={() => attach(n.label)}
                    hitSlop={4}>
                    <Text style={[styles.suggestionText, { color: c.muted }]}>{n.label}</Text>
                  </Pressable>
                ))}
              </View>
            )}
            {message && <Text style={[styles.hint, { color: c.muted }]}>{message}</Text>}
          </View>
        ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { paddingVertical: 12, gap: 6 },
  meta: { fontSize: 13, marginBottom: 4 },
  content: {},
  names: { flexDirection: 'row', flexWrap: 'wrap', columnGap: 14, rowGap: 4 },
  nameChip: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  name: { fontWeight: '500' },
  detach: { fontSize: 16, lineHeight: 18, paddingHorizontal: 2 },
  namer: { gap: 8, marginTop: 4 },
  nameInput: {
    borderWidth: 1,
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    fontSize: 14,
  },
  suggestions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    columnGap: 14,
    rowGap: 6,
  },
  suggestionText: { fontSize: 14, textDecorationLine: 'underline' },
  hint: { fontSize: 13 },
});
