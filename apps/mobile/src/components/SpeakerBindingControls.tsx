import { View } from 'react-native';
import { BodyText, PrimaryButton, SectionCard } from './ui';
import type { SpeakerBindingDraft, SpeakerInventoryItemViewModel } from '../contracts/import';
import type { PersonViewModel } from '../contracts/relationship';

export function SpeakerBindingControls({
  speaker,
  binding,
  persons,
  onBind,
  disabled = false,
}: {
  speaker: SpeakerInventoryItemViewModel;
  binding: SpeakerBindingDraft;
  persons: readonly PersonViewModel[];
  onBind: (binding: SpeakerBindingDraft) => void;
  disabled?: boolean;
}) {
  return (
    <SectionCard title={speaker.rawLabel}>
      <BodyText>
        {speaker.sourceLabel} · {speaker.messageCount} 条消息
      </BodyText>
      <BodyText>
        绑定：{binding.kind}
        {binding.kind === 'person' ? ` · ${binding.personId ?? '尚未选择 Person'}` : ''}
      </BodyText>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {(['self', 'person', 'system', 'ignore'] as const).map((role) => (
          <PrimaryButton
            key={role}
            label={`${speaker.rawLabel} → ${role}`}
            variant="quiet"
            disabled={disabled}
            selected={binding.kind === role}
            onPress={() =>
              onBind(role === 'person' ? { kind: role, personId: null } : { kind: role })
            }
          />
        ))}
      </View>
      {binding.kind === 'person' &&
        persons.map((person) => (
          <PrimaryButton
            key={person.id}
            label={`${speaker.rawLabel} → ${person.id}`}
            variant="quiet"
            selected={binding.personId === person.id}
            disabled={disabled}
            onPress={() => onBind({ kind: 'person', personId: person.id })}
          />
        ))}
    </SectionCard>
  );
}
