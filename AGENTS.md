# 项目总纲与工程规则

本仓库要把 `goutoujunshi` Skill 重构为可独立运行的 AI Agent Runtime，最终交付前后端分离的 React Native 手机 App。Agent 必须脱离 Codex、Claude Code、DeepSeek Harness 等宿主独立运行。`knowledge/goutoujunshi` 是行为规范的冻结快照；解释与实现写在本仓库的合同、代码和 ADR 中，不擅改上游。同步上游时记录 commit、更新哈希清单，并保留原 MIT 许可与署名。

## 每次工作开始前

1. 阅读本文件、`docs/MASTER_PLAN.md` 和 `docs/ARCHITECTURE.md`；修改 Agent 行为前再阅读 `docs/SKILL_CONTRACT.md`。
2. 检查 `git status` 和最近的 Git history，识别已有未提交工作并保护它。
3. 检查代码、测试与可运行结果，以仓库真实状态判定当前阶段；文档中的 `PASS` 标记不能代替验证。
4. 确定本次被要求完成的阶段。完成该阶段后停止，提交验收结果；除非用户明确要求，不自动进入下一阶段。

## 固定架构

- Mobile：React Native、Expo、TypeScript；作为客户端，通过 REST 和 WebSocket 调用后端。
- Backend：FastAPI、PostgreSQL；API 是 Agent Runtime 外部的 transport layer。
- Agent：LangGraph、结构化 State 和可独立调用的 Python API/CLI。关键流程拆为可单独测试的节点；节点不依赖 FastAPI Request/Response。
- Knowledge：保留原 `SKILL.md` 与 `references`；先按场景确定性路由并按需读取 1–3 篇参考。只有基线完成并评测后才考虑可选 RAG；`FEATURE_RAG=false` 必须可完整工作。
- 模型调用统一经过 `LLMProvider`，至少有 `chat`、`stream`、`structured_output`，并提供无需真实 API Key 的 Mock LLM。
- 所有 Agent、Prompt、Knowledge、Memory 与模型密钥在服务端。Mobile 不直接调用任何大模型 API，也不包含模型密钥。

## 实现边界

- 不把整份 `SKILL.md` 塞入一个 system prompt 后宣称完成 Agent 化。
- 不提前引入当前阶段无需求的 Redis、微服务、Kafka、Kubernetes、独立向量库等基础设施。
- 安全检查必须先于普通关系分析；事实、推测与未知分开，模型推测不得自动变成事实。
- 不保存模型隐藏的 chain-of-thought，不在日志中输出完整私人聊天或 access token。
- 长期记忆须经明确同意、按用户和对象隔离、限量且可查看、暂停、恢复和删除；未经同意写入次数为零，不把完整聊天记录存为长期记忆。
- `evals/golden_cases.jsonl` 是合成回归案例。变更行为时补充案例，优先用 Mock LLM 运行测试，不依赖真实密钥。
- 使用 `uv` 管理 Python、`pnpm` 管理 JavaScript/TypeScript；引入依赖时检查当前官方兼容性并提交 lockfile。
- 不覆盖用户已有未提交工作；外部服务、账号或密钥不可用时如实记录，继续完成不依赖它们的工作，不伪造成功。

## 阶段门槛

严格按 `docs/MASTER_PLAN.md` 的 Phase 0–12 顺序执行，不跳阶段。每阶段同时满足 CODE、TEST、DOC、DEMO、REGRESSION 才能标记完成：实现代码，运行相关自动化测试，更新文档，展示真实可运行的结果，并通过全部已完成阶段的回归验证。运行 `make verify`，记录命令、结果、关键架构决定、已知问题与验收报告；环境不支持的验证不能记作通过。可以提交时创建清晰的阶段 Git commit。完成当前阶段后停止，等待下一次明确指令。
