import { createContext, useContext, type PropsWithChildren } from 'react';
import type { ShellDataSource } from '../contracts/shell';

const DataSourceContext = createContext<ShellDataSource | null>(null);
export function DataSourceProvider({
  source,
  children,
}: PropsWithChildren<{ source: ShellDataSource }>) {
  return <DataSourceContext.Provider value={source}>{children}</DataSourceContext.Provider>;
}
export function useDataSource() {
  const source = useContext(DataSourceContext);
  if (!source) throw new Error('DataSourceProvider is required');
  return source;
}
