import type { SurfaceId } from '../contracts/shell';
export type ShellPath = '/' | '/chat' | '/relationship' | '/import' | '/history' | '/settings';
export interface ShellRoute {
  id: Exclude<SurfaceId, 'home'>;
  path: Exclude<ShellPath, '/'>;
  label: string;
  summary: string;
}
export const routes: readonly ShellRoute[] = [
  { id: 'chat', path: '/chat', label: '开始对话', summary: '把困惑慢慢说清楚' },
  { id: 'relationship', path: '/relationship', label: '关系资料', summary: '了解自己与关系背景' },
  { id: 'import', path: '/import', label: '导入与分析', summary: '聊天记录的整理入口' },
  { id: 'history', path: '/history', label: '历史记录', summary: '回看交流与思考' },
  { id: 'settings', path: '/settings', label: '设置', summary: '主题与应用信息' },
];
