import { useMemo, useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { filterHistory, HISTORY_PAGE_SIZE, type HistorySourceKind } from '../contracts/history';
import { useDataSource } from '../data/DataSourceProvider';
import { useRelationshipScope, useLocalNavigation } from '../navigation/scope';
import { useSurface } from '../hooks/useSurface';
import { useTheme } from '../theme/ThemeProvider';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  EmptyState,
  PrimaryButton,
  SectionCard,
} from '../components/ui';
import { StatePreview } from '../components/StatePreview';
import { RelationshipSelector } from '../components/RelationshipSelector';
import { HistoryList } from '../components/HistoryList';

export default function HistoryScreen() {
  const scope = useRelationshipScope();
  return <HistorySession key={scope ?? 'general'} scope={scope} />;
}
export function HistorySession({ scope }: { scope: string | null }) {
  const source = useDataSource();
  const { colors } = useTheme();
  const nav = useLocalNavigation();
  const model = useMemo(() => source.readHistory(), [source]);
  const profiles = useMemo(() => source.readRelationships(), [source]);
  const [kind, setKind] = useState<HistorySourceKind>('relationship');
  const [limit, setLimit] = useState(HISTORY_PAGE_SIZE);
  const [loaded, setLoaded] = useState(false);
  const { state, scenario, setScenario, retry } = useSurface('history');
  const unavailable = scope !== null && !profiles.some((p) => p.id === scope);
  const all = useMemo(
    () => filterHistory(model, { kind, relationshipId: scope }),
    [model, kind, scope],
  );
  const items = useMemo(
    () => (loaded && scenario === 'empty' && !unavailable ? all.slice(0, limit) : []),
    [loaded, scenario, unavailable, all, limit],
  );
  const reset = () => {
    setLimit(HISTORY_PAGE_SIZE);
    setLoaded(false);
    retry();
  };
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <HistoryList
        items={items}
        header={
          <View style={{ gap: 16 }}>
            <AppHeader
              title="历史记录"
              subtitle="AI 对话与导入关系聊天分别查看。"
              onBack={nav.back}
            />
            <DemoNotice />
            <BodyText muted>
              本地演示 · 未连接服务器。Chat 的本地输入不会出现在保存历史中。
            </BodyText>
            <RelationshipSelector profiles={profiles} selected={scope} onSelect={nav.select} />
            {unavailable ? (
              <EmptyState
                title="关系不可用"
                description="没有读取其它关系的历史，请返回选择有效关系。"
              />
            ) : (
              <>
                <SectionCard title="历史来源">
                  <View style={{ gap: 8 }}>
                    <PrimaryButton
                      label="AI 对话"
                      selected={kind === 'agent'}
                      variant="quiet"
                      onPress={() => {
                        setKind('agent');
                        setLimit(HISTORY_PAGE_SIZE);
                      }}
                    />
                    <PrimaryButton
                      label="关系聊天"
                      selected={kind === 'relationship'}
                      variant="quiet"
                      onPress={() => {
                        setKind('relationship');
                        setLimit(HISTORY_PAGE_SIZE);
                      }}
                    />
                  </View>
                  <BodyText>
                    {kind === 'agent'
                      ? 'Agent Chat History · user/assistant 合成示例'
                      : 'Imported Relationship Chat History · self/person/system 合成示例'}
                  </BodyText>
                  <PrimaryButton
                    label="加载历史样例（Demo）"
                    disabled={kind === 'relationship' && scope === null}
                    onPress={() => {
                      setLoaded(true);
                      setLimit(HISTORY_PAGE_SIZE);
                      retry();
                    }}
                  />
                  <BodyText muted>
                    当前窗口：{items.length} / {loaded ? all.length : 0} · 每次最多增加{' '}
                    {HISTORY_PAGE_SIZE} 条。未实现网络 cursor。
                  </BodyText>
                  <BodyText muted>
                    按历史时间、来源数据集、source_index、ID
                    排序；不按内容去重。不同文件部分重叠仍是后续限制。
                  </BodyText>
                </SectionCard>
                {scope && (
                  <>
                    <PrimaryButton
                      label="进入 Chat 本地预览"
                      onPress={() => nav.open('/chat', scope)}
                    />
                    <PrimaryButton
                      label="前往导入 Demo"
                      variant="quiet"
                      onPress={() => nav.open('/import', scope)}
                    />
                  </>
                )}
              </>
            )}
            <StatePreview
              showEmpty={false}
              state={state}
              scenario={scenario}
              onSelect={setScenario}
              onRetry={retry}
            />
            <PrimaryButton label="重置历史 Demo" variant="quiet" onPress={reset} />
          </View>
        }
        footer={
          <View style={{ gap: 8, paddingVertical: 16 }}>
            <BodyText muted>匿名合成历史 · Demo · 未保存服务器记录</BodyText>
            <PrimaryButton
              label="查看更多（Demo）"
              disabled={
                !loaded || scenario !== 'empty' || unavailable || items.length >= all.length
              }
              onPress={() => setLimit((n) => Math.min(n + HISTORY_PAGE_SIZE, all.length))}
            />
          </View>
        }
      />
    </SafeAreaView>
  );
}
