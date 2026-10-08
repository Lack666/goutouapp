import type { ChatScreenViewModel } from '../contracts/chat';
import type { RelationshipProfileViewModel } from '../contracts/relationship';

const profiles: readonly RelationshipProfileViewModel[] = [
  {
    id: 'demo-a',
    displayName: '关系 A · 同学',
    person: { id: 'person-a', nickname: '对象 A（合成）' },
    label: '同学',
    lastInteraction: '演示时间 · 周一',
    known: ['合成背景：一起参加过学习活动。'],
    missing: ['对方的沟通偏好', '双方对关系的期待'],
    historySummary: '合成摘要：一次学习活动的安排。未导入任何记录。',
    analysisSummary: null,
    source: 'demo',
  },
  {
    id: 'demo-b',
    displayName: '关系 B · 待补充',
    person: { id: 'person-b', nickname: null },
    label: null,
    lastInteraction: null,
    known: [],
    missing: ['昵称', '关系状态', '最近互动时间', '历史聊天', '分析结果'],
    historySummary: null,
    analysisSummary: null,
    source: 'demo',
  },
];
export function readDemoRelationships(): readonly RelationshipProfileViewModel[] {
  return profiles.map((p) => ({
    ...p,
    person: { ...p.person },
    known: [...p.known],
    missing: [...p.missing],
  }));
}
export function readDemoChat(relationshipId: string | null): ChatScreenViewModel {
  const profile = profiles.find((p) => p.id === relationshipId);
  return {
    source: 'demo',
    thread: {
      id: `demo-thread-${relationshipId ?? 'general'}`,
      relationshipId,
      title: relationshipId === null ? '本地对话预览' : (profile?.displayName ?? '关系未提供'),
      messages: [
        {
          id: 'example-user',
          role: 'user',
          text: '这是一段合成问题：怎样把自己的需求说清楚？\n\n先整理发生的事情，再区分自己的猜测。🌱',
          timeLabel: '演示时间 · 10:00',
          source: 'synthetic-demo',
        },
        {
          id: 'example-assistant',
          role: 'assistant',
          text: '预置示例：可以先描述具体发生的事情，再表达感受和需求。\n\n这只是界面示例，未分析你的输入，也不代表对方的想法。',
          timeLabel: '演示时间 · 10:00',
          source: 'synthetic-demo',
        },
      ],
    },
    fiu: [
      {
        kind: 'fact',
        text: '合成场景中约定在周末讨论活动。',
        provenance: '来源：预置合成场景描述',
      },
      {
        kind: 'inference',
        text: '双方可能愿意继续沟通。',
        alternative: '也可能只是讨论活动安排；需要更多信息。',
      },
      { kind: 'unknown', text: '对方对关系的期待尚不确定。' },
    ],
  };
}
