import { createContext, useContext, useMemo, useState, type PropsWithChildren } from 'react';
import { useColorScheme } from 'react-native';
import { palettes, type ThemeColors } from './tokens';

export type ThemePreference = 'system' | 'light' | 'dark';
export function resolveTheme(preference: ThemePreference, system: string | null | undefined) {
  return preference === 'system' ? (system === 'dark' ? 'dark' : 'light') : preference;
}
interface ThemeContextValue {
  preference: ThemePreference;
  mode: 'light' | 'dark';
  colors: ThemeColors;
  setPreference: (preference: ThemePreference) => void;
}
const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: PropsWithChildren) {
  const system = useColorScheme();
  const [preference, setPreference] = useState<ThemePreference>('system');
  const mode = resolveTheme(preference, system);
  const value = useMemo(
    () => ({ preference, setPreference, mode, colors: palettes[mode] }),
    [mode, preference],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error('ThemeProvider is required');
  return value;
}
