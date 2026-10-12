import { createNativeSseObserver } from './nativeSseObserverCore';
export { createNativeSseObserver } from './nativeSseObserverCore';

// Node contract tests and Web never load React Native or activate diagnostics.
export const nativeSseObserver = createNativeSseObserver(false);
