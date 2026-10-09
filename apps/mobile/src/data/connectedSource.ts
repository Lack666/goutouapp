import type { ShellDataSource } from '../contracts/shell';
const unavailable = (): never => {
  throw new Error('此业务尚未接入服务器。');
};
// Connected screens use the async controller. Accidental Demo template use fails closed.
export const connectedSource: ShellDataSource = {
  kind: 'connected',
  readChat: unavailable,
  readRelationships: () => [],
  readImport: unavailable,
  readHistory: () => ({ agent: [], relationship: [] }),
  readSettings: unavailable,
  readSurface: (id) => ({
    status: 'empty',
    view: {
      id,
      title: '开发连接',
      description: 'Connected Development Mode',
      emptyTitle: '尚未接入',
      emptyDescription: '此业务尚未接入服务器。',
    },
  }),
};
