# ICA-B0/B1 匿名合成与 Mock 工程验收

日期：2026-11-04。基线HEAD：`d3025d1`。本报告所在提交为本轮交付版本；
逐文件实际工作区SHA256与汇总指纹见 [source-manifest.json](evidence/ica-b1/source-manifest.json)。
其指纹包含本轮源码、迁移、合同、冻结数据、OpenAPI和测试证据，另记录未变动的知识、依赖与正式Marker。

**ICA-B0 ENGINEERING READINESS PASS**

**ICA-B1 MOCK ENGINEERING READINESS PASS**

**ICA-BQ QUALITY PENDING / REAL USER READINESS NOT APPROVED**

这是用户“按照规划开始推进项目／继续”授权的首轮B0/B1工程交付，
不是整个ICA-B、产品上线或正式阶段通过。停止在Mock工程边界。
Marker保持9/9H；Phase11 QUALITY FAIL、原人工评分/失败、SAFETY-ROLE-P1、Phase10 DEFERRED、Phase12 PENDING均保留。
未运行完整Root Verify、Phase0–9历史全量、Android历史全集或真实模型评测。

## 1. 交付与复用

复用已通过ICA-A的JSONL/Markdown、canonical Dataset、范围规划、Core/halo、UUID/span证据和签名来源授权。
没有重写这些纯Python模块。行为基于冻结Skill，独立执行图不修改共用Agent行为。
合同见 [ICA_B0_CONTRACT](ICA_B0_CONTRACT.md)，参考复核见 [ICA_B0_B1_REFERENCE_REVIEW](ICA_B0_B1_REFERENCE_REVIEW.md)。

本轮修改清单以source-manifest中的`changed_files`为准，主要落点：

- `apps/server/app/agent/imported_analysis.py`、`imported_contracts.py`：独立LangGraph、受限Schema、三类发现、来源和反证校验。
- `apps/server/app/services/imported_execution.py`、`schemas/imported_execution.py`、现有API/config：独立执行challenge、确认、准入账本、结果读取。
- `db/models/imported_analysis.py`、models导出、`20261103_01_ica_execution.py`：临时Run、操作键、预算与writer围栏迁移。
- 现有`imported_analysis.py`服务、`erasure.py`、`lifecycle_erasure.py`、`backup_restore.py`：撤销/TTL/四域删除/restore派生数据联动。
- Mobile generated client、transport、`icaTransport.test.ts`、OpenAPI与export脚本：52个操作、独立默认关闭的执行开关；没有报告页面。
- `test_ica_cases.py`、`test_ica_runtime.py`、`test_ica_execution.py`、`test_ica_execution_lifecycle.py`：40个新增定向案例。
- `evals/ica/v1`：48份冻结合成案例、作者脚本、逐case与全文件hash。
- `.gitattributes`：冻结案例与原始证据字节保留，避免Windows自动换行转换破坏hash。
- MASTER_PLAN、ARCHITECTURE、v4路线及本轮合同/审查/验收、`docs/evidence/ica-b1`。

原有人工评分JSON、人工报告、human review UI及其他用户评测文件只读保留，不纳入本轮提交。
没有新增依赖、改变生产数据库或修改上游Skill快照。

## 2. 可执行行为与证据约束

所有K个Core安全检查完成才进入普通提取。有风险时保守退出，仅做独立内容复核；
角色保留actor、用户角色和当前/历史/引用/未知时态，未解决时不输出普通关系建议。
普通路径为互动候选→全部Core逐一检查所有候选反证→综合→独立内容复核。
零候选记录反证`not_applicable`，未执行阶段不伪造完成。

首版限三类：情绪表达与回应可能错位、分离互动中的重复问题、合法双窗的互动变化。
每项分开事实、推测、未知、替代解释、反证和可退出行动；允许零发现。
重复问题要求至少两次双方参与的分离episode且相隔24h；双窗有明确可比最低材料要求。
这些保守规则不是心理诊断或统计显著性证明。

提取只用本Core/halo，最终事实只能来自验证过的候选。引文逐项验证alias、真实UUID、speaker、
Python Unicode code-point半开span与quote；局部和最终引用均不能扩大授权范围。
漏反证、丢反证、使用已反驳候选、单边材料、伪造来源和内容复核拒绝均阻止报告发布。
内容复核是独立Mock协议调用，尚未证明真实模型能有效识别解释错误。
每次服务端读取还会重验当前grant和来源，纯Python快照不替代权限。

## 3. 签名 PostgreSQL 演示

实际运行完整FastAPI签名HTTP路由（TestClient/ASGI，非公网socket），使用真实JWT身份和PostgreSQL；
不是Mock Repository或SQLite。测试自动完成JSONL注册、上传、双方绑定、finalize/merge、来源prepare/confirm、
独立execution-prepare/confirm和真实LangGraph调用Mock队列。

- [900条/近3天](evidence/ica-b1/signed-demo-900.json)：K=5，Core=900，正文6300字节，双方各450条。
  无候选路径12次Mock调用；预留上界23次。
- [2100条/近7天](evidence/ica-b1/signed-demo-2100.json)：K=11，Core=2100，正文14700字节，双方各1050条。
  无候选路径24次Mock调用；预留上界41次。实际累计保守预留1,961,571，范围规划上限4,804,174。
- [有发现的双人合成互动](evidence/ica-b1/signed-finding.json)：1片、5次Mock调用，
  最终alias经签名evidence接口回查当前数据库UUID与原文；独立内容复核拒绝的第二次运行不发布报告。

900/2100样例为高密度单活跃日，范围内其余日期明确为0；没有假装每日均匀分布或导出完整。
实际UTC半开窗、时区、每日双方计数、来源缺口、scope/snapshot摘要均在证据JSON中。
未导出的聊天仍是未知。既有双窗、DST、时间逆序、同时间同正文不同UUID、媒体/系统、空日期、
10k有界读取及EXPLAIN测试在本轮重新通过；未重新做年度容量测试。

## 4. 授权、生命周期与并发

四个新增签名API均位于`/api/v1/imported-analysis`：

- `POST /execution-prepare`：原grant必须为Mock，绑定问题/范围/来源摘要、模型、预算、Runtime及Schema/知识路由hash，生成最多5分钟challenge。
- `POST /execution-confirm`：字面`true`、challenge/hash、当前来源均有效才创建独立可执行权限；只确认不调用模型。
- `POST /runs/{run_id}/execute`：服务端默认关闭，仅接受服务端安装的MockLLMProvider合成fixture；没有fixture就拒绝，不伪造成功。
- `GET /runs/{run_id}`：当前权限与来源再次验证后返回受限状态/报告。

原ICA-A确认不自动授予执行。两个Mobile transport开关独立，执行开关不开放来源或Memory权限。
运行没有任意查询工具、Memory读写或消息发送能力；导入文字和模型派生文字始终是不可信数据域。
真实服务测试在已有Memory记录且paused的状态下执行，并对HTTP控制状态与SQL记录进行前后核对，未发生变化。

Owner锁和短事务覆盖challenge消费、唯一操作键、执行claim、预算准入、结果落库及撤销；
不持有SQL锁等待模型。重复确认与执行不重复调用，失败也不自动重跑/重置预算。
发送前持久`admitted`提交是准入线性化点；撤销阻止后续准入和晚到结果发布，已经准入的Mock可能仍在途。
撤销清发布令牌但保留`writer_active`，执行真正settle才清活动标志；并发删除/恢复不能抢先假定执行停止。

Run TTL不超过原grant的24h。撤销、TTL、Dataset/Person/Relationship/Owner删除清除报告、别名、
执行绑定和派生明细；独立操作键/预算围栏保留以防旧请求复活。
Restore真实原生dump/restore测试验证清派生私密数据、当前执行writer隔离、归档后新操作键围栏与缺失证据拒绝放行。
不把报告复制到普通Conversation，原文只存在已有来源表。

限制：进程崩溃留下的活动writer需要未来受控恢复证明；本版不会自动清busy、自动续TTL或自动重放。
独立只读审查未发现可证实的核心越权或删除阻塞，仍不替代后续质量/生产审查。

## 5. 调用与费用

真实外部Provider调用数：**0**。没有DeepSeek或其他付费调用。
无候选`2K+2`；有候选最多`3K+2`；安全退出`K+1`；沿用v3`3K+8`总预留。
每次按最终序列化messages/Schema、JSON转义、halo和参考计输入字节，另加4096 framing与8192输出保守预留。
此计量不是实际tokenizer/usage。静态单片输入>128KiB在执行prepare时拒绝；动态后续超限失败并保留已消耗预算账本。
报告主体≤32KiB，持久派生扩展≤128KiB。费用0仅表示keyless Mock，没有以合成费率冒充真实报价。
ICA-A Preview中的`unquoted`历史预算原样保留，执行授权另绑定Mock零费率，不能用于真实模型准入。

## 6. 评测资料与未获批准项

48份匿名合成案例：16开发、32保留。每类普通能力10份，另有反证/缺口、安全角色时态、隐私/注入案例。
本轮只做结构、hash、身份、scope与Unicode来源校验，没有批量运行保留集并宣称模型成绩。
开发者能访问文件，尚未建立独立盲评保管。使用过的保留集须退为开发集，新版本再验收。

ICA-BQ仍待真实模型与独立人评：引用语义、precision、主要模式召回、反证检出、完成率、安全角色及用户价值。
原通用Agent的SAFETY-ROLE-P1和历史低人评分未关闭，本轮保守安全分支没有给它们重新打分。
普通“引用文字存在”不能证明推测成立。
Android报告、真实模型价格/预算、正式月/季/年父任务/事件索引/汇总与ICA-D发布验证均未实现。

## 7. 实际测试、错误与修复

最终后端：**255 passed in 124.48s**，其中40项为本轮新增，其余215项为ICA-A及相关回归。
[原始日志](evidence/ica-b1/backend-final.txt)。范围包括Parser/Import/Merge、签名SQL/keyset、
scope/challenge/跨Owner、Runtime/Unicode/反证、并发授权/撤销、TTL/四域删除、原生Restore、
11R两条Memory P0真实HTTP+SQL、既有Agent Runtime/knowledge和maintenance。
数据库迁移roundtrip测试降到`20261014_01`后升到head，包含本轮新Run表迁移及独立DB隔离。

Mobile相关**82项/5 suites PASS**，见[日志](evidence/ica-b1/mobile-tests.txt)。
TypeScript `tsc --noEmit`通过；OpenAPI确定性校验52 operations，原26项Phase7D合同保留；
client生成确定性/输入漂移/输出篡改**3项PASS**。变更Python的Ruff与Format **19文件PASS**，`git diff --check`通过。
[检查摘要](evidence/ica-b1/validation.json)。未运行无关历史全量或Android原生全套。

保留真实失败记录，不覆盖为绿：

- 首轮完整回归为254通过/1失败，见[原日志](evidence/ica-b1/backend-tests.txt)。
  超限测试原16,000个汉字经过JSON转义仍低于实际单片上限，因此返回200符合实现。
  改为12,000个emoji（来源48KiB，JSON转义超过128KiB），重新验证执行确认前拒绝；没有放宽预算。
- 早期并行集成时新Runtime文件未完成导致ModuleNotFoundError；完成模块后重跑。未以关闭节点解决。
- 新transport测试最初使用空UUID，生成类型拒绝；改为合法合成UUID，未放宽Schema。
- API导出脚本原固定48操作，新增4个真实路由后更新为52；仍逐项保留原26合同。
- Ruff长行与闭包捕获修正通过；没有关闭规则。当前原`test_agent_runtime.py`与knowledge测试全部通过，
  沿用ICA-A已确认的内容复核Mock队列修复，本轮未修改其共用Runtime或旧评分。
- 暂存时发现Windows autocrlf会重写冻结JSONL，补充局部字节保留属性；重新核对暂存blob与工作区hash，
  并重跑2项冻结案例结构测试通过。没有重生成或改写案例答案。
- 收尾连接检查误把模板名`ica_test`当已有数据库，得到“database does not exist”；
  fixture本来就是通过`postgres`创建随机后缀DB。改用`postgres`检查后连接正常，没有创建/修改未知库。

## 8. PostgreSQL环境与复现

复用ICA-A既有隔离PG16 ASCII路径/locale=C/UTF8方案，服务仅`127.0.0.1:15435`。
原Windows中文安装路径UTF8 byte0xb9诊断见 [ICA-A completion](ICA_A_V3_COMPLETION_ACCEPTANCE.md#postgresql-diagnosis-and-reproducibility)。
本轮没有重复initdb、改角色或碰生产。重新启动既有测试服务；Windows受限令牌启动失败时按原已批准路径启动一次。
实际版本PostgreSQL16.15。每次pytest在自建`ica_test_<随机>`库上迁移并在finally删除，
recovery测试另建独立库；结束查询确认剩余测试库0、活动测试连接0。
清理与服务停止证据见 [postgres-cleanup.json](evidence/ica-b1/postgres-cleanup.json)。

实际命令（PowerShell，仓库根目录；PG_BIN_DIR/basetemp按原隔离ASCII目录设置）：

```powershell
$env:PYTHONUTF8='1'
$env:UV_CACHE_DIR=Join-Path $PWD '.cache/uv'
$env:TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:15435/ica_test'
$env:PG_BIN_DIR='<isolated-pg16>/bin'
uv run --no-sync pytest apps/server/tests/test_ica_foundation.py apps/server/tests/test_ica_signed.py apps/server/tests/test_ica_execution.py apps/server/tests/test_ica_execution_lifecycle.py apps/server/tests/test_ica_runtime.py apps/server/tests/test_ica_cases.py apps/server/tests/test_chat_import.py apps/server/tests/test_import_jobs.py apps/server/tests/test_import_merge.py apps/server/tests/test_import_api.py apps/server/tests/test_phase11r_memory.py apps/server/tests/test_erasure.py apps/server/tests/test_full_erasure_9h.py apps/server/tests/test_full_restore_9h.py apps/server/tests/test_agent_runtime.py apps/server/tests/test_agent_knowledge.py apps/server/tests/test_data_lifecycle.py -q --tb=short --basetemp=<fresh-authorized-ASCII-directory>
pnpm --filter @goutou/mobile test -- tests/icaTransport.test.ts tests/connectedImport.test.ts tests/connectedImportUI.test.tsx tests/filePicker.test.ts tests/connectedHistory.test.ts
pnpm --filter @goutou/mobile typecheck
uv run --no-sync python scripts/export_openapi.py
pnpm api:check
```

最终源码与生成物对应本报告所在提交及raw-byte manifest。没有自动进入BQ/ICA-C/ICA-D/Phase12。
下一步建议是先处理独立保留集保管与SAFETY-ROLE-P1，再以明确总调用/费用上限开展ICA-BQ；
真实模型质量过关后才开发面向用户的正式报告交互。
