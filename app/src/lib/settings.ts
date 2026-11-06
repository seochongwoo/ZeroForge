import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

// 서버 주소와 토큰. 앱은 토큰을 secure-store에, 웹은 브라우저 저장소에 둔다.
// 혼자 쓰는 도구라 웹은 일단 이걸로 충분하다 (develop_plan Step 3-2).

export type ServerSettings = { serverUrl: string; token: string };

const URL_KEY = 'zf:serverUrl';
const TOKEN_KEY = 'zf.token';

async function getToken(): Promise<string | null> {
  if (Platform.OS === 'web') return AsyncStorage.getItem(TOKEN_KEY);
  return SecureStore.getItemAsync(TOKEN_KEY);
}

async function setToken(token: string): Promise<void> {
  if (Platform.OS === 'web') return AsyncStorage.setItem(TOKEN_KEY, token);
  return SecureStore.setItemAsync(TOKEN_KEY, token);
}

export function normalizeUrl(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

export async function loadSettings(): Promise<ServerSettings | null> {
  const [serverUrl, token] = await Promise.all([AsyncStorage.getItem(URL_KEY), getToken()]);
  if (!serverUrl || !token) return null;
  return { serverUrl, token };
}

export async function saveSettings({ serverUrl, token }: ServerSettings): Promise<void> {
  await Promise.all([AsyncStorage.setItem(URL_KEY, normalizeUrl(serverUrl)), setToken(token.trim())]);
}
