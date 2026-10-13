import { useMemo, useState } from 'react';
import { View } from 'react-native';
import {
  AppHeader,
  BodyText,
  DemoNotice,
  PrimaryButton,
  ScreenContainer,
  SectionCard,
} from '../components/ui';
import { useDataSource } from '../data/DataSourceProvider';
import {
  deletionPreview,
  previewMemoryControl,
  type MemoryControlAction,
  type MemoryDeleteConfirmationViewModel,
} from '../contracts/settings';
import { useLocalNavigation } from '../navigation/scope';
import { StatePreview } from '../components/StatePreview';
import { useSurface } from '../hooks/useSurface';
import { useTheme, type ThemePreference } from '../theme/ThemeProvider';
import { tokens } from '../theme/tokens';
import { useConnection } from '../session/ConnectionProvider';
import { DevelopmentSessionControls } from '../components/DevelopmentSessionControls';
import { ConnectedMemoryPanel } from './ConnectedMemoryPanel';

const preferences: readonly { id: ThemePreference; label: string }[] = [
  { id: 'system', label: '跟随系统' },
  { id: 'light', label: '浅色' },
  { id: 'dark', label: '深色' },
];
export default function SettingsScreen() {
  const connection = useConnection();
  return connection?.session.snapshot().mode === 'connected' ? (
    <ConnectedSettingsScreen />
  ) : (
    <DemoSettingsScreen />
  );
}
function ConnectedSettingsScreen() {
  const connection = useConnection()!;
  const { back } = useLocalNavigation();
  const { preference, setPreference } = useTheme();
  return (
    <ScreenContainer>
      <AppHeader title="设置" subtitle="开发会话与外观" onBack={back} />
      <SectionCard title="外观">
        {preferences.map((item) => (
          <PrimaryButton
            key={item.id}
            label={item.label}
            selected={preference === item.id}
            variant="quiet"
            onPress={() => setPreference(item.id)}
          />
        ))}
      </SectionCard>
      <DevelopmentSessionControls />
      <BodyText muted>
        当前 App 仅开放记忆删除；聊天历史、Person、Relationship 和完整账户尚无自助删除入口。
      </BodyText>
      <ConnectedMemoryPanel connection={connection} />
    </ScreenContainer>
  );
}
function DemoSettingsScreen() {
  const source = useDataSource();
  const model = useMemo(() => source.readSettings(), [source]);
  const profiles = useMemo(() => source.readRelationships(), [source]);
  const [control, setControl] = useState(model.control);
  const [inspect, setInspect] = useState(false);
  const [undo, setUndo] = useState(false);
  const [confirmation, setConfirmation] = useState<MemoryDeleteConfirmationViewModel | null>(null);
  const [feedback, setFeedback] = useState('');
  const { state, scenario, setScenario, retry } = useSurface('settings');
  const { back } = useLocalNavigation();
  const { preference, setPreference, mode } = useTheme();
  const update = (action: MemoryControlAction) => {
    setControl((current) => previewMemoryControl(current, action));
    setFeedback('本地演示状态已更新');
  };
  return (
    <ScreenContainer>
      <AppHeader title="设置" subtitle="让界面更适合你。" onBack={back} />
      <SectionCard title="外观">
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: tokens.space.sm }}>
          {preferences.map((item) => (
            <PrimaryButton
              key={item.id}
              label={item.label}
              variant="quiet"
              selected={preference === item.id}
              onPress={() => setPreference(item.id)}
            />
          ))}
        </View>
        <BodyText muted>
          当前外观：{mode === 'dark' ? '深色' : '浅色'}。本地偏好仅在本次打开期间保留。
        </BodyText>
      </SectionCard>
      <SectionCard title="应用信息">
        <BodyText>狗头军师 · 0.1.0</BodyText>
        <BodyText muted>移动端本地演示 · Backend not connected</BodyText>
      </SectionCard>
      <DemoNotice />
      <DevelopmentSessionControls />
      <SectionCard title="账户与记忆">
        <BodyText muted>尚未接入账户或记忆服务。当前没有可管理的服务器资料。</BodyText>
      </SectionCard>
      {scenario === 'empty' && (
        <>
          <SectionCard title="Memory 授权 · Demo">
            <BodyText>
              Consent：{control.consentEnabled ? '已授权（演示）' : '未授权（演示）'}
            </BodyText>
            <BodyText>Pause：{control.paused ? '已暂停（演示）' : '未暂停（演示）'}</BodyText>
            <BodyText>
              召回/写入开关预览：
              {control.consentEnabled && !control.paused ? '允许（演示）' : '关闭（演示）'}
            </BodyText>
            <BodyText muted>
              授权与暂停是独立维度。撤销授权保留现有记录并暂停；重新授权保留暂停状态。未授权时恢复不会重新授权。
            </BodyText>
            <PrimaryButton
              label="授权预览（Demo）"
              variant="quiet"
              onPress={() => update('grant')}
            />
            <PrimaryButton
              label="撤销授权预览（Demo）"
              variant="quiet"
              onPress={() => update('revoke')}
            />
            <PrimaryButton
              label="暂停预览（Demo）"
              variant="quiet"
              onPress={() => update('pause')}
            />
            <PrimaryButton
              label="恢复预览（Demo）"
              variant="quiet"
              onPress={() => update('resume')}
            />
            <BodyText live>{feedback || '仅本地 UI 演示，不改变服务器数据。'}</BodyText>
          </SectionCard>
          <SectionCard title="Inspect Memory · Demo">
            <PrimaryButton
              label={inspect ? '收起记忆样例' : '查看记忆样例（Demo）'}
              selected={inspect}
              variant="quiet"
              onPress={() => setInspect(!inspect)}
            />
            <BodyText muted>
              历史信息并非一定仍然正确。有效/过期状态是合成快照，不是当前服务器判断。
            </BodyText>
            {inspect &&
              (model.records.length ? (
                model.records.map((record) => (
                  <SectionCard key={record.id} title={record.summary}>
                    <BodyText>
                      subject：{record.subject} · scope：{record.personId ?? 'user'} /{' '}
                      {record.relationshipId ?? '无关系范围'}
                    </BodyText>
                    <BodyText>创建：{record.createdAt}</BodyText>
                    <BodyText>过期：{record.expiresAt}</BodyText>
                    <BodyText>
                      状态：{record.state === 'active' ? '有效（演示快照）' : '过期（不可召回）'} ·
                      匿名合成 Demo
                    </BodyText>
                    <PrimaryButton
                      label={`预览删除 ${record.id}`}
                      variant="quiet"
                      onPress={() =>
                        setConfirmation(
                          deletionPreview(model.records, { kind: 'one', recordId: record.id }),
                        )
                      }
                    />
                  </SectionCard>
                ))
              ) : (
                <BodyText>没有记忆样例</BodyText>
              ))}
          </SectionCard>
          <SectionCard title="Undo Preview · Demo">
            <PrimaryButton
              label="查看撤销预览（Demo）"
              selected={undo}
              variant="quiet"
              onPress={() => setUndo(!undo)}
            />
            {undo && (
              <>
                <BodyText>{model.undo?.summary ?? '没有可撤销的样例'}</BodyText>
                <BodyText>
                  Expected Operation：{model.undo?.expectedOperation ?? '尚无服务器操作信息'}
                </BodyText>
                <BodyText muted>
                  Guarded Undo 需服务器最新操作 ID 与
                  operation_key；过期或变更时不能撤销其它记录。撤销不能恢复已删除的记忆。
                </BodyText>
                <PrimaryButton label="正式撤销（尚未开放）" disabled />
              </>
            )}
          </SectionCard>
          <SectionCard title="删除确认预览 · Demo">
            {profiles.map((p) => (
              <PrimaryButton
                key={p.person.id}
                label={`预览删除 ${p.person.id} 的记忆`}
                variant="quiet"
                onPress={() =>
                  setConfirmation(
                    deletionPreview(model.records, { kind: 'person', personId: p.person.id }),
                  )
                }
              />
            ))}
            <PrimaryButton
              label="预览删除全部记忆（Demo）"
              variant="quiet"
              onPress={() =>
                setConfirmation(
                  deletionPreview(model.records, { kind: 'all', revokeConsent: null }),
                )
              }
            />
            {confirmation && (
              <SectionCard title="请核对删除范围 · Demo">
                <BodyText>删除范围：{confirmation.scopeLabel}</BodyText>
                <BodyText>影响数量：{confirmation.affectedCount} 条匿名样例</BodyText>
                <BodyText muted>
                  只展示主库 Memory 与关联撤销历史的删除范围；不会删除关系实体、AI
                  对话或导入聊天。此演示不删除任何样例或服务器数据。
                </BodyText>
                {confirmation.target.kind === 'all' && (
                  <>
                    <BodyText>
                      删除后授权选择：
                      {confirmation.target.revokeConsent === null
                        ? '尚未选择'
                        : confirmation.target.revokeConsent
                          ? '撤销授权并暂停'
                          : '保留当前授权'}
                    </BodyText>
                    {[true, false].map((revokeConsent) => (
                      <PrimaryButton
                        key={String(revokeConsent)}
                        label={
                          revokeConsent
                            ? '删除后撤销授权（Demo 选择）'
                            : '删除后保留授权（Demo 选择）'
                        }
                        variant="quiet"
                        selected={
                          confirmation.target.kind === 'all' &&
                          confirmation.target.revokeConsent === revokeConsent
                        }
                        onPress={() =>
                          setConfirmation(
                            deletionPreview(model.records, { kind: 'all', revokeConsent }),
                          )
                        }
                      />
                    ))}
                  </>
                )}
                <PrimaryButton
                  label="我已核对范围（仅演示）"
                  selected={confirmation.stage === 'acknowledged'}
                  disabled={
                    confirmation.target.kind === 'all' && confirmation.target.revokeConsent === null
                  }
                  onPress={() => setConfirmation((c) => c && { ...c, stage: 'acknowledged' })}
                />
                {confirmation.stage === 'acknowledged' && (
                  <BodyText>
                    已核对本地展示；真实 Challenge、Receipt、operation_key 仍需服务器提供。
                  </BodyText>
                )}
                <PrimaryButton label="正式删除（尚未开放）" disabled />
                <PrimaryButton
                  label="取消删除预览"
                  variant="quiet"
                  onPress={() => setConfirmation(null)}
                />
              </SectionCard>
            )}
          </SectionCard>
          <SectionCard title="保留期限与隐私">
            <BodyText>{model.retention.label}</BodyText>
            {model.retention.notices.map((notice) => (
              <BodyText key={notice} muted>
                {notice}
              </BodyText>
            ))}
          </SectionCard>
        </>
      )}
      <PrimaryButton
        label="重置 Memory Demo"
        variant="quiet"
        onPress={() => {
          setControl(model.control);
          setInspect(false);
          setUndo(false);
          setConfirmation(null);
          setFeedback('本地演示状态已更新');
          retry();
        }}
      />
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
