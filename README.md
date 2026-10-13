# 狗头军师 App

Phase 8A–8E 已完成工程验收：生成客户端、开发 JWT、真实资源、Agent REST/POST SSE、
聊天导入与分域历史、Memory 控制及受保护操作。Phase 8F 已完成 Android 原生收口，
Phase 8 为 PASS；Phase 9A 已完成，标记为 `8 / 9A`，Phase 9 整体保持 IN PROGRESS。
9A 状态、阶段标记与独立 pre/post 验证结果见 [9A 验收报告](docs/PHASE_9A_ACCEPTANCE.md)。
当前证据见 [Phase 8 Closeout Addendum](docs/PHASE_8_FINAL_ACCEPTANCE.md#closeout-addendum--2026-10-12)，
后续范围见 [Phase 9 交接](docs/PHASE_9_SECURITY_RELIABILITY_HANDOFF.md)。

这是将 [goutoujunshi Skill](https://github.com/shengjidaguai-china/goutoujunshi)
改造成独立 AI Agent 与 React Native 手机 App 的 Monorepo。目标架构为
React Native + Expo 客户端、FastAPI + PostgreSQL 服务端，以及可脱离任何
Agent Harness 独立运行的 LangGraph Agent。手机端不直接调用模型 API。

## 当前状态

Phase 0–6 已完成（Phase 6A–6D PASS）。当前有 83 个合成 Golden Cases、
独立 LangGraph Runtime、真实 JWT 的 Agent REST/SSE、显式绑定的聊天导入流水线，
以及 consent/查看/暂停/恢复、受保护撤销、确认删除、有限保留期和维护 CLI。
可用 Mock LLM 无密钥运行；真实模型的端到端语义质量尚未验证。
生产调度、备份轮换与恢复删除重放尚未部署。Phase 7A–7D 提供 Expo React Native
六页面骨架、Chat/Profile、导入向导、分域历史与 Memory 设置的本地演示。
Phase 7 已完成（7A–7D PASS），六页面集成与错误恢复已验证；详见最终验收报告。
Phase 8A 已实现服务端 Person/Relationship/Conversation 公共资源与 Agent 历史前置合同；
Phase 8B 接入 OpenAPI 生成客户端、开发 JWT 会话与真实 owned 资源；Demo 保留。
Phase 8C 已接入 Agent REST/SSE；8D 接入真实文件导入与关系聊天历史。
Phase 8E 已接入真实 Memory 控制、Guarded Undo/Delete 和持久回执。
Phase 8F 已关闭 SSE、资源创建、同键重试、Owner/Relationship 隔离、Memory 故障与重启、
Import/History 生命周期验收；16 个完整独立原生场景及全部已完成阶段回归通过。
完整矩阵与原始失败记录见 [Closeout Matrix](docs/PHASE_8F_CLOSEOUT_MATRIX.json)。
阶段状态以代码和验收结果为准，参见 [Master Plan](docs/MASTER_PLAN.md)
和 [Phase 6 最终验收报告](docs/PHASE_6_FINAL_ACCEPTANCE.md)、
[Phase 7A 验收报告](docs/PHASE_7A_ACCEPTANCE.md)、
[Phase 7C 验收报告](docs/PHASE_7C_ACCEPTANCE.md)、
[Phase 7 最终验收](docs/PHASE_7_FINAL_ACCEPTANCE.md)和
[Phase 8 API 交接清单](docs/PHASE_8_MOBILE_INTEGRATION_HANDOFF.md)。
资源、重试和生成输入见 [Public Resource API](docs/RESOURCE_API.md)与
[Phase 8A 验收报告](docs/PHASE_8A_ACCEPTANCE.md)。

## 目录

- `apps/mobile`：Expo 手机客户端六页面，Demo 与真实开发资源连接模式。
- `tools/api-codegen`：锁定生成器工具包；输出唯一 OpenAPI 权威对应的客户端。
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

Mobile 使用 Node 24.15.0（SDK 57 最低 22.13+）和仓库固定 pnpm 11.25.0，
依赖由根目录 `pnpm-lock.yaml` 锁定：

```powershell
pnpm --version
pnpm install --frozen-lockfile
pnpm --filter @goutou/mobile web
pnpm mobile:verify
```

`make verify` 同时运行 Mobile 静态/7D 集成门禁、真实 Web 导出与浏览器回归，
以及全部已完成后端阶段回归。Web 22 个场景通过；用户报告 Android 人工检查通过，
Codex 原生启动尝试因模拟器断连/无响应未完成，原生自动化与 APK 构建未运行。
Demo 界面明确标为演示，服务器发送消息、上传和编辑资料禁用。本地用户消息预览、
导入预检、历史增量窗口、Memory 预览、主题切换、导航与本地错误重试
有效；Demo 不显示服务器结果。Connected 使用真实资源、Agent REST/SSE 和导入/历史。
详细启动、Chrome smoke 和 Android 条件见 [Mobile 架构](docs/MOBILE_ARCHITECTURE.md)。

最终六页面 Demo 可复现：`pnpm --filter @goutou/mobile demo:final`，
按 Mobile README 配置 Chromium/Chrome。真实业务接入、账号资源与结构化分析 DTO
缺口见交接文档；App 尚未调用后端 Agent、导入或 Memory 服务。

Phase 6 独立端到端演示使用隔离 PostgreSQL 测试库（`TEST_DATABASE_URL` 数据库名
以 `_test` 结尾），真实本地 Uvicorn socket、签名 JWT 与 Mock LLM：

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked --env-file .env python apps/server/memory_phase6_e2e_demo.py
```

演示输出操作状态、计数、ID 和断言，不输出记忆内容、聊天或 JWT。

Phase 8A 的无真实模型密钥演示同样使用隔离测试库，真实 HTTP 创建三个资源、
重复创建重试、跨用户拒绝、现有 Agent 执行与正式历史读取：

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python apps/server/resource_api_demo.py
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/export_openapi.py --check
```

`docs/contracts/openapi.json` 是唯一 TypeScript 生成输入。`pnpm api:generate` 生成，
`pnpm api:check` 检测字节漂移并测试可复现性；不手改生成代码。
开发身份继续使用 development-only JWT CLI，生产账号系统仍未实现。

8B 开发接入：按 [开发会话](docs/MOBILE_DEV_AUTH.md)获取 15 分钟 CLI JWT，
Settings 中主动隐藏录入并验证，Relationship 页面创建/列出/查看三个资源。
Android/iOS 使用 SecureStore，Web 只存内存；过期/401/退出清除凭证及全部资源作用域。
公开配置包括 `EXPO_PUBLIC_API_BASE_URL` 和仅限 Android 开发验收的 Observer 开关，
不能放 JWT/模型/签名/数据库密钥；Release、iOS、Web 的 Observer 均关闭。
详见 [客户端](docs/MOBILE_API_CLIENT.md)、[资源与 Android 步骤](docs/MOBILE_RESOURCE_INTEGRATION.md)
和 [8B 验收](docs/PHASE_8B_ACCEPTANCE.md)。

`pnpm --filter @goutou/mobile smoke:connected` 使用隔离 PostgreSQL，实际 CLI JWT、
FastAPI 和 Chrome 验证资源、同 UUID 重试、分页与用户切换。Root verify 同时运行
旧 Demo 的 22 个浏览器场景和新 connected gate。8B 时 Android connected 为 NOT RUN，
该历史缺项已在 8F Closeout 用实际 Pixel_10/API37/Expo Go57 原生执行关闭。
Doctor/Android JS 导出仍不代替原生网络证据；流程见
[Android Closeout Procedure](docs/PHASE_8_FINAL_ANDROID_DEMO.md#closeout-procedure--2026-10-12)。

## 上游署名

使用的上游仓库为 `https://github.com/shengjidaguai-china/goutoujunshi`，
commit 为 `6db7354a4002dc7c448a9c87ffdad8132570c9d3`。上游采用 MIT
License，Copyright (c) 2026 powerycy。原版 [LICENSE](knowledge/goutoujunshi/LICENSE)
随 Skill 一起保留；更新上游需重新审阅并更新 manifest。
