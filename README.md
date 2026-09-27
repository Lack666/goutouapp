# 狗头军师 App

这是将 [goutoujunshi Skill](https://github.com/shengjidaguai-china/goutoujunshi)
改造成独立 AI Agent 与 React Native 手机 App 的 Monorepo。目标架构为
React Native + Expo 客户端、FastAPI + PostgreSQL 服务端，以及可脱离任何
Agent Harness 独立运行的 LangGraph Agent。手机端不直接调用模型 API。

## 当前状态

Phase 0–3 已完成：后端基础、81 个合成 Golden Cases，以及包含安全、场景、
FIU、知识路由、关系分析、行动建议、受控长期记忆和类型化进度事件的独立
LangGraph Runtime。可用 Mock LLM 无密钥运行；真实模型的端到端语义质量尚未
验证。Agent Service/API transport 与 React Native 客户端仍待后续阶段。
阶段状态以代码和验收结果为准，参见 [Master Plan](docs/MASTER_PLAN.md)
和 [Phase 3 验收报告](docs/PHASE_3H_ACCEPTANCE.md)。

## 目录

- `apps/mobile`：未来的 Expo 手机客户端。
- `apps/server`：FastAPI/PostgreSQL 基础、LLM Provider 与独立 Agent Runtime。
- `knowledge/goutoujunshi`：未修改的上游 Skill 内容。
- `knowledge/upstream-manifest.json`：上游仓库、commit、License 和文件哈希。
- `docs`：架构方向、Skill Contract、ADR 与阶段验收。
- `evals`：匿名合成 Golden Cases 和标注验证器。
- `scripts`：仓库验证脚本。

## 本地开发入口

需要 Python 3.12+、uv、Node.js、pnpm 和 Git；Docker 从服务端阶段开始使用。
在有 GNU Make 的系统运行 `make doctor`，在 Windows PowerShell 运行
`.\make.cmd doctor`。当前阶段的完整回归命令是 `make verify` 或
`.\make.cmd verify`。Phase 3 的完整验证需要按
[数据库操作说明](docs/DATABASE.md)配置隔离的 PostgreSQL 测试库。

配置模板见 [.env.example](.env.example)。只在服务端使用真实密钥；本地
`.env` 已被 Git 忽略，不提交。运行时 Python 依赖由 `uv.lock` 锁定。

## 上游署名

使用的上游仓库为 `https://github.com/shengjidaguai-china/goutoujunshi`，
commit 为 `6db7354a4002dc7c448a9c87ffdad8132570c9d3`。上游采用 MIT
License，Copyright (c) 2026 powerycy。原版 [LICENSE](knowledge/goutoujunshi/LICENSE)
随 Skill 一起保留；更新上游需重新审阅并更新 manifest。
