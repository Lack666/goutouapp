# ICA-BQ-V2 新保留集与真实评测验收

日期：2026-11-09；基线HEAD：`b0999fc`。

**ICA-BQ-V2 QUALITY FAIL / PARTIAL；真实独立人评PENDING。**
已完成一次授权批次：233次真实调用、重试0、未知0；预留¥19.935784，未超过¥20。
普通完成event10/22、baseline9/22，低于95%门槛，两臂也均不足20份可读普通报告。
人评可以诊断已发布报告的价值与问题，不能补救本批机器完成率。没有登记质量PASS或进入下一阶段。

## 版本与来源

沿用[R1 quote-v2](ICA_BQ_R1_CONTRACT.md)的严格引文来源协议，无Agent行为修改。
新合同：[ICA_BQ_V2_EVAL_CONTRACT](ICA_BQ_V2_EVAL_CONTRACT.md)。
独立作者未读取v1案例/模型输出/评分，具体接触范围及局限见
[作者声明](../evals/ica/v2/AUTHORING_PROVENANCE.md)。案例仍由AI编写，语义oracle未获独立真人认可。
开发者可以访问同一仓库，不声称具备外部独立盲评保管。

新48例：development16，holdout32。其中普通22（情绪错配6、重复冲突6、双窗变化6、反证/不足4），
安全角色6，注入/导出不足4。三类普通各3正例/3硬负例；完整案例/故事/消息UUID及完整对话均不复用v1。
开发900/2100条分别Core5/11片，不混入付费小样例的质量分母，也不冒充长周期真实模型质量证明。
案例字节SHA256：`15e1d48fff423456f6144bcf64cf639c13b6303af5ff4959129f955fc3b7a379`。

发现作者oracle可选alias按各窗重置，与Runtime全局编号不同。冻结原文件和正确UUID/span/quote均保留，
人评私有包另提供当前服务端UUID→alias映射及警示，裁定不能直接使用作者的额外alias。
没有借此修改语义预期或模型输入。

## 准入、真实预算授权与冻结

[plan.json](evidence/ica-bq-v2/batch-v2/plan.json)完整SHA256：
`4b892761e50eafa92c0481f5d2dcacd9132822790f4ea64c6eb597e60062e4ee`。
用户本轮新确认“授权本批≤¥20，禁止自动重试”，
[独立授权记录](evidence/ica-bq-v2/batch-v2/authorization.json)绑定该计划，
[claim](evidence/ica-bq-v2/batch-v2/claimed.json)只能独占一次。旧v1授权未复用。

模型deepseek-flash，文档版本DeepSeek-V4.1-Flash-1017；非思考模式，temperature0。
价格按2026-11-09[官方页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)高峰费率冻结，
不保证远端别名对应不可变权重。[JSON模式](https://api-docs.deepseek.com/guides/json_mode/)不能代替Schema/语义校验。

32例×两臂各一次，按案例交替先后顺序；同图/Schema/验证的逐片摘要prompt对照，不是独立架构对比。
图调用上界356次，全范围3K+8规划合计740次（两个不同概念）；钱包独立上限400请求、
10,000,000保守预留Token、¥20；输出4096Token、实际序列化输入128KiB。
按每次最大输入输出的全图最坏费用包络¥107.905024，显然不保证¥20可覆盖该包络。
实际每次包含Schema/halo/动态候选的payload才做准入；预算不足停机，剩余保留not_run，
绝不缩小单次授权聊天范围、追加授权或自动重试。4096输出也不保证容纳最坏96项反证。

所有五阶段wire Schema、实际源码/知识/参考/案例/人评量表均绑定，发送前重验。
每次先fsync预留，再一次HTTP请求。未知、无usage、预留超限、来源漂移或已发布结果的安全路由
不符oracle时停整批。技术拒绝不能发布，不伪造通过，也不解释为已经真人判定角色正确。
每条结果和人评哈希均绑定plan SHA；未授权时不得读取真实密钥或构造Provider。

## 工程验证与修正

[集中回归](evidence/ica-bq-v2/backend-tests.txt)：**309 passed in6.90s**，17个定向文件。
包括59项新案例、4项新集Graph/来源/无泄漏整合、52项新批次准入/HTTP MockTransport、
18项新人评，以及旧ICA/quote/Agent Runtime/Knowledge/安全角色。各项包含于309，不重复累加。

[Ruff](evidence/ica-bq-v2/ruff.txt)、[Format8文件](evidence/ica-bq-v2/format.txt)、
[作者脚本Ruff](evidence/ica-bq-v2/author-ruff.txt)/[格式](evidence/ica-bq-v2/author-format.txt)通过。
[OpenAPI52且原26合同保留](evidence/ica-bq-v2/openapi.txt)、
[generated client3项](evidence/ica-bq-v2/api-client.txt)通过，无API/schema/generated Mobile内容漂移。

发送前发现并修复：plan普通dict相等会把true/1、0/false、400/400.0视为相同，改为严格JSON哈希比较；
新安全family为safety_role，补齐旧safety兼容；批次哈希加入人工绑定；
人评packet改为深拷贝并验证显示输入/输出，拒绝缺项/额外项/内容篡改；已知低分FAIL优先于PENDING。
这些均在计划最终冻结和首次发送之前完成，无结果驱动的Prompt或validator修复。

本轮未改`apps/server/app`、Mobile生产源码、Memory/Grant/删除/Restore或依赖。
没有重新运行PostgreSQL/Mobile全套/Root Verify；R1真实签名PG、生命周期与Memory P0记录继续保留，
不能写成本轮重新执行。此次外部调用仅冻结匿名合成材料，不连接用户真实聊天或数据库。

## 人工评审

工具与量表：[ICA_BQ_V2_HUMAN_REVIEW](ICA_BQ_V2_HUMAN_REVIEW.md)。
真实包由冻结CLI导出：[人工入口](evidence/ica-bq-v2/human-review/reviewer/README.md)、
[原文与报告](evidence/ica-bq-v2/human-review/reviewer/reports.md)、
[空白评分表](evidence/ica-bq-v2/human-review/reviewer/packet.json)。公开原文/报告与私有映射/oracle分目录。
所有人工字段保持null；助手不填写真人身份、独立性声明、分数、语义或接受度。
有可读报告后通知用户。任何机器失败留在分母，不能被人评补救成完成。
若不足每臂20份可读普通报告，人工反馈仅用于诊断，不能登记完整质量PASS。

包中64条均保留；28条有已发布报告，其中19条属于普通问题（两臂10/9），其余为安全/对抗样例。
34条技术失败和2条not_run没有报告，不能评为可接受。所有人工字段仍null，未伪造任何分数。
[未评分摘要](evidence/ica-bq-v2/human-review-pending.json)两臂均FAIL，语义/接受度仍待真人判断。
第一轮只阅读reviewer目录；完成后另存评分副本，再按说明做独立oracle裁定。

并行任务已成功导出此包；主任务在收到该子任务额度错误通知后再次尝试导出，独占创建保护拒绝，
旧包和pending摘要未覆盖。[重复导出错误](evidence/ica-bq-v2/human-export.txt)与
[摘要防覆盖错误](evidence/ica-bq-v2/human-summary.txt)保留。随后主任务核对全部64条原文/输出/plan哈希，
重新计算的摘要与原pending文件完全一致。不是重新生成随机评审ID或重置评分。

## 实际结果、费用与未解决问题

[原始结果](evidence/ica-bq-v2/batch-v2/results.jsonl)、
[调用账本](evidence/ica-bq-v2/batch-v2/calls.jsonl)、
[预算摘要](evidence/ica-bq-v2/batch-v2/budget-summary.json)、
[运行日志](evidence/ica-bq-v2/batch-v2/console.txt)、
[自动审计](evidence/ica-bq-v2/execution-audit.json)。

| 两臂合计 | 数量 |
| --- | ---: |
| completed | 28 |
| failed | 34 |
| not_run | 2 |
| content_review_rejected | 10 |
| model_statistics | 13 |
| invalid_evidence | 2 |
| invalid_model_output | 5 |
| unverified_fact | 1 |
| nontext_finding | 1 |
| incomparable_windows | 2 |

最后h31 baseline在下一次准入会超钱包时失败；h32两臂均not_run，仍计入32例固定分母。
原Runtime把该准入异常包装成invalid_model_output，因此上表5项中有1项是预算拒绝，
不能说成5个实际模型Schema错误。用已记录的前两阶段离线重建第三次synthesis请求，
大小22,059 bytes，需再预留¥0.085078，合计将达¥20.020862，故发送前拒绝。
见[零外部调用诊断](evidence/ica-bq-v2/cutoff-diagnostic.json)。本轮不修改已冻结的错误分类接线。
没有额外请求或第二批补跑，所有233次admitted都有唯一returned记录，无重复stage/chunk尝试。
预留7,104,788 Token，实际input1,308,255/output48,184/total1,356,439；
缓存命中573,696、未命中734,559，全部usage可核对。
按冻结高峰缓存明细计算的保守估算**¥1.87753784**，不是结算发票。
预留上限与实际估算是不同账：达到预留上限仍按冻结政策停止，不释放预留后续跑。
返回model全部deepseek-flash；请求延迟p50 1,142.63ms/p95 5,226.56ms，不是App体验承诺。

已发布报告的102处canonical引用出现位置均再次匹配真实合成UUID/speaker/正文code-point范围；
这只证明来源结构，不证明语义合理，且不替代真实DB授权测试。
批次前后源码/Schema/案例/量表与计划完整哈希一致，没有付费后修改Prompt、schema或护栏。
新旧案例不同，不能用本批与v1的引用失败数量差直接声称因果质量提升。

主要未解决项是数字统计护栏拒绝、内容复核拒绝、结构输出及少量来源/窗口错误。
本轮仅保留错误分类与原输出，没有据此调整规则或重跑。若后续使用这些输出修复行为，
这些case成为已知开发材料，新质量验收须另冻独立保留集。
原96项反证最坏输出、月/季/年扩容、独立架构对比均未因此通过。

## 交付与停止

[源码与证据清单](evidence/ica-bq-v2/source-manifest.json)记录实际修改文件及raw-byte SHA256；
[命令记录](evidence/ica-bq-v2/commands.ps1)记录离线检查、一次授权/运行和人评导出。
冻结执行源指纹为`717d6effdafd59b90cfc67d04718d684024834292830add2865a0375d006e76d`。
独立审计子任务在交付最后消息时遇到工具额度限制，最终账本核验由主任务自动完成，
不冒称新的人类独立评审。所有原始结果、已知失败、未执行项和人评null原样保留。
保留v1、R1、Phase11 QUALITY FAIL、Phase10 DEFERRED、Phase12 PENDING、Marker9/9H及用户六份既有文件。
没有ICA-C报告页面、月/季/年分析扩容、Phase12或第二次付费批次。
本阶段到此停止，等待真实人工反馈或新的有限修复指令。
