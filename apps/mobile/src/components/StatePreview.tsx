import { View } from 'react-native';
import type { DemoScenario, SurfaceState } from '../contracts/shell';
import { tokens } from '../theme/tokens';
import { EmptyState, ErrorState, LoadingState, PrimaryButton, SectionCard } from './ui';

const scenarios: readonly { id: DemoScenario; label: string }[] = [
  { id: 'empty', label: '空状态' },
  { id: 'loading', label: '加载状态' },
  { id: 'error', label: '错误状态' },
];
export function StatePreview({
  state,
  scenario,
  onSelect,
  onRetry,
  showEmpty = true,
}: {
  state: SurfaceState;
  scenario: DemoScenario;
  onSelect: (scenario: DemoScenario) => void;
  onRetry: () => void;
  showEmpty?: boolean;
}) {
  return (
    <>
      <SectionCard title="演示状态预览">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: tokens.space.sm }}>
          {scenarios.map((item) => (
            <PrimaryButton
              key={item.id}
              label={item.label}
              variant="quiet"
              selected={scenario === item.id}
              onPress={() => onSelect(item.id)}
            />
          ))}
        </View>
      </SectionCard>
      {state.status === 'loading' ? (
        <LoadingState />
      ) : state.status === 'error' ? (
        <ErrorState message={state.message} onRetry={onRetry} />
      ) : showEmpty ? (
        <EmptyState title={state.view.emptyTitle} description={state.view.emptyDescription} />
      ) : null}
    </>
  );
}
