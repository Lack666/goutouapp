import { View } from 'react-native';
import type { RelationshipProfileViewModel } from '../contracts/relationship';
import { BodyText, PrimaryButton, SectionCard } from './ui';

export function RelationshipSelector({
  profiles,
  selected,
  onSelect,
}: {
  profiles: readonly RelationshipProfileViewModel[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <SectionCard title="关系范围 · Demo">
      <BodyText>
        {selected === null
          ? '尚未选择关系'
          : (profiles.find((p) => p.id === selected)?.displayName ?? '关系不可用')}
      </BodyText>
      <View style={{ gap: 8 }}>
        {profiles.map((p) => (
          <PrimaryButton
            key={p.id}
            label={`选择${p.displayName}`}
            selected={p.id === selected}
            variant="quiet"
            onPress={() => onSelect(p.id)}
          />
        ))}
      </View>
    </SectionCard>
  );
}
