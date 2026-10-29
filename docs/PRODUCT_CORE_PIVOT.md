# 狗头军师产品核心调整：关系复盘与沟通洞察

日期：2026-10-29。路线版本：`product-core-pivot-v2`。状态：**审查与规划交付；产品开发未启动**。

本轮授权仅覆盖架构审查、路线调整方案与实施规划。实施合同见
[Imported Chat Analysis MVP](IMPORTED_CHAT_ANALYSIS_MVP.md)。本文不修改
[MASTER_PLAN](MASTER_PLAN.md)、`project-phase.json`、冻结知识、旧评测或正式阶段标记。

## 1. 产品定位与判断边界

狗头军师 App 的核心是**基于长期聊天记录的关系复盘与沟通洞察工具**。用户主动选择材料，
系统从可核查的互动中帮助用户发现可能忽略的情绪表达、沟通错位、反复冲突与时间变化，
提出值得核实的潜在隔阂、未被回应的需求，以及尊重双方边界的修复选项。

聊天只证明“记录中出现了什么表达”，不能直接证明对方的真实动机、心理状态或长期积怨。
“多次表达失落后收到事务建议”可以是观察；“对方从不在乎你”不能成为事实。
每项发现必须同时交代支持证据、反面证据检查、其他解释、未知及适用范围。
没有充分证据时返回零发现或证据不足，不能为了生成报告而补齐三类结论。

接下来的产品投入以导入记录分析闭环为主。通用情感问答继续保留当前质量标签，
暂不以提高其人工评分为开发主目标；产品专项通过也不能替通用 Agent 颁发质量 PASS。

## 2. 审查基线与现有结论

源码基线：`de17b6a`，最近提交为 Phase11R 有限语义/Memory 修复；此前依次有
`7dffd45`、`44831ef`、`42803c1` 的审计、11Q 修复与旧 ICA 规划。
实际读取 `project-phase.json` 为 `completed_phase=9`、`completed_subphase=9H`。

- [Phase11R 工程报告](PHASE_11R_SEMANTIC_REPAIR_REPORT.md) 的 **TARGETED PASS** 保留。
  该报告记录两条真实 Memory P0 控制越权路径已修复；不是通用质量或全量回归通过。
- [Phase11 原质量收尾](PHASE_11_QUALITY_CLOSEOUT.md) 的原评分、失败、分母、阈值和结论不变。
- 工作区现有 [11R 人工评审报告](PHASE_11R_HUMAN_REVIEW_REPORT.md) 记录 8/8 完成、
  3/8 可接受（37.5%），人工质量 FAIL；**Phase11 仍 QUALITY FAIL**。
  这份报告是本轮开始前的未提交用户文件，本文引用其工作区内容，不冒充已提交验收。
- Phase10 仍 OPTIONAL / DEFERRED，原 Phase12 仍 PENDING，生产发布仍未获批准。

开始时已有未提交文件：`evals/agent/results/human-review-15.json`、
`scripts/human_review_ui.py`，以及 `docs/PHASE_11R_HUMAN_REVIEW_REPORT.md`、
`evals/agent/results/human-review-summary.md`、`r11-human-review-v1-summary.md`、
`r11-human-review-v1.json`（后三者位于 `evals/agent/results/`）。本轮不修改或提交这些用户工作。

## 3. 能力审查：可复用基础与实际缺口

### 导入数据、清洗与来源

[import_jobs.py](../apps/server/app/db/models/import_jobs.py) 已有 `RelationshipMessage`：
消息 UUID、Owner、Relationship、canonical ImportJob、source_index、sender/person、
规范化正文、content_type、UTC/原始时间/时区、指纹及原文件行号。
Dataset 是已 imported 的 canonical `ChatImportJob`，无需另建 Dataset 内容表。
稳定消息 ID 与 occurrence 顺序可复用；正文指纹不代表唯一消息。

[WeChatMarkdownParser](../apps/server/app/chat_import/wechat_markdown.py) 支持版本化微信 Markdown v1、
增量 UTF-8、时区/DST、保守多行清洗、issue/skip 和媒体占位；
[ImportJobService](../apps/server/app/services/import_jobs.py) 要求明确 self/person/system/ignore 绑定，
双人就绪须恰有一个 self、一个与 Relationship 匹配的 Person。
[ImportMergeService](../apps/server/app/services/import_merge.py) 重新解析并校验，分批 staging 后原子导入，
相同 transcript 返回 canonical `dataset_job_id`。重复正文 occurrence 保留。

缺少按单 Dataset/日期/消息位置构建的精确授权快照、缺口披露和证据读取接口。
现有 Relationship 历史分页覆盖整个关系，不能当作分析范围；导入成功不保证导出完整。
报告必须披露忽略说话人、解析跳过、媒体缺失、时间警告。选中数据的实际 min/max 时间应从记录计算，
不能盲用按源顺序累计的 first/last metadata。

### Owner、Person、Dataset 与删除

[ResourceService](../apps/server/app/services/resources.py)、
[records repositories](../apps/server/app/db/repositories/records.py) 与复合外键已提供签名 Owner 与对象隔离，
已有 canonical Dataset 发现。列表可包含删除墓碑，选择分析时必须再次拒绝已删除项目。
新增服务仍须逐级验证 active Owner → Relationship → Person → canonical imported Dataset → 消息清单，
不能信任客户端 UUID 或以 FK 代替请求鉴权。

[ErasureService](../apps/server/app/services/erasure.py)、
[LifecycleErasure](../apps/server/app/services/lifecycle_erasure.py)、
[backup_restore](../apps/server/app/services/backup_restore.py) 已有确认、收据、墓碑、writer 屏障和受控恢复。
**当前 Dataset 删除不认识分析 Run、报告或引文这些尚不存在的依赖**。
报告一旦持久化，必须在同一子阶段扩展撤销、删除、TTL、重放、在途 writer 和恢复对账；不能等发布再补。

### LangGraph、FIU 与 Evidence

[AgentRuntime](../apps/server/app/agent/runtime.py) 已有独立 Python run/stream、节点读写矩阵，
安全优先、场景、FIU、确定性参考路由、关系分析、行动与回复节点；可复用执行骨架与验证边界。
节点不能依赖 FastAPI Request 或自行读取任意 Dataset。

当前 [AgentService](../apps/server/app/services/agent_service.py) 只读 Agent Conversation 的 Message；
服务层 history 上限20，[context_payload](../apps/server/app/agent/prompts/common.py) 实际仅送最近8条。
[capabilities](../apps/server/app/agent/capabilities.py) 仍明确 chat_import 未接入。
现有 State 不含可信导入范围、授权、消息快照或报告。不能仅改能力文案或把原文拼入普通 Chat。

[contracts](../apps/server/app/agent/contracts.py) 的 FIU 可复用事实/推测/未知原则，但 source 仅是类型标签，
F/I/U/A 是本轮内部位置 ID；[analysis_validation](../apps/server/app/agent/analysis_validation.py)
检查这些 ID/参考 alias，并不提供原始消息归属、quote span 或语义蕴含证明。
需要独立版本化的 imported context/source/report 合同，并保持普通路径原校验不放宽。

### DeepSeek、Token 与上下文

[LLMProvider](../apps/server/app/llm/provider.py) 与 Mock 已有 chat/stream/structured_output；
[OpenAICompatibleProvider](../apps/server/app/llm/openai_compatible.py) 可继续承载 DeepSeek，
无需新增 SDK。JSON object 模式加本地 Pydantic 校验不等于服务商强制 Schema，失败必须保持失败。
隐藏 reasoning 已丢弃，不能引入隐藏思维链保存。

[ContextBudget](../apps/server/app/agent/knowledge.py) 只限制参考：1–3篇、每篇4000字符、总9000字符，
不是整个模型输入预算。[EvalBudget](../apps/server/app/llm/eval_budget.py) 有评测请求/Token/费用预留，
失败也消耗预留；普通 factory 未注入它，不能宣称生产调用已有完整预算控制。
缺少分析 Run 级预算与最终序列化请求（含 Schema/参考/复核）窗口检查。
模型、窗口与价格在下一次真实批次前核对官方版本；仓库2026-10-26的价格仅为历史快照。

### Android 与 Memory

[ConnectedImportScreen](../apps/mobile/src/features/ConnectedImportScreen.tsx) 已有真实五步导入；
[filePicker.native](../apps/mobile/src/data/filePicker.native.ts) 处理用户选择的 content URI 和私有缓存。
[ConnectedHistoryScreen](../apps/mobile/src/features/ConnectedHistoryScreen.tsx)、history controller、
Dataset 发现、生成 client、JWT、SSE、session/scope epoch 和删除控件可以复用。
历史浏览每页100、客户端最多2000条，是浏览限制，不是模型读取范围。

当前六个 [routes](../apps/mobile/src/navigation/routes.ts) 无正式报告 route。
[ImportScreen](../apps/mobile/src/features/ImportScreen.tsx) 的分析概览是 Demo，AI 按钮禁用。
缺范围选择、独立分析授权、report controller/DTO/API、原文证据跳转与派生缓存清理。
新增端点也须更新 transport allowlist/OpenAPI 生成链，不能只增加 UI。

[Memory](../apps/server/app/agent/memory.py) 与 [memory_nodes](../apps/server/app/agent/memory_nodes.py)
的11R完整命令门禁、持久化前意图重验以及签名控制/确认流程永久保留。
MVP 分析入口 `memory_enabled=false`，不注入可用 Memory service，不召回、不提取、不写入、
不更改 consent/pause。导入正文不是当前用户命令；分析授权与报告临时保存均不授予 Memory 权限。

### 评估系统

[evals/agent](../evals/agent) 已有合成样本、Mock、有限真实执行、预算账本、哈希绑定人工评审与诊断。
可复用工具机制，不能复用通用问答总分作为产品验收。
消息级归因、三类沟通模式、反证、覆盖率和实际洞察价值须建立独立 `ica-eval-v1`；详见 MVP §8。

## 4. 最小产品边界

闭环为：**导入聊天 → 选择范围 → 明确授权 → 提取关键互动 → 三类洞察 → 原文证据 → 报告**。

第一版限定单 Owner、单 Person/Relationship、单 canonical Dataset 的双人文本；
在同一 Dataset 可选一个连续范围，或用于比较的两个明确时间窗，总计最多200条/48KiB正文。
长历史文件可以导入，第一版只对用户选中的有界切片负责，不宣传全史自动分析。
每类最多一项发现，不强制每类有结论；不足时明确说明需要哪些材料。

三类能力为：情绪表达与回应可能错位；分离互动中反复出现且在所选记录未见充分处理的冲突；
两个可比时段中的互动模式变化。第一版不做人格诊断、关系评分、爱意概率、动机测谎、
OCR/语音理解、多对象合并、聊天软件数据导出、自动发信、后台持续监测或模型敏感信息长期建档。
不默认引入 RAG、pgvector、Redis、队列或新的基础设施。

## 5. 版本化路线调整与阶段衔接

2026-10-28 的 [ICA 原计划](IMPORTED_CHAT_ANALYSIS_PLAN.md) 保留为历史 v1。
其中“11Q 通用质量通过后才可 ICA-A”与本次产品方向冲突。提出以下明确的 v2 替代方案：

1. 移除“先使通用问答人工评分达标”这一产品开发前置；允许匿名合成数据和 Mock 的 ICA-A先行。
   不移除安全、授权、删除或专项质量门槛；Phase11 原有 FAIL 原样保留。
2. 保留 ICA-A/B/C/D 名称作为产品里程碑，不重排 Phase0–12 编号，不将 ICA 改名为 Phase12。
   A=范围/授权/证据底座，B=三类洞察与报告全生命周期，C=Android，D=专项验收/最终回归。
3. 高风险角色错位建立独立 `SAFETY-ROLE-P1` 工作包，可与合成数据开发并行；
   **任何真实用户试用前必须关闭**，不能以一般分析能力或程序安全出口通过抵消。
4. 原 Phase12 的锁依赖、CI/CD、Docker/Compose、EAS preview、发布清单范围和编号不变，
   顺延至 ICA-D、P1关闭与最终完整 Root Verify 之后。Phase10 继续可选延后。

建议顺序：**本轮规划 → ICA-A → ICA-B → ICA-C → ICA-D → 原 Phase12**；
`SAFETY-ROLE-P1` 在 ICA-D 的真人试用准入前完成，若先改共用安全代码则提前定向回归。
每个子阶段单独授权、独立验收并停止，不把路线文档当作后续编码或付费请求授权。

本轮只提交此“正式路线修订建议”，不改 MASTER_PLAN 的 gate、阶段状态表或 verifier marker。
下一次明确采纳 v2 并授权 ICA-A 时，先在 MASTER_PLAN 增加有日期的路线说明及合同/ADR链接，
保留历史段落，仍不改 Phase11 QUALITY FAIL、Phase12 PENDING 或9/9H。
中间结果只能标注子阶段 READINESS/功能/专项质量结论；正式阶段 PASS 仍需 CODE/TEST/DOC/DEMO/REGRESSION。

v2 相对旧 proposal 的关键参数变化：支持显式双窗比较；临时报告由30天改为24小时；
真实请求上界由8改为9以计入可能的 Analysis/Action/Response 三次复核。
这些都是待 ICA-A 冻结的拟定合同，当前没有实现。

## 6. 独立安全工作包与下一步

`SAFETY-ROLE-P1` 的问题是：受害用户已退到安全处，却先看到面向潜在施害者的“放下物品/停止伤害”段落。
下一次独立授权后，仅调整角色适配、受控表达与发布校验接线，保留安全优先和最终验证。
对受害者、施害者、角色不明分别验证；角色不明用中性保护表达，历史引用/小说不自动归责现实用户。
新增冻结最小对照，覆盖当前危险/已安全/双向指控；全部检查实际 REST/SSE 用户可见文本，
严重归责错位和危险修复建议为零，真实人工复核。关闭后只记录该P1定向结论，不重评旧样本。

建议下一开发授权只包含 **ICA-A：可信范围、授权与消息级证据底座**，
具体任务、文件落点和验收见 MVP §9。该阶段使用合成数据/Mock，零真实模型请求，
不以通用 Agent 总体质量通过作为前置，不接收真实私人聊天。
本次实测发现的5项旧知识 Mock测试失败需在 A 中有限诊断/对齐，不能放宽安全 guard 来换绿。

## 7. 本轮验证与限制

以下为2026-10-29实际执行，不是引用旧 PASS，也不构成阶段验收。命令均在仓库根目录运行。

- `uv --cache-dir .cache/uv run --offline pytest -q apps/server/tests/test_chat_import.py apps/server/tests/test_agent_memory.py`
  → **30 passed**，仅离线导入/Memory。
- `uv --cache-dir .cache/uv --no-managed-python run --offline --locked pytest -q tests/test_skill_contract.py tests/test_phase11_quality_closeout.py --basetemp .cache/pivot-root-pytest`
  → **5 passed，59 subtests passed**。
- 设置 `PYTHONPATH=apps/server;.` 后运行
  `uv --cache-dir .cache/uv --no-managed-python run --offline --locked python apps/server/agent_demo.py`
  → exit0；独立 Mock Runtime 明确保存1条，并在另一会话召回1条。
  这是既有显式授权 Memory demo，不是导入分析 demo，也不涉及私人数据。
- `pnpm --filter @goutou/mobile test --runTestsByPath tests/connectedImport.test.ts tests/connectedHistory.test.ts tests/connectedImportUI.test.tsx tests/filePicker.test.ts tests/connectedMemory.test.ts tests/connectedMemoryUI.test.tsx tests/sessionIsolation.test.ts`
  → **7 suites / 134 tests passed**，仅 Jest。
- `uv --cache-dir .cache/uv run --frozen --offline pytest apps/server/tests/test_agent_analysis.py apps/server/tests/test_agent_knowledge.py apps/server/tests/test_llm_mock.py apps/server/tests/test_llm_openai_compatible.py apps/server/tests/test_eval_observability.py apps/server/tests/test_phase11r_contact.py -q`
  → **95 passed / 5 failed / 4 errors**。4项 error 为默认临时目录权限；最初不用 workspace cache
  的 `uv run --frozen --offline pytest` 同一文件清单也因默认 cache 初始化失败未启动测试。
  复跑 `uv --cache-dir .cache/uv run --frozen --offline pytest apps/server/tests/test_agent_knowledge.py --basetemp .cache/pytest-ica-runtime-audit -q --tb=short`
  → **13 passed / 5 failed，无 error**，原4项临时目录用例通过；两次有重叠，不能相加成独立总数。

5项失败是 `test_graph_semantic_mock_routes_and_loads` 的 personality/conflict/breakup/online 四个参数，
及 `test_user_prompt_cannot_request_arbitrary_files_or_all_references`，均返回 STRUCTURED_OUTPUT_FAILURE。
对 conflict 的直接图诊断证明 action_planner → review_content → provider.chat 缺少 Mock响应队列；
其余四项同根因仅为源码推断，尚未逐项证实。本轮不修产品或测试。

未配置 TEST_DATABASE_URL，未重跑签名 PostgreSQL/11R SQL canary；未执行 Android、真实DeepSeek、
Phase0–9全量或 `make verify` / `make.cmd verify`。遵照本轮范围，完整 Root Verify 留至最终收尾，
环境不可用与未执行均不记作通过。现有基础可复用，不等于当前回归全绿。

本轮完成后停止，等待下一步开发授权。
