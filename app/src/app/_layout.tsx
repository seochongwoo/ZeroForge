import { DarkTheme, DefaultTheme, ThemeProvider } from 'expo-router';
import { Stack } from 'expo-router/stack';
import { StatusBar } from 'expo-status-bar';
import { useColorScheme } from 'react-native';

export default function RootLayout() {
  const scheme = useColorScheme();
  return (
    <ThemeProvider value={scheme === 'dark' ? DarkTheme : DefaultTheme}>
      <StatusBar style="auto" />
      <Stack>
        {/* 첫 화면 = 입력창. 헤더도 없다 */}
        <Stack.Screen name="index" options={{ headerShown: false, title: 'ZeroForge' }} />
        <Stack.Screen name="settings" options={{ title: '설정' }} />
      </Stack>
    </ThemeProvider>
  );
}
