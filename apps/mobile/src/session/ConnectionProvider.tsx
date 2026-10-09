import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  useSyncExternalStore,
  type PropsWithChildren,
} from 'react';
import { AppState } from 'react-native';
import { useRouter } from 'expo-router';
import { randomUUID } from 'expo-crypto';
import { DevelopmentSession } from './developmentSession';
import { createPlatformTokenStorage } from './tokenStorage';
import { ApiTransport } from '../api/transport';
import { ResourceController } from '../data/resourceController';
import { DataSourceProvider } from '../data/DataSourceProvider';
import { demoSource } from '../data/demoSource';
import { connectedSource } from '../data/connectedSource';
import { AgentChatController } from '../data/agentChatController';
import { streamFetch } from '../api/streamFetch';

export interface Connection {
  session: DevelopmentSession;
  resources: ResourceController;
  chat: AgentChatController;
}
export function createConnection(baseURL: string, localDevelopment: boolean): Connection {
  const session = new DevelopmentSession(createPlatformTokenStorage());
  const transport = new ApiTransport(
    baseURL,
    session,
    fetch,
    12_000,
    localDevelopment,
    true,
    streamFetch,
  );
  return {
    session,
    resources: new ResourceController(transport, session, randomUUID),
    chat: new AgentChatController(transport, session, randomUUID),
  };
}
const Context = createContext<Connection | null>(null);
export const useConnection = () => useContext(Context);
export function useSessionView(connection: Connection) {
  return useSyncExternalStore(
    connection.session.subscribe,
    connection.session.snapshot,
    connection.session.snapshot,
  );
}
export function useResourceView(connection: Connection) {
  return useSyncExternalStore(
    connection.resources.subscribe,
    connection.resources.snapshot,
    connection.resources.snapshot,
  );
}
export function ConnectionProvider({
  children,
  connection: injected,
}: PropsWithChildren<{ connection?: Connection }>) {
  const [connection] = useState(
    () =>
      injected ??
      createConnection(
        process.env.EXPO_PUBLIC_API_BASE_URL ??
          (__DEV__ ? 'http://127.0.0.1:8000' : 'https://localhost:8000'),
        __DEV__,
      ),
  );
  const session = useSessionView(connection);
  const router = useRouter();
  const navigationEpoch = useRef(session.epoch);
  useEffect(() => {
    if (navigationEpoch.current !== session.epoch) {
      navigationEpoch.current = session.epoch;
      // Drop stacked owner URLs as well as in-memory selections on identity reset.
      if (router.canDismiss()) router.dismissAll();
      router.replace('/settings');
    }
  }, [router, session.epoch]);
  useEffect(() => {
    void connection.session.restore(connection.resources.probe);
    const subscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') connection.session.resume();
      else connection.chat.pause();
    });
    return () => subscription.remove();
  }, [connection]);
  return (
    <Context.Provider value={connection}>
      <DataSourceProvider
        key={`${session.mode}:${session.epoch}`}
        source={session.mode === 'demo' ? demoSource : connectedSource}
      >
        {children}
      </DataSourceProvider>
    </Context.Provider>
  );
}
