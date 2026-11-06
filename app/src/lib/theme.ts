import { useColorScheme } from 'react-native';

const palette = {
  light: {
    bg: '#fbfaf8',
    surface: '#ffffff',
    text: '#1c1b1a',
    muted: '#6f6b66',
    border: '#e4e1dc',
    accent: '#2f2d2a',
    onAccent: '#ffffff',
    warn: '#9a4b16',
  },
  dark: {
    bg: '#141413',
    surface: '#1d1c1b',
    text: '#eceae6',
    muted: '#9b968f',
    border: '#33312e',
    accent: '#eceae6',
    onAccent: '#141413',
    warn: '#e3a26f',
  },
};

export type Colors = typeof palette.light;

export function useColors(): Colors {
  return useColorScheme() === 'dark' ? palette.dark : palette.light;
}
