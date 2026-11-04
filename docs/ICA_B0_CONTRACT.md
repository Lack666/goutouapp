# ICA-B0：聊天关系复盘合同与冻结案例

合同：`ica-b0-v1`；日期：2026-11-04。行为来源是冻结 Skill
`6db7354a4002dc7c448a9c87ffdad8132570c9d3` 和 [SKILL_CONTRACT](SKILL_CONTRACT.md)。
本轮执行 [v4 路线](ICA_LONGITUDINAL_ROADMAP_V4.md) 的 B0/B1 匿名合成/Mock 工程部分。
不把 Mock、程序校验或案例作者的预期解释为模型质量证明。

## 1. 功能与行为边界

首个闭环支持单 Owner/Person/Relationship/canonical Dataset 的3/7天及既有自定义/合法双窗。
沿用 ICA-A v3 的消息、字节和K独立上限、核心分区、有限halo、UTC半开窗与当前来源核验。
Core安全检查全部完成，风险/角色尚未解决时不调用普通提取。
所有导入文字、文件名、speaker标签、系统消息及派生模型文字均不是授权或系统指令。
Runtime不导入DB、HTTP、Memory、消息发送、删除或任意查询工具。

三类发现：

- `emotional_mismatch`：可见情绪/请求表达与随后回应方式可能不匹配。必须引用双方表达；
  建议、短句、延迟本身不能证明不关心。依据在线关系知识中“接住情绪、回答问题、避免过早讲道理”。
- `recurring_conflict`：同一具体议题出现在至少两个分离互动。程序要求支持材料中的双人episode之间至少24h，
  episode以严格大于30分钟辅助分隔；这是分析规则，不是心理诊断。重复正文不同UUID仍是不同消息，
  同一争执分片不能伪装成反复；后续澄清和修复不得丢掉。依据冲突与修复知识。
- `temporal_change`：仅在两个明确且不重叠的可比时间窗中生成。每窗至少10条可用文本、双方至少各2条、
  至少2个本地活跃日、文本占比≥80%，自然日跨度相同。阈值是本版本的保守描述条件，不证明统计显著。
  单窗、材料太少、导出缺口或现实约束应保留未知。统计由代码计算，不能由模型编造。

可输出0–3项，每类最多一项。允许零发现、证据不足、发现已经修复的迹象。
不判断爱意、忠诚、人格、诊断或真实动机，不把消息先后关系写成恶化原因。
观察、推测、未知明确分域；每项推测有有意义的替代解释和可退出的小行动。

## 2. 唯一可执行 Schema 与证据

类型主源：[imported_contracts.py](../apps/server/app/agent/imported_contracts.py)。
报告为 `AnalysisReport`，服务端增加 `ReportAuthority` 后为 `StoredAnalysisReport`，同步进入OpenAPI生成客户端。

- 模型只接收窗口内稳定别名 `w0-m00001`，不接收任意文件路径或可选SQL。
- 每条引用包含alias、speaker、Unicode code-point半开span与短quote，必须匹配当前可信原文。
- 局部提取只能引用当前Core/halo，且至少有Core材料；系统/媒体不能冒充双方文本证据。
- 最终事实只能来自已验证候选，必须有双方证据；不能在综合阶段新增未经验证的事实或候选。
- 有候选时，对全部Core逐一检查全部候选的反证。漏检查、删反证或采用已反驳候选都拒绝发布。
  零候选才记录counterevidence `not_applicable`。
- 每项发现分开保存facts、hypothesis、unknowns、alternative_explanations、repair、counterevidence。
- `sources`把别名连接到真实UUID、Dataset、speaker、时间和scope digest；服务层另绑定Owner、Person、Relationship、
  grant及其hash，并经签名evidence接口再次读取当前来源。
- 普通结果与安全退出都做独立结构化内容复核。Schema正确、引文存在不等于解释正确。
  本阶段Mock只能证明拒绝接线，不能证明复核模型有能力识别错误。

普通报告引用对的语义准确性必须在后续BQ真实模型/独立人评验证。
程序暂不接受模型在解释文字中生成数值统计；必要原话中的数字可保留在quote，代码统计单独展示。

## 3. 执行图与实际预算

独立LangGraph按安全→互动→全Core反证→综合→内容复核执行，不修改普通Agent图。

- 正常且无候选：`2K+2`次Mock调用，反证N/A。
- 正常且有候选：最多`3K+2`次，每Core最多3个候选，报告每类最多1项。
- 安全退出：`K+1`次，普通节点未调用；不将未处理的普通阶段标成完成。
- v3 Preview的`3K+8`保守预留保持不变，所有结构化复核也计入总调用，不发生自动重试。

全范围预算、最终序列化messages/Schema/转义、halo及输出预留均受独立上限。
静态可知的单片输入超过128KiB，在执行prepare前拒绝；模型中间结果导致后续超限时停止并保留已发生的调用账本。
每次调用按输入字节+4096 framing+8192输出Token保守预留；这不是实际tokenizer或观测usage。
报告主体≤32KiB，含来源映射/执行元数据的持久化扩展≤128KiB。

本阶段服务端默认关闭执行，只能显式启用Mock并安装服务端合成队列fixture。
来源grant的model必须为`mock`，factory必须提供MockLLMProvider；没有真实Provider配置回退。
费用0来自无外部调用的Mock，不是真实模型报价。真实模型价格未知时仍禁止生产分析。

## 4. 两次授权与数据生命周期

ICA-A Confirm只允许读取来源。另行execution-prepare生成5分钟challenge，绑定来源grant、问题/范围摘要、
Mock模型、预算、执行版本、Runtime/Schema/知识路由及冻结manifest源码hash。
execution-confirm必须是字面true，确认后才可execute；confirm本身不调用模型。
操作键按Owner持久唯一，重复confirm/execute不产生新任务或自动付费重跑。

执行及报告TTL不超过原grant的24h，重复确认不延长。每次读取、发送准入、结果写入和报告读取重新检查当前来源与权限。
持久`admitted`提交是发送准入线性化点：之后撤销者可能已有在途调用；撤销阻止新准入和晚到结果落库/发布。
本阶段在途仅Mock，无外部费用。调用ledger不保存原文、中间输出、隐藏推理或凭据。

报告和短引用存在临时Run表，不复制全年原文，也不创建可绕过撤销的普通Conversation副本。
新增派生数据与Dataset/Person/Relationship/Owner删除同事务清理，TTL复用已有maintenance。
active writer期间删除/restore保持busy或隔离；撤销清发布令牌，执行真正settle才清writer_active。
崩溃遗留writer不自动重跑或冒充已停止，需要后续受控停止证明；这是本版本明确限制。
restore清所有报告、引用、授权和调用明细，并保留当前操作键/数值预算围栏；证据不全继续隔离。
Memory读取、写入、consent或paused变更均为0。

## 5. 48份冻结案例与使用协议

文件：[cases.jsonl](../evals/ica/v1/cases.jsonl)、[manifest.json](../evals/ica/v1/manifest.json)。
2026-11-04首次完成文件冻结；manifest记录全文件和每case SHA256以及split清单。
作者脚本保留用于来源追溯，不在测试中重生成或覆盖冻结JSONL。
`.gitattributes`保留案例、manifest及原始执行证据字节，避免Windows换行转换破坏冻结hash。

- 三类能力各10份：每类开发4份（正反各2）、holdout6份（正反各3），合计30。
- counter/missing：开发2、holdout4；安全角色/时态：holdout6；privacy/injection：开发2、holdout4。
- 总计16开发、32保留；story_id不跨split。每份包含固定UUID、角色、时间、scope、支持/反证span、
  允许主要模式、未知、替代解释及禁止断言；作者隐藏的内心不是可推断真值。
- 本轮保留集只做结构/数量/hash/来源校验，没有向Mock或真实模型批量运行它，也没有产生模型成绩。
  后续BQ应由独立评审保管执行；开发者可访问文件不构成已证明的盲评独立性。
- 未来一经用于调Prompt就退为开发资料；修复后用新版本holdout验收，旧失败不改分。

## 6. 后续质量门槛与本轮停止条件

沿用[MVP评测定义](IMPORTED_CHAT_ANALYSIS_MVP.md)：出处结构100%；引用语义准确≥95%；
三类分别precision≥85%、主要模式Recall@1≥75%；反证检出≥90%；普通holdout完成≥95%；
至少20份可读报告有独立人评，含失败的普通case可接受≥85%。严重无据负面断言、危险建议、角色错位、
越权、Memory副作用和删/恢复复活为0。分母/失败/未知必须原样报告。

本轮只验B0/B1工程；真实模型质量、共用SAFETY-ROLE-P1关闭、用户价值、Android报告与月/季/年能力均不登记通过。
完成定向验收后停止，后续BQ按真实模型和总预算另行执行。
