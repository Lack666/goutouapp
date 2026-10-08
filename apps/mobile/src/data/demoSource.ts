import type { ShellDataSource, SurfaceId, SurfaceViewModel } from '../contracts/shell';

const surfaces: Record<SurfaceId, SurfaceViewModel> = {
  home: {
    id: 'home',
    title: '首页',
    description: '从这里开始，给关系留一点思考的空间。',
    emptyTitle: '欢迎来到狗头军师',
    emptyDescription: '选择一个入口，了解你可以从哪里开始。',
  },
  chat: {
    id: 'chat',
    title: '对话',
    description: '整理你的困惑，也给自己一点空间。',
    emptyTitle: '还没有对话',
    emptyDescription: '这里将展示你的问题和回复。当前可以预览布局，暂时无法发送消息。',
  },
  relationship: {
    id: 'relationship',
    title: '关系资料',
    description: '认识自己，也理解你正在关注的人。',
    emptyTitle: '还没有关系资料',
    emptyDescription: '这里将展示个人资料、关系背景和你确认的信息。当前尚未连接账户资料。',
  },
  import: {
    id: 'import',
    title: '导入与分析',
    description: '让分散的聊天记录有一个清楚的入口。',
    emptyTitle: '还没有导入记录',
    emptyDescription: '导入入口和分析展示区已预留。当前不会读取、上传或分析任何聊天文件。',
  },
  history: {
    id: 'history',
    title: '历史记录',
    description: '回看过去的交流，慢慢看清自己的变化。',
    emptyTitle: '还没有历史记录',
    emptyDescription: '这里将展示可回看的记录。演示模式不会生成真实对话或分析结论。',
  },
  settings: {
    id: 'settings',
    title: '设置',
    description: '让界面更适合你。',
    emptyTitle: '应用信息',
    emptyDescription: '狗头军师 · 0.1.0 · 本地演示',
  },
};

export const demoSource: ShellDataSource = {
  kind: 'demo',
  readSurface(id, scenario) {
    if (scenario === 'loading') return { status: 'loading' };
    if (scenario === 'error')
      return { status: 'error', message: '演示状态：本地读取失败。点击重试可恢复空状态。' };
    return { status: 'empty', view: { ...surfaces[id] } };
  },
};
