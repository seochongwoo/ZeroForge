import { StyleSheet, Text, View } from 'react-native';

import type { Row } from '@/components/EntryItem';
import { useColors } from '@/lib/theme';

const WEEKDAYS = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];

/** "11월 7일 토요일". 올해가 아니면 앞에 연도. 담담하게 날짜만 (UI_CONCEPT §4-2) */
export function dateLabel(iso: string): string {
  const d = new Date(iso);
  const year = d.getFullYear() === new Date().getFullYear() ? '' : `${d.getFullYear()}년 `;
  return `${year}${d.getMonth() + 1}월 ${d.getDate()}일 ${WEEKDAYS[d.getDay()]}`;
}

function dayKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

export type StreamItem = { kind: 'date'; key: string; label: string } | { kind: 'entry'; key: string; row: Row };

/** 최신순 기록 사이에 날짜 구분선을 끼운다. 개수나 빈 날 표시는 없다 (P4) */
export function toStream(rows: Row[]): StreamItem[] {
  const out: StreamItem[] = [];
  let prev = '';
  for (const row of rows) {
    const day = dayKey(row.written_at);
    if (day !== prev) {
      out.push({ kind: 'date', key: `date-${day}`, label: dateLabel(row.written_at) });
      prev = day;
    }
    out.push({ kind: 'entry', key: row.id, row });
  }
  return out;
}

export function DateDivider({ label }: { label: string }) {
  const c = useColors();
  return (
    <View style={styles.divider} accessibilityRole="header">
      <Text style={[styles.label, { color: c.muted }]}>{label}</Text>
      <View style={[styles.line, { backgroundColor: c.rule }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  divider: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingTop: 28, paddingBottom: 4 },
  label: { fontSize: 13 },
  line: { flex: 1, height: StyleSheet.hairlineWidth },
});
