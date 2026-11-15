import { router } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Naming } from '@/lib/api';
import { fonts, useColors, useLayout } from '@/lib/theme';

type Props = {
  namings: Naming[];
  /** column: 데스크톱 왼쪽 칸, row: 휴대폰·태블릿에서 입력창 아래 가로 한 줄 */
  variant: 'column' | 'row';
  /** 이름 화면에서: 지금 보고 있는 이름. 굵게 보이고, 다른 이름을 누르면 화면을 쌓지 않고 바꿔 끼운다 */
  currentId?: string;
  /** column에서 위쪽 여백. 옆 본문의 첫 줄과 높이를 맞춘다 */
  topOffset?: number;
};

/** 이름만 모아 둔 곳. 최근에 쓴 이름이 먼저, 개수는 없다 (P4). 이름이 없으면 아무것도 보이지 않는다 */
export function NameIndex({ namings, variant, currentId, topOffset = 48 }: Props) {
  const c = useColors();
  const { name } = useLayout();
  if (namings.length === 0) return null;

  const open = (id: string) => {
    if (id === currentId) return;
    const href = { pathname: '/names/[id]', params: { id } } as const;
    // 이름에서 이름으로 옮겨 갈 때는 쌓지 않는다: 뒤로 한 번이면 쓰는 화면
    if (currentId) router.replace(href);
    else router.push(href);
  };

  const items = namings.map((n) => (
    <Pressable
      key={n.id}
      accessibilityRole="link"
      accessibilityState={{ selected: n.id === currentId }}
      accessibilityHint="이 이름의 기록 모아 보기"
      onPress={() => open(n.id)}
      hitSlop={6}
      style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
      {({ hovered }: { pressed: boolean; hovered?: boolean }) => (
        <Text
          numberOfLines={1}
          style={[
            styles.label,
            { color: c.ink, fontSize: name, fontFamily: fonts.sans },
            n.id === currentId && styles.current,
            hovered && n.id !== currentId && styles.hovered,
          ]}>
          {n.label}
        </Text>
      )}
    </Pressable>
  ));

  if (variant === 'column') {
    return (
      <View style={[styles.column, { paddingTop: topOffset }]} accessibilityLabel="이름">
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
  column: { flex: 1 },
  heading: { fontSize: 13, marginBottom: 14 },
  columnList: { gap: 12, paddingBottom: 24 },
  rowList: { gap: 18, paddingVertical: 6, alignItems: 'center' },
  rowHeading: { fontSize: 13 },
  label: { fontWeight: '500' },
  current: { fontWeight: '800' },
  hovered: { textDecorationLine: 'underline' },
});
