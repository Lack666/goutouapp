# 狗头军师 App

这是将 [goutoujunshi Skill](https://github.com/shengjidaguai-china/goutoujunshi)
改造成独立 AI Agent 与 React Native 手机 App 的 Monorepo。目标架构为
React Native + Expo 客户端、FastAPI + PostgreSQL 服务端，以及可脱离任何
Agent Harness 独立运行的 LangGraph Agent。手机端不直接调用模型 API。

## 当前状态

Phase 0–6 已完成（Phase 6A–6D PASS）。当前有 83 个合成 Golden Cases、
独立 LangGraph Runtime、真实 JWT 的 Agent REST/SSE、显式绑定的聊天导入流水线，
以及 consent/查看/暂停/恢复、受保护撤销、确认删除、有限保留期和维护 CLI。
可用 Mock LLM 无密钥运行；真实模型的端到端语义质量尚未验证。
生产调度、备份轮换与恢复删除重放尚未部署。React Native 客户端为 Phase 7。
阶段状态以代码和验收结果为准，参见 [Master Plan](docs/MASTER_PLAN.md)
和 [Phase 6 最终验收报告](docs/PHASE_6_FINAL_ACCEPTANCE.md)。

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
`.\make.cmd verify`。完整验证需要按
[数据库操作说明](docs/DATABASE.md)配置隔离的 PostgreSQL 测试库。

配置模板见 [.env.example](.env.example)。只在服务端使用真实密钥；本地
`.env` 已被 Git 忽略，不提交。运行时 Python 依赖由 `uv.lock` 锁定。

Phase 6 独立端到端演示使用隔离 PostgreSQL 测试库（`TEST_DATABASE_URL` 数据库名
以 `_test` 结尾），真实本地 Uvicorn socket、签名 JWT 与 Mock LLM：

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/memory_phase6_e2e_demo.py
```

演示输出操作状态、计数、ID 和断言，不输出记忆内容、聊天或 JWT。

## 上游署名

使用的上游仓库为 `https://github.com/shengjidaguai-china/goutoujunshi`，
commit 为 `6db7354a4002dc7c448a9c87ffdad8132570c9d3`。上游采用 MIT
License，Copyright (c) 2026 powerycy。原版 [LICENSE](knowledge/goutoujunshi/LICENSE)
随 Skill 一起保留；更新上游需重新审阅并更新 manifest。
