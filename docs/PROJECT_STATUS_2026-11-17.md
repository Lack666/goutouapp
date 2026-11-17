# 项目完成情况核对与介绍交付记录

日期：2026-11-17（Asia/Shanghai）。核对基线 HEAD：`e9216180770a6e878b2247061de8fd7313ec7e81`。

## 结论

**Phase 0–9 历史工程验收已完成，正式标记仍为9/9H；Phase11质量FAIL、可选Phase10暂缓、Phase12待开始。** 后续 ICA-A / B1 / R1 已实现工程能力，ICA-BQ-v2真实评测仍FAIL/PARTIAL，不能将这些定向结果视为产品整体通过。

本次更新README与[项目全景介绍](PROJECT_OVERVIEW.md)，并实际执行无付费模型的核对。没有启动新阶段、改变Agent行为或修改正式标记。向GitHub上传工程资料，不代表App上线。

## 阶段完成矩阵

| 阶段 | 已交付 | 当前结论 |
| --- | --- | --- |
| 0 | 仓库、上游审计、monorepo、验证入口 | 历史PASS |
| 1 | Skill行为合同、合成Golden Cases | 历史PASS；当前Golden库存83例 |
| 2 | FastAPI、PostgreSQL、SQLAlchemy/Alembic、Provider | 历史PASS |
| 3 | 独立LangGraph、安全/FIU/知识/分析/行动/回答/Memory/流事件 | 历史PASS；本次独立Mock Demo成功 |
| 4 | AgentService、签名REST/POST SSE、操作幂等 | 历史PASS |
| 5 | 解析、导入Job、绑定、合并、历史API | 历史PASS；后续增加JSONL互操作 |
| 6 | Memory授权、查看、暂停/恢复、撤销、删除、保留 | 历史PASS；后续保留Memory P0修复证据 |
| 7 | Expo六页面与本地Demo | 历史PASS |
| 8 | 真实API客户端、开发身份、对话/导入/历史/Memory接入 | 历史PASS，包含历史Android验收 |
| 9 | 安全、资源准入、生命周期、删除、受证明的运行恢复 | 历史PASS至9H；生产准入未批准 |
| 10 | 可选hybrid RAG/pgvector | OPTIONAL / DEFERRED，非现状能力 |
| 11 | 评测、观测、人工工具和多轮有限修复 | 工具已实现，QUALITY FAIL，统一回归待收尾 |
| ICA-A | 范围预览/确认、覆盖、证据、撤回、TTL和删除恢复 | 工程完成，见独立验收 |
| ICA-B1/R1 | Mock执行、反证、报告、生命周期、quote-v2 | 定向工程PASS；产品默认关闭且Mock-only |
| ICA-BQ-v2 | 新合成保留集、一次真实预算批次、人评包 | QUALITY FAIL / PARTIAL，人评PENDING |
| ICA-C/长周期/ICA-D | 手机报告体验、月季年容量、统一终验 | 未完成 |
| 12 | CI/CD、EAS、发布准备 | PENDING |

历史依据：[MASTER_PLAN](MASTER_PLAN.md)、[9H验收](PHASE_9H_ACCEPTANCE.md)、[Phase9最终验收](PHASE_9_FINAL_ACCEPTANCE.md)、[11质量收尾](PHASE_11_QUALITY_CLOSEOUT.md)、[ICA-A完成](ICA_A_V3_COMPLETION_ACCEPTANCE.md)、[B1](ICA_B1_ACCEPTANCE.md)、[R1](ICA_BQ_R1_ACCEPTANCE.md)、[BQ-v2](ICA_BQ_V2_ACCEPTANCE.md)。

README、Mobile README和架构文档原先混有多个阶段的历史边界。本次入口说明采用最新源码与相应验收；不改写原阶段报告、既有评分或失败证据。

## 当前质量证据

| 批次 | 数据与结果 | 限制 |
| --- | --- | --- |
| Phase11独立评测 | 普通完成14/20（70%）；去重人工可接受8/28（28.57%）；主人评2/15 | 历史冻结批次，不能代表修复后最新总体质量，也不能省略其失败 |
| 11R等有限修复 | 存在TARGETED PASS及真实小批次接线证据 | 不是对全部场景独立质量重评 |
| ICA-BQ-v2 | event普通10/22、baseline9/22；总28 completed / 34 failed / 2 not_run | 两臂均低于95%门槛；仅19份普通可读报告 |
| ICA-v2调用与预算 | 233次实际调用，0重试/未知；预留¥19.935784，按冻结usage估算¥1.87753784 | 历史费用估算，不是结算发票或当前报价；本次不重复调用 |
| ICA-v2人评 | 64条保留，可读报告及空评分包已导出 | 正式人工字段仍null；待真人诊断，不能补救失败完成率 |

主要未解决项是生成完成率、统计与来源校验、内容复核、少量结构/窗口错误及人工接受度。源码已经存在某项机制，不代表其真实模型效果已达到门槛。

## 本次实际验证

所有以下命令均在当前工作区执行。日志见[本次证据目录](evidence/project-overview-2026-11-17/)。本次外部Provider调用0，不使用真实聊天，不申请新模型预算。

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 根门禁 | `.\make.cmd verify` | **exit1**，`FAIL: 9H current-source/baseline scope drift` |
| 后端定向离线 | `uv --cache-dir .cache/uv --no-managed-python run --locked --offline pytest @overviewTests -q --basetemp=.cache/pytest-overview-20261117` | **309 passed in6.71s** |
| Mobile类型 | `pnpm --filter @goutou/mobile run typecheck` | exit0 |
| Mobile单元/UI | `pnpm --filter @goutou/mobile test` | **29 suites / 413 tests PASS**，21.553s |
| OpenAPI | `uv --cache-dir .cache/uv --no-managed-python run --locked --offline python scripts/export_openapi.py --check` | **52 operations**；原26合同保留 |
| 生成客户端 | `pnpm api:check` | **3 tests PASS**，生成字节可复现 |
| 独立Runtime | `uv --cache-dir .cache/uv --no-managed-python run --locked --offline python apps/server/agent_demo.py` | exit0；首会话保存1条Memory，新会话召回1条并给出回答 |

后端17文件选择清单、环境设置与命令见[commands.ps1](evidence/project-overview-2026-11-17/commands.ps1)。这309项包含Runtime、Knowledge、安全角色、ICA基础/执行、quote-v2、评测准入和人评工具；HTTP模拟使用MockTransport，不是新一轮真实Provider评测。

另一只读审计先跑Runtime/Knowledge/quote/安全角色74项并通过，它们与309项重叠，不重复累加为383。Mobile、API和后端各类测试也不折算成功能完成百分比。

### 根验证为什么失败

`scripts/check_security_9h.py`在运行完整测试前检查9H矩阵中的源码指纹。历史9H矩阵绑定其完成时源码，后续Phase11/ICA已经增加或修改Runtime、服务、LLM、删除链路、OpenAPI和测试；现有用户未提交的`human_review_ui.py`也在指纹范围。因此当前源码不能继续复用旧指纹声称全量通过。

本次保留检查失败，不更新历史矩阵/哈希来绕过。失败不是新发现的运行时业务断言失败，因为根命令尚未执行到后续测试；但也意味着当前完整回归没有通过。后续需要按明确范围重新执行并绑定当前证据。

### 环境与初次失败

- pnpm初次因沙箱不能读取用户AppData临时目录而EPERM，尚未进入TypeScript/Jest/codegen。将当前进程`TEMP`和`TMP`设为工作区`.cache/tmp-overview`后成功，不更改系统设置或依赖。
- 独立Demo裸命令最初缺少仓库根的Python导入路径；增加`PYTHONPATH=.;apps/server`及`PYTHONUTF8=1`后exit0。独立API不依赖开发宿主，但需要正常模块导入配置。
- 审计74项首轮默认Windows Temp有4个setup error；使用工作区专用`--basetemp`后通过。主309项从开始即使用专用目录。

**本次未运行**：新一轮签名PostgreSQL全套、真实Web浏览器全套、Android/iOS设备测试、真实Provider评测、EAS构建或公网部署。这些不能登记为本次PASS。历史2026-10-21的13个新Android场景及当时完整回归保留为历史证据。

## 尚未完成与建议顺序

1. 在明确有限范围内处理Agent和ICA已知质量缺陷，保留原失败，再冻新独立案例与人工量表；真实调用需单独具体预算授权。
2. 验收ICA真实模型质量和授权执行路径，补手机端范围/成本确认、报告、反证及原文查看。
3. 按独立门槛验收月/季/年容量、全范围安全、事件与摘要来源链；日期范围不能代替容量和质量证明。
4. 完成ICA-D、Phase11和全部历史阶段当前源码回归，满足CODE/TEST/DOC/DEMO/REGRESSION。
5. 补生产身份、监控维护、独立灾备和删除传播等准入条件，再进入Phase12 CI/CD、EAS及正式发布。

这是剩余事项说明，不是本轮启动这些阶段的授权。最终目标及技术路线见[全景介绍](PROJECT_OVERVIEW.md)。

## 工作区保护与上传范围

开始时存在2个已修改文件与4个未跟踪文件：`evals/agent/results/human-review-15.json`、`scripts/human_review_ui.py`、`docs/PHASE_11R_HUMAN_REVIEW_REPORT.md`及3份人工评分/摘要材料。本轮保持其内容，不纳入本轮文档提交，也不将未提交评分改成正式质量结论。

上传目标由用户明确指定为`Lack666/goutouapp`。本轮提交README、全景介绍、本状态记录及本次核对证据；工程既有提交历史随正常Git推送保留，不强推或覆盖未知远端内容。`.env`和`api.txt`已忽略，未纳入提交。

上传前检查当前/历史blob及11份源码ZIP，未命中常见Provider/GitHub token、JWT或私钥字面量；最大历史blob约5.68MB，无100MB文件障碍。检查存在模式覆盖局限，不是全部隐私认证。既有证据含本地文件路径元数据；本次不为清理路径改写历史证据。

GitHub认证和实际推送结果以交付时操作结果为准，不预填上传成功。
