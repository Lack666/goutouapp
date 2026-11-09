# ICA-BQ-R1 离线证据协议修复验收

日期：2026-11-09。基线 HEAD：`79ff9d7`。

**ICA-BQ-R1 ENGINEERING PASS；ICA-BQ QUALITY FAIL / PARTIAL 保持。**

本轮是用户“继续下一步”授权下的有限离线修复，不是新的真实模型评测。
真实 Provider 调用 **0**，费用 **0**，自动重试 **0**。上一轮147次真实调用与原结果
完整保留，不从其¥20授权剩余额度追加批次。没有开始ICA-C、长周期扩容或Phase12。
正式Marker仍9/9H，Phase11 QUALITY FAIL、Phase10 DEFERRED、Phase12 PENDING；
原人工评分、报告、失败证据及六份既有用户工作文件未纳入本轮修改或提交。

## 修复及合同

新增版本合同 [ICA_BQ_R1_CONTRACT](ICA_BQ_R1_CONTRACT.md)，不覆盖span-v1方案。

- 模型wire协议`quote-v2`只接收合法消息alias、真实speaker与最多160 code point的精确原文。
  服务端仅在该alias对应消息内查找唯一匹配，计算Unicode `[start,end)`，再走原来源验证器。
  不存在、重复含重叠、规范化差异、错speaker、跨chunk/窗及混合数字span字段全部拒绝。
- 同正文不同UUID保留独立来源。core/halo允许集合、双窗隔离、反证与候选事实完整相等检查不变。
  所有校验在成功回调与completed receipt之前完成。模型输入中的canonical refs投影为quote-only，
  内部状态、HTTP证据查询、存储报告和Mobile generated client继续保留canonical数字span。
- Mock执行版本为`ica-bq-r1-mock-v2`，绑定quote-v2、resolver源码指纹、原问题/授权/预算和来源。
  before/after/publication仍重新检查当前Grant与数据库来源，未增加Memory或消息发送权限。
  旧执行绑定不能跨协议继续执行。prepare、confirm均不启动模型。
- 安全normal要求risks为空；其他决定要求风险。复核仍要求四项全真且无reason codes。
  Prompt说明这些已有跨字段要求；没有关闭安全复核、修改schema限额或放宽统计/反证规则。
- 显式`span-v1`仅保留给历史回放与原评测工具；不按模型输出自动降级，HTTP不能选择legacy。
  新wire默认用于Runtime和服务端Mock执行。旧付费batch-v1工具未升级成新的质量批次。

参考W3C TextQuoteSelector的精确引文锚定概念与Python字符串查找，代码独立实现，无新依赖，
不声称W3C全规范兼容、不复制第三方代码。来源链接与边界见版本合同。
冻结MIT Skill、knowledge哈希和按需路由保持不变。

## 已披露输出的迁移诊断

[quote-migration-replay.json](evidence/ica-bq-r1/quote-migration-replay.json)
固定核对旧calls/results/cases三个SHA256，并保留141个真实记录输出的原始与迁移后哈希。
只有完整五字段v1 evidence对象可在显式离线迁移中移除start/end；生产v2不接受这类对象。

64条旧序列中，**48条 recording_incomplete，16条 validation_rejected**。
后者为invalid_model_output6、content_review_rejected9、model_statistics1。
旧请求未发生的后续阶段绝不补造，全部`report=null`，不生成伪造的审批、安全结论或完成率。
291处引用出现位置可在原合成来源内唯一匹配，其中210处旧数字span错误可由原文重建；
这不是291条独立消息，也不证明模型解释正确。新协议下真实模型能否生成更好结果尚未验证。
已披露旧holdout现在只能作开发诊断，后续质量验收必须用新独立保留集。

## 真实签名HTTP、PostgreSQL与Demo

复用原独立PG16 ASCII安装目录，绑定`127.0.0.1:15435`。没有initdb、修改角色、连接生产、
清空未知数据库或新增基础设施。每次pytest用随机`ica_test_<suffix>`，迁移至Alembic head，
Native Restore使用额外随机独立测试库。测试后数据库与连接均0，实例已停止。
见[清理与版本记录](evidence/ica-bq-r1/postgres-cleanup.txt)及[停止记录](evidence/ica-bq-r1/postgres-stop.txt)。

本轮真实签名导入、身份绑定、范围prepare/confirm、独立执行prepare/confirm、Mock图和证据查询：

| 匿名合成范围 | Core精确覆盖 | K | 实际Mock调用 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 近3天 | 900/900 | 5 | 12 | 全范围完成，insufficient_evidence |
| 近7天 | 2100/2100 | 11 | 24 | 全范围完成，insufficient_evidence |
| Unicode双方互动 | 2/2 | 1 | 5 | 有finding，canonical引用经真实来源查询复核 |

快照：[900](evidence/ica-bq-r1/signed-demo-900.json)、
[2100](evidence/ica-bq-r1/signed-demo-2100.json)、
[Unicode来源](evidence/ica-bq-r1/signed-finding.json)。
空候选的counterevidence receipt如实为not_applicable，没有伪造模型已完成反证。
这些报告是Mock接线证明，不是DeepSeek洞察或用户质量示例。

真实DB10k源读取：[SQL EXPLAIN与内存](evidence/ica-bq-r1/sql-10k.json)。
每页上限500，读取21页，Python峰值2,933,310 bytes；范围超准入仍整体拒绝，未截到200条。
没有新增推测性的索引。该小型匿名数据EXPLAIN不证明生产级性能或月/季/年容量。

PG回归涵盖非法Owner/Person/Dataset、篡改/过期challenge、并发confirm幂等、
来源变化、resolver源码/协议变化、撤销、TTL、所有范围删除、活动writer fencing、
Restore quarantine及当前操作键关联。Memory consent/paused/记录在ICA流程中不改变；
11R两条真实HTTP+SQL Memory P0回归通过。未增加迁移或授权能力。

## 测试、失败及修正

[后端集中日志](evidence/ica-bq-r1/backend-tests.txt)：**506 passed in54.66s**，
覆盖30个定向文件：导入/merge/JSONL/Markdown、scope/keyset/DST/Unicode/分片、
签名授权/执行/删除/Restore、Agent Runtime/Knowledge/REST、安全角色、Memory P0及评测工具。
新增quote30、quote Runtime18、quote replay12均包含在506内。
[首轮69项](evidence/ica-bq-r1/focused-tests.txt)与该组重叠，不重复累加。
原Agent Runtime/Knowledge定向组本轮均通过；未关闭安全或修改原人工结果。

- Mobile导入/文件选择/UI/会话隔离 **67/4 suites PASS**：
  [日志](evidence/ica-bq-r1/mobile-tests.txt)。
- Transport **43/1 suite PASS**：[日志](evidence/ica-bq-r1/transport-tests.txt)。
  初次发现既有测试还断言43个操作，实际已有52，
  [原失败日志](evidence/ica-bq-r1/transport-initial-failure.txt)保留。
  修正清单断言：36个原操作、dataset1、erasures3、lifecycle3和ICA9；
  ICA9逐一校验method/path/Bearer，未改变生产transport或放宽合同。
- [TypeScript](evidence/ica-bq-r1/mobile-typecheck.txt)、
  [OpenAPI52且原26合同保留](evidence/ica-bq-r1/openapi.txt)、
  [generated-client3项](evidence/ica-bq-r1/api-client.txt)通过，公开schema无漂移。
  单独重复codegen检查未另计测试总数。
- [Ruff](evidence/ica-bq-r1/ruff.txt)、[Format10文件](evidence/ica-bq-r1/format.txt)、
  [Mobile格式](evidence/ica-bq-r1/mobile-format.txt)通过。最初长行与import顺序已修正后验证。
- 修正旧签名测试默认覆写B1历史证据的问题，改写pytest tmp_path，再独立归档本轮输出。
  本轮没有先覆盖旧证据再恢复。旧BQ/B1结果与冻结案例保持原字节。

没有运行完整Root Verify、Phase0–9历史全集、Android原生历史全集或真实Provider测试。
没有进行新人工评分。这些未执行项不记PASS。

## 源码、复现与停止边界

实际修改清单、raw-byte SHA256、基线完整HEAD和旧证据核对见
[source-manifest.json](evidence/ica-bq-r1/source-manifest.json)。
运行源码指纹`bf76eb4bd39d1b9aaaab5700eae2eddf4e142bf8f67e4f3432cabfd16ad998d7`，
签名Demo中的runtime_digest与此一致。原Canonical DTO与OpenAPI输出无改动。
主要文件：`imported_quote.py`、`imported_analysis.py`、`imported_execution.py`、
`evals/ica/{runner,quote_replay}.py`、五个ICA测试、Mobile一个清单测试，及版本合同/验收文档。

精确已执行命令、测试选择、隔离目录及归档步骤见
[commands.ps1](evidence/ica-bq-r1/commands.ps1)。离线重放输出独占创建，不可原目录重跑覆写。

仍待后续明确有限阶段：冻结新的独立案例/人工rubric及quote-v2真实评测协议；
使新的付费harness显式绑定v2 Schema、模型、当前价格、预算和一次性发送计划；
获得新的明确预算后才可发送。旧工具默认legacy用于历史再现，本轮没有据此创建新计划。
quote-v2真实生成成功率、语义质量、人类接受度、最坏96项反证输出预算、
月/季/年召回与聚合能力均未因本次修复自动通过。

**本轮到此停止。不得把ENGINEERING PASS写成ICA-BQ质量通过，或自动进入下一阶段。**
