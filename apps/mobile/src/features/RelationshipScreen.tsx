import { useMemo, useState } from 'react';
import { useRouter } from 'expo-router';
import { View } from 'react-native';
import { useDataSource } from '../data/DataSourceProvider';
import { useSurface } from '../hooks/useSurface';
import { StatePreview } from '../components/StatePreview';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  EmptyState,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';

export default function RelationshipScreen() {
  const source = useDataSource();
  const router = useRouter();
  const profiles = useMemo(() => source.readRelationships(), [source]);
  const [selected, setSelected] = useState<string | null>(null);
  const profile = profiles.find((p) => p.id === selected) ?? profiles[0];
  const { state, scenario, setScenario, retry } = useSurface('relationship');
  return (
    <ScreenContainer>
      <AppHeader
        title="关系资料"
        subtitle="先了解已知信息，给未知留一点空间。"
        onBack={() => (router.canGoBack() ? router.back() : router.replace('/'))}
      />
      <DemoNotice />
      <View style={{ gap: 8 }}>
        {profiles.map((p) => (
          <PrimaryButton
            key={p.id}
            label={`选择${p.displayName}`}
            variant="quiet"
            selected={profile?.id === p.id}
            onPress={() => setSelected(p.id)}
          />
        ))}
      </View>
      {scenario === 'empty' ? (
        profile ? (
          <>
            <SectionCard title={profile.displayName}>
              <BodyText>关系类型：{profile.label ?? '未提供'}</BodyText>
              <BodyText>最近互动：{profile.lastInteraction ?? '未提供'}</BodyText>
            </SectionCard>
            <SectionCard title="对象资料 · Person">
              <BodyText>显示昵称：{profile.person.nickname ?? '未提供'}</BodyText>
            </SectionCard>
            <SectionCard title="已知信息">
              {profile.known.length ? (
                profile.known.map((item, i) => <BodyText key={i}>{item}</BodyText>)
              ) : (
                <BodyText muted>未提供</BodyText>
              )}
            </SectionCard>
            <SectionCard title="待补充信息">
              {profile.missing.length ? (
                profile.missing.map((item, i) => <BodyText key={i}>{item}</BodyText>)
              ) : (
                <BodyText muted>未提供</BodyText>
              )}
            </SectionCard>
            <SectionCard title="历史摘要">
              <BodyText muted>{profile.historySummary ?? '未提供历史聊天或摘要。'}</BodyText>
              <PrimaryButton
                label="查看关系历史（尚未接入）"
                variant="quiet"
                onPress={() => router.push('/history')}
              />
            </SectionCard>
            <SectionCard title="分析结果">
              <BodyText muted>
                {profile.analysisSummary ?? '未提供分析结果；没有自动分析任何聊天记录。'}
              </BodyText>
            </SectionCard>
            <PrimaryButton
              label="前往本地对话预览"
              onPress={() =>
                router.push({ pathname: '/chat', params: { relationshipId: profile.id } })
              }
            />
            <PrimaryButton
              label="前往导入与分析（尚未接入）"
              variant="quiet"
              onPress={() => router.push('/import')}
            />
          </>
        ) : (
          <EmptyState title="还没有关系资料" description="未提供对象或关系资料。" />
        )
      ) : null}
      <BodyText muted>
        来源：匿名合成 Demo。关系、对象与聊天记录分属不同数据；未读取账户或导入内容。
      </BodyText>
      <PrimaryButton label="编辑资料（尚未开放）" disabled />
      <StatePreview
        showEmpty={false}
        state={state}
        scenario={scenario}
        onSelect={setScenario}
        onRetry={retry}
      />
    </ScreenContainer>
  );
}
