import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { listEntries } from '@/lib/api';
import { loadSettings, normalizeUrl, saveSettings } from '@/lib/settings';
import { useColors } from '@/lib/theme';

// 한 번만 입력하는 화면: 서버 주소와 토큰
export default function SettingsScreen() {
  const c = useColors();
  const [serverUrl, setServerUrl] = useState('');
  const [token, setToken] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    loadSettings().then((s) => {
      if (s) {
        setServerUrl(s.serverUrl);
        setToken(s.token);
      } else if (Platform.OS === 'web' && !__DEV__) {
        // 배포된 웹은 API와 같은 주소에서 서빙된다 (ADR 0003). 토큰만 넣으면 된다.
        setServerUrl(window.location.origin);
      }
    });
  }, []);

  async function onSave() {
    const settings = { serverUrl: normalizeUrl(serverUrl), token: token.trim() };
    if (!/^https?:\/\//.test(settings.serverUrl) || !settings.token) {
      setMessage('서버 주소(http:// 또는 https://로 시작)와 토큰을 모두 입력하세요.');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await listEntries(settings);
    } catch {
      setBusy(false);
      setMessage('서버에 연결하지 못했습니다. 주소와 토큰을 확인하세요.');
      return;
    }
    await saveSettings(settings);
    setBusy(false);
    if (router.canGoBack()) router.back();
    else router.replace('/');
  }

  const inputStyle = [styles.input, { color: c.text, borderColor: c.border, backgroundColor: c.surface }];

  return (
    <ScrollView style={{ backgroundColor: c.bg }} contentContainerStyle={styles.container}>
      <View style={styles.field}>
        <Text style={[styles.label, { color: c.muted }]}>서버 주소</Text>
        <TextInput
          style={inputStyle}
          value={serverUrl}
          onChangeText={setServerUrl}
          placeholder="http://192.168.0.10:8000"
          placeholderTextColor={c.muted}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
      </View>
      <View style={styles.field}>
        <Text style={[styles.label, { color: c.muted }]}>토큰</Text>
        <TextInput
          style={inputStyle}
          value={token}
          onChangeText={setToken}
          placeholder=".env의 ZF_TOKEN"
          placeholderTextColor={c.muted}
          autoCapitalize="none"
          autoCorrect={false}
          secureTextEntry
        />
      </View>
      {message && <Text style={[styles.message, { color: c.warn }]}>{message}</Text>}
      <Pressable
        accessibilityRole="button"
        onPress={onSave}
        disabled={busy}
        style={({ pressed }) => [styles.button, { backgroundColor: c.accent, opacity: busy || pressed ? 0.6 : 1 }]}>
        <Text style={[styles.buttonText, { color: c.onAccent }]}>{busy ? '확인 중…' : '저장'}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16, maxWidth: 640, width: '100%', alignSelf: 'center' },
  field: { gap: 6 },
  label: { fontSize: 14 },
  input: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16 },
  message: { fontSize: 14 },
  button: { borderRadius: 8, paddingVertical: 12, alignItems: 'center' },
  buttonText: { fontSize: 16, fontWeight: '600' },
});
