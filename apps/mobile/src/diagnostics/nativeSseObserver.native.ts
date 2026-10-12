import { Platform } from 'react-native';
import { createNativeSseObserver } from './nativeSseObserverCore';
export { createNativeSseObserver } from './nativeSseObserverCore';

// The flag has no effect in release builds or on iOS. It contains no secret.
export const nativeSseObserver = createNativeSseObserver(
  __DEV__ &&
    Platform.OS === 'android' &&
    process.env.EXPO_PUBLIC_NATIVE_ACCEPTANCE_OBSERVER === '1',
);
