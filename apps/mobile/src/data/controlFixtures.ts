import type { ImportDemoKind, ImportWizardViewModel } from '../contracts/import';
import type { HistoryPageViewModel, RelationshipHistoryItemViewModel } from '../contracts/history';
import type { SettingsViewModel } from '../contracts/settings';

// Entirely anonymous, generated examples; dates belong to the fixtures, never the clock.
export function readDemoImport(kind: ImportDemoKind): ImportWizardViewModel {
  const speakers =
    kind === 'empty'
      ? []
      : [
          { id: 'speaker-0', rawLabel: '我', sourceLabel: '合成导出标签 0', messageCount: 6 },
          {
            id: 'speaker-1',
            rawLabel: '匿名同学🌱',
            sourceLabel: '合成导出标签 1',
            messageCount: 5,
          },
          {
            id: 'speaker-2',
            rawLabel: '系统通知🔔',
            sourceLabel: '合成导出标签 2',
            messageCount: 1,
          },
          ...(kind === 'group'
            ? [
                {
                  id: 'speaker-3',
                  rawLabel: '匿名参与者🌿',
                  sourceLabel: '合成导出标签 3',
                  messageCount: 4,
                },
              ]
            : []),
        ];
  return {
    provenance: 'synthetic-demo',
    summary: {
      sourceFormat: 'wechat_markdown_v1（合成摘要，未解析文件）',
      messageCount: speakers.reduce((n, s) => n + s.messageCount, 0),
      speakerCount: speakers.length,
      firstTimestamp: '2026-09-01T10:00:00+08:00',
      lastTimestamp: '2026-09-02T11:20:00+08:00',
      sourceTimezone: 'Asia/Shanghai',
      warnings: ['示例警告：有一条系统通知，需明确绑定；警告并不代表文件不可用。'],
      possibleDuplicate: '可能重复的合成数据集提示；不代表已去重。',
    },
    speakers,
  };
}
export function readDemoHistory(): HistoryPageViewModel {
  const relationship: RelationshipHistoryItemViewModel[] = [];
  for (const relationshipId of ['demo-a', 'demo-b']) {
    // 1,020 rows per scope, two datasets with equal historical timestamps.
    for (let i = 0; i < 1020; i++) {
      const sender = i % 9 === 2 ? 'system' : i % 2 === 0 ? 'self' : 'person';
      relationship.push({
        id: `${relationshipId}-${i}`,
        kind: 'relationship',
        relationshipId,
        sender,
        rawSpeakerLabel:
          sender === 'self' ? '我' : sender === 'person' ? '匿名同学🌱' : '系统通知🔔',
        content: `${relationshipId === 'demo-a' ? 'A' : 'B'} 合成历史 ${i} 🌱\n\n${sender === 'system' ? '合成活动通知。' : '讨论学习活动的安排。'}`,
        timestamp: `2026-09-01T${String(10 + Math.floor(i / 360)).padStart(2, '0')}:${String(Math.floor(i / 6) % 60).padStart(2, '0')}:00+08:00`,
        datasetId: i < 510 ? 'synthetic-source-1' : 'synthetic-source-2',
        sourceIndex: i % 510,
        provenance: 'synthetic-demo',
      });
    }
  }
  return {
    agent: [null, 'demo-a', 'demo-b'].flatMap((relationshipId) => [
      {
        id: `user-${relationshipId}`,
        kind: 'agent' as const,
        relationshipId,
        role: 'user' as const,
        content: '预置合成问题：怎样表达活动安排？',
        timestamp: '2026-09-03T10:00:00+08:00',
        datasetId: 'synthetic-agent',
        sourceIndex: 0,
        provenance: 'synthetic-demo' as const,
      },
      {
        id: `assistant-${relationshipId}`,
        kind: 'agent' as const,
        relationshipId,
        role: 'assistant' as const,
        content: '预置助手示例：先确认时间，再说明需求。未运行 Agent。',
        timestamp: '2026-09-03T10:00:00+08:00',
        datasetId: 'synthetic-agent',
        sourceIndex: 1,
        provenance: 'synthetic-demo' as const,
      },
    ]),
    relationship,
  };
}
export function readDemoSettings(): SettingsViewModel {
  return {
    control: { consentEnabled: false, paused: false },
    records: [
      {
        id: 'memory-user',
        summary: '合成摘要：偏好清楚的活动安排。',
        subject: 'user',
        personId: null,
        relationshipId: null,
        createdAt: '2026-09-01T10:00:00Z',
        expiresAt: '2027-02-28T10:00:00Z',
        state: 'active',
        provenance: 'synthetic-demo',
      },
      {
        id: 'memory-a',
        summary: '合成摘要：关系 A 曾讨论学习活动。',
        subject: 'relationship',
        personId: 'person-a',
        relationshipId: 'demo-a',
        createdAt: '2026-09-01T10:00:00Z',
        expiresAt: '2027-02-28T10:00:00Z',
        state: 'active',
        provenance: 'synthetic-demo',
      },
      {
        id: 'memory-b',
        summary: '合成摘要：对象 B 的旧活动安排。',
        subject: 'object',
        personId: 'person-b',
        relationshipId: null,
        createdAt: '2026-01-01T10:00:00Z',
        expiresAt: '2026-06-30T10:00:00Z',
        state: 'expired',
        provenance: 'synthetic-demo',
      },
    ],
    undo: {
      summary: '最近一条可撤销记忆 · 合成关系 A 摘要',
      expectedOperation: '需匹配服务器最新插入操作；本演示没有 operation ID 或 receipt。',
      executable: false,
    },
    retention: {
      label: '示例保留策略：180 天',
      notices: [
        '真实期限以后以服务器返回的 policy 为准。',
        '过期后不可召回；物理清理可能稍后执行。',
        '主库删除不等于备份/日志立即清除；必要的操作元数据按其策略保留。',
      ],
    },
  };
}
