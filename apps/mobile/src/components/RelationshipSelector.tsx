import { View } from 'react-native';
import type { RelationshipProfileViewModel } from '../contracts/relationship';
import { BodyText, PrimaryButton, SectionCard } from './ui';

export function RelationshipSelector({
  profiles,
  selected,
  onSelect,
  connected = false,
  disabled = false,
}: {
  profiles: readonly RelationshipProfileViewModel[];
  selected: string | null;
  onSelect: (id: string) => void;
  connected?: boolean;
  disabled?: boolean;
}) {
  return (
    <SectionCard title={connected ? '关系范围 · 服务器资源' : '关系范围 · Demo'}>
      <BodyText>
        {selected === null
          ? '尚未选择关系'
          : (profiles.find((p) => p.id === selected)?.displayName ?? '关系不可用')}
      </BodyText>
      <View style={{ gap: 8 }}>
        {profiles.map((p) => (
          <PrimaryButton
            key={p.id}
            label={`选择${p.displayName}${connected ? ` · ${p.id}` : ''}`}
            selected={p.id === selected}
            variant="quiet"
            disabled={disabled}
            onPress={() => onSelect(p.id)}
          />
        ))}
      </View>
    </SectionCard>
  );
}
