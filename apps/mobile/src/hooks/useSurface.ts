import { useState } from 'react';
import type { DemoScenario, SurfaceId } from '../contracts/shell';
import { useDataSource } from '../data/DataSourceProvider';

export function useSurface(id: SurfaceId) {
  const source = useDataSource();
  const [scenario, setScenario] = useState<DemoScenario>('empty');
  return {
    state: source.readSurface(id, scenario),
    scenario,
    setScenario,
    retry: () => setScenario('empty'),
  };
}
