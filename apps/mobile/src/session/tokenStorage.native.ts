import * as SecureStore from 'expo-secure-store';
import type { TokenStorage } from './storage';
const key = 'goutou.development.session.v1';
export function createPlatformTokenStorage(): TokenStorage {
  return {
    read: () => SecureStore.getItemAsync(key),
    write: (token) =>
      SecureStore.setItemAsync(key, token, {
        keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      }),
    clear: () => SecureStore.deleteItemAsync(key),
  };
}
