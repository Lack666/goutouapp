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
import { ImportController } from '../data/importController';
import { HistoryController } from '../data/historyController';
import { MemoryController } from '../data/memoryController';
import { ErasureController } from '../data/erasureController';

export interface Connection {
  session: DevelopmentSession;
  resources: ResourceController;
  chat: AgentChatController;
  imports: ImportController;
  history: HistoryController;
  memory: MemoryController;
  erasure: ErasureController;
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
    60_000,
    true,
    120_000,
    true,
    true,
  );
  const controllers = {
    session,
    resources: new ResourceController(transport, session, randomUUID),
    chat: new AgentChatController(transport, session, randomUUID),
    imports: new ImportController(transport, session),
    history: new HistoryController(transport, session),
    memory: new MemoryController(transport, session, randomUUID),
  };
  const erasure = new ErasureController(
    transport,
    session,
    randomUUID,
    (target) => {
      const history = controllers.history.snapshot();
      if (
        (target.domain === 'dataset' &&
          history.kind === 'relationship' &&
          history.parentId === target.relationship_id) ||
        (target.domain === 'conversation' &&
          history.kind === 'agent' &&
          history.parentId === target.target_id)
      )
        controllers.history.clear(history.kind);
      if (target.domain === 'conversation') {
        controllers.chat.invalidateConversation(target.target_id);
      } else if (
        controllers.imports.snapshot().receipt?.datasetId === target.target_id ||
        controllers.imports.snapshot().job?.id === target.target_id
      )
        controllers.imports.clear();
    },
    async (target) => {
      const epoch = session.epoch();
      if (target.domain === 'dataset' && target.relationship_id) {
        await controllers.history.open('relationship', target.relationship_id);
        if (epoch !== session.epoch()) return;
        if (
          controllers.history.snapshot().status !== 'ready' ||
          controllers.history
            .snapshot()
            .items.some(
              (item) => item.kind === 'relationship' && item.datasetId === target.target_id,
            )
        )
          throw new Error('History refresh failed');
      } else {
        controllers.resources.invalidateConversation(target.target_id);
        await controllers.resources.load('conversations');
        if (epoch !== session.epoch()) return;
        if (controllers.resources.snapshot().pages.conversations.status !== 'ready')
          throw new Error('Resource refresh failed');
      }
    },
  );
  return { ...controllers, erasure };
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
      if (state === 'active') {
        connection.session.resume();
        if (
          connection.session.snapshot().status === 'authenticated' &&
          connection.imports.snapshot().job
        )
          void connection.imports.inspect();
        void connection.history.resume();
        void connection.memory.resume();
      } else {
        connection.chat.pause();
        // Opening the system picker itself changes AppState; retain its guarded result.
        if (connection.imports.snapshot().upload !== 'selecting') connection.imports.pause();
        connection.history.pause();
        connection.memory.pause();
        connection.erasure.pause();
      }
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
