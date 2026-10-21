import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Text } from 'react-native';
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
      {__DEV__ && process.env.EXPO_PUBLIC_NATIVE_ACCEPTANCE_OBSERVER === '1' ? (
        <Text
          accessibilityLabel={`NATIVE-BUILD ${process.env.EXPO_PUBLIC_NATIVE_BUILD_SOURCE ?? 'missing'}`}
          pointerEvents="none"
          style={{
            position: 'absolute',
            top: 32,
            left: 0,
            fontSize: 2,
            lineHeight: 4,
            zIndex: 10000,
          }}
        >
          {`NATIVE-BUILD ${process.env.EXPO_PUBLIC_NATIVE_BUILD_SOURCE ?? 'missing'}`}
        </Text>
      ) : null}
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
