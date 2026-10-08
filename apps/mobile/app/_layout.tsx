import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import { demoSource } from '../src/data/demoSource';
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
        <DataSourceProvider source={demoSource}>
          <NavigationShell />
        </DataSourceProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
