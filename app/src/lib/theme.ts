import { Platform, useColorScheme, useWindowDimensions } from 'react-native';

// UI_CONCEPT.md §5 — 거의 흑백. 포인트 색은 불씨(ember) 하나, 서기의 주석과 열린 질문에만 쓴다.
// 빨강·초록 같은 성공/실패 색은 쓰지 않는다. 텍스트 색은 배경 대비 4.5:1 이상.
const palette = {
  light: {
    paper: '#F7F4EE', // 배경
    surface: '#FCFAF6', // 입력칸
    ink: '#1F1D1A', // 내 글, 지금 이름
    muted: '#6B655C', // 날짜, UI, 옛 이름
    rule: '#E3DED4', // 구분선
    ember: '#A84A14', // 서기의 주석, 질문 (Step 8)
  },
  dark: {
    paper: '#161513',
    surface: '#1D1C19',
    ink: '#E8E3DA',
    muted: '#9A948A',
    rule: '#2A2825',
    ember: '#E08A4F',
  },
};

export type Colors = typeof palette.light;

export function useColors(): Colors {
  return useColorScheme() === 'dark' ? palette.dark : palette.light;
}

// §5-1 타이포그래피. 웹폰트는 내려받지 않는다: 첫 화면(입력창)이 폰트를 기다리지 않게.
// 기기에 있는 명조/고딕을 쓴다 (Windows: 바탕/맑은 고딕, macOS·iOS: Apple 명조/산돌고딕).
export const fonts = {
  serif: Platform.select({
    web: "'Noto Serif KR', 'MaruBuri', 'Nanum Myeongjo', AppleMyungjo, Batang, serif",
    android: 'serif',
    default: undefined,
  }),
  sans: Platform.select({
    web: "Pretendard, -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', system-ui, sans-serif",
    default: undefined,
  }),
};

/** 폭 기준 (§3): 휴대폰 < 768 ≤ 태블릿 < 1024 ≤ 데스크톱 */
export function useLayout() {
  const { width } = useWindowDimensions();
  const desktop = width >= 1024;
  return {
    desktop,
    /** 이름 목록을 옆 칸에 둘 수 있는 폭. 태블릿 폭(창을 줄인 데스크톱 포함)부터. 그보다 좁으면 입력창 아래 한 줄 */
    sideNames: width >= 768,
    /** 옆 칸 너비: 데스크톱 200, 태블릿 폭 150 */
    asideWidth: desktop ? ASIDE_WIDTH : 150,
    /** 내 글 크기 (휴대폰 18 / 데스크톱 20, 행간 1.8) */
    body: desktop ? { fontSize: 20, lineHeight: 36 } : { fontSize: 18, lineHeight: 32 },
    /** 이름 크기 (14 / 15) */
    name: desktop ? 15 : 14,
  };
}

export const COLUMN_MAX = 640;

/** 웹 브라우저의 기본 포커스 테두리(파랑·노랑)를 끈다. 대신 입력칸 테두리 색으로 포커스를 보여준다 */
export const noOutline = Platform.OS === 'web' ? ({ outlineStyle: 'none' } as object) : null;
export const ASIDE_WIDTH = 200;

/** 마우스와 키보드를 쓰는 환경인가 (웹 데스크톱). 여기서만 입력칸에 커서를 먼저 둔다: 휴대폰에서는 키보드가 튀어나와 화면을 가린다 */
export const finePointer =
  Platform.OS === 'web' &&
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(hover: hover) and (pointer: fine)').matches;
