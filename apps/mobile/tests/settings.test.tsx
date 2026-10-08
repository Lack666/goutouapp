import { fireEvent, screen } from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';
import { app } from './testApp';
import { demoSource } from '../src/data/demoSource';
import { deletionPreview, previewMemoryControl } from '../src/contracts/settings';
import { DataSourceProvider } from '../src/data/DataSourceProvider';
import SettingsScreen from '../src/features/SettingsScreen';

const press = async (name: string) => fireEvent.press(screen.getByRole('button', { name }));
describe('Settings honest Memory preview', () => {
  it('consent and pause are independent, revoke keeps inspectable records, resume does not grant', async () => {
    await renderRouter(app, { initialUrl: '/settings' });
    await press('暂停预览（Demo）');
    expect(screen.getByText('Consent：未授权（演示）')).toBeOnTheScreen();
    await press('授权预览（Demo）');
    expect(screen.getByText('Pause：已暂停（演示）')).toBeOnTheScreen();
    await press('恢复预览（Demo）');
    expect(screen.getByText('召回/写入开关预览：允许（演示）')).toBeOnTheScreen();
    await press('查看记忆样例（Demo）');
    await press('撤销授权预览（Demo）');
    await press('恢复预览（Demo）');
    expect(screen.getByText('Consent：未授权（演示）')).toBeOnTheScreen();
    expect(screen.getByText('Pause：已暂停（演示）')).toBeOnTheScreen();
    expect(screen.getByText('合成摘要：关系 A 曾讨论学习活动。')).toBeOnTheScreen();
    expect(screen.getByText('本地演示状态已更新')).toBeOnTheScreen();
    await press('重置 Memory Demo');
    expect(screen.getByText('Pause：未暂停（演示）')).toBeOnTheScreen();
    expect(screen.queryByText('合成摘要：关系 A 曾讨论学习活动。')).toBeNull();
  });
  it('inspects synthetic subject/scope, historical creation and expiry, never raw internals', async () => {
    await renderRouter(app, { initialUrl: '/settings' });
    await press('查看记忆样例（Demo）');
    expect(screen.getByText('subject：relationship · scope：person-a / demo-a')).toBeOnTheScreen();
    expect(screen.getByText('过期：2026-06-30T10:00:00Z')).toBeOnTheScreen();
    expect(screen.getByText('状态：过期（不可召回） · 匿名合成 Demo')).toBeOnTheScreen();
    expect(screen.getByText(/历史信息并非一定仍然正确/)).toBeOnTheScreen();
    expect(screen.getAllByText('创建：2026-09-01T10:00:00Z')).toHaveLength(2);
    expect(screen.queryByText(/raw evidence|hidden reasoning|operation internals/)).toBeNull();
  });
  it('Undo Preview identifies expected operation requirement and disables real guarded execution', async () => {
    await renderRouter(app, { initialUrl: '/settings' });
    await press('查看撤销预览（Demo）');
    expect(screen.getByText(/Expected Operation：需匹配服务器/)).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '正式撤销（尚未开放）' })).toBeDisabled();
    expect(screen.getByText(/撤销不能恢复已删除的记忆/)).toBeOnTheScreen();
  });
  it('previews one/person/all scope, explicit all-consent choice and cancellation without deletion', async () => {
    await renderRouter(app, { initialUrl: '/settings' });
    await press('查看记忆样例（Demo）');
    await press('预览删除 memory-a');
    expect(screen.getByText('删除范围：单条记忆 memory-a')).toBeOnTheScreen();
    expect(screen.getByText('影响数量：1 条匿名样例')).toBeOnTheScreen();
    await press('我已核对范围（仅演示）');
    expect(screen.getByRole('button', { name: '正式删除（尚未开放）' })).toBeDisabled();
    await press('取消删除预览');
    await press('预览删除 person-b 的记忆');
    expect(screen.getByText('删除范围：Person person-b 的对象/关系记忆')).toBeOnTheScreen();
    expect(screen.getByText('影响数量：1 条匿名样例')).toBeOnTheScreen();
    await press('预览删除全部记忆（Demo）');
    expect(screen.getByText('影响数量：3 条匿名样例')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '我已核对范围（仅演示）' })).toBeDisabled();
    await press('删除后撤销授权（Demo 选择）');
    await press('我已核对范围（仅演示）');
    expect(screen.getByText(/真实 Challenge、Receipt、operation_key/)).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: '正式删除（尚未开放）' })).toBeDisabled();
    await press('删除后保留授权（Demo 选择）');
    expect(screen.getByRole('button', { name: '我已核对范围（仅演示）' })).not.toBeSelected();
    expect(screen.getByText('合成摘要：关系 A 曾讨论学习活动。')).toBeOnTheScreen();
    expect(screen.getByText('Consent：未授权（演示）')).toBeOnTheScreen();
  });
  it('explains configurable policy, expiry/cleanup/backup boundaries, and session-only theme', async () => {
    await renderRouter(app, { initialUrl: '/settings' });
    expect(screen.getByText('示例保留策略：180 天')).toBeOnTheScreen();
    expect(screen.getByText('真实期限以后以服务器返回的 policy 为准。')).toBeOnTheScreen();
    expect(screen.getByText('过期后不可召回；物理清理可能稍后执行。')).toBeOnTheScreen();
    expect(screen.getByText(/主库删除不等于备份\/日志立即清除/)).toBeOnTheScreen();
    await press('深色');
    expect(screen.getByRole('button', { name: '深色' })).toBeSelected();
    expect(screen.getByText(/本地偏好仅在本次打开期间保留/)).toBeOnTheScreen();
  });
  it('resets route-local controls on unmount and accepts an empty/substituted DataSource', async () => {
    await renderRouter(app, { initialUrl: '/' });
    await press('进入设置');
    await press('授权预览（Demo）');
    await press('返回上一级');
    await press('进入设置');
    expect(screen.getByText('Consent：未授权（演示）')).toBeOnTheScreen();
    const Injected = () => (
      <DataSourceProvider
        source={{
          ...demoSource,
          readSettings: () => ({
            ...demoSource.readSettings(),
            records: [],
            undo: null,
            retention: { label: '替代保留策略', notices: [] },
          }),
        }}
      >
        <SettingsScreen />
      </DataSourceProvider>
    );
    await renderRouter({ ...app, settings: Injected }, { initialUrl: '/settings' });
    await press('查看记忆样例（Demo）');
    expect(screen.getByText('没有记忆样例')).toBeOnTheScreen();
    await press('查看撤销预览（Demo）');
    expect(screen.getByText('没有可撤销的样例')).toBeOnTheScreen();
    expect(screen.getByText('替代保留策略')).toBeOnTheScreen();
  });
  it('retains service semantics and immutable record/preview values', () => {
    const model = demoSource.readSettings();
    expect(previewMemoryControl({ consentEnabled: false, paused: true }, 'resume')).toEqual({
      consentEnabled: false,
      paused: true,
    });
    expect(previewMemoryControl({ consentEnabled: false, paused: true }, 'grant')).toEqual({
      consentEnabled: true,
      paused: true,
    });
    expect(
      deletionPreview(model.records, { kind: 'person', personId: 'person-a' }).affectedCount,
    ).toBe(1);
    expect(deletionPreview(model.records, { kind: 'all', revokeConsent: false })).toMatchObject({
      affectedCount: 3,
      stage: 'review',
      executable: false,
    });
    const other = demoSource.readSettings();
    expect(model).toEqual(other);
    expect(model.records[0]).not.toBe(other.records[0]);
    expect(model.undo).not.toBe(other.undo);
    expect(model.retention.notices).not.toBe(other.retention.notices);
  });
});
