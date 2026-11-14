import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Naming } from '@/lib/api';
import { fonts, useColors, useLayout } from '@/lib/theme';

type Props = {
  namings: Naming[];
  /** column: 데스크톱 왼쪽 칸, row: 휴대폰·태블릿에서 입력창 아래 가로 한 줄 */
  variant: 'column' | 'row';
};

/** 이름만 모아 둔 곳. 최근에 쓴 이름이 먼저, 개수는 없다 (P4). 이름이 없으면 아무것도 보이지 않는다 */
export function NameIndex({ namings, variant }: Props) {
  const c = useColors();
  const { name } = useLayout();
  if (namings.length === 0) return null;

  const items = namings.map((n) => (
    <Pressable
      key={n.id}
      accessibilityRole="link"
      accessibilityHint="이 이름의 기록 모아 보기"
      onPress={() => router.push({ pathname: '/names/[id]', params: { id: n.id } })}
      hitSlop={6}
      style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
      {({ hovered }: { pressed: boolean; hovered?: boolean }) => (
        <Text
          numberOfLines={1}
          style={[
            styles.label,
            { color: c.ink, fontSize: name, fontFamily: fonts.sans },
            hovered && styles.hovered,
          ]}>
          {n.label}
        </Text>
      )}
    </Pressable>
  ));

  if (variant === 'column') {
    return (
      <View style={styles.column} accessibilityLabel="이름">
        <Text style={[styles.heading, { color: c.muted }]}>이름</Text>
        <ScrollView contentContainerStyle={styles.columnList} showsVerticalScrollIndicator={false}>
          {items}
        </ScrollView>
      </View>
    );
  }
  return (
    <View accessibilityLabel="이름">
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.rowList}
        keyboardShouldPersistTaps="handled">
        {/* 기록 아래에 붙은 이름과 헷갈리지 않게 작은 머리말 */}
        <Text style={[styles.rowHeading, { color: c.muted }]}>이름</Text>
        {items}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  // 설정 줄 높이만큼 내려서 입력창과 위쪽을 맞춘다
  column: { flex: 1, paddingTop: 48 },
  heading: { fontSize: 13, marginBottom: 14 },
  columnList: { gap: 12, paddingBottom: 24 },
  rowList: { gap: 18, paddingVertical: 6, alignItems: 'center' },
  rowHeading: { fontSize: 13 },
  label: { fontWeight: '500' },
  hovered: { textDecorationLine: 'underline' },
});
