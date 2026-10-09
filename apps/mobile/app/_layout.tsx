import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ConnectionProvider } from '../src/session/ConnectionProvider';
import { ThemeProvider, useTheme } from '../src/theme/ThemeProvider';

function NavigationShell() {
  const { mode, colors } = useTheme();
  return (
    <>
      <StatusBar style={mode === 'dark' ? 'light' : 'dark'} />
      <Stack
        screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}
      />
    </>
  );
}
export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <ConnectionProvider>
          <NavigationShell />
        </ConnectionProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
