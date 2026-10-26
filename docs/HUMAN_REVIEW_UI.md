# Phase11 本地人工评审界面

该工具只读取已有评测结果，不导入 Provider、不读 api.txt、不调用 DeepSeek。
不修改 Dataset、Agent、运行状态、模型输出、评分规则、历史自动评测或 Phase Marker。

从仓库根目录启动：

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked python scripts/human_review_ui.py --open
```

浏览器打开 http://127.0.0.1:8765/ 。如端口已占用，用 `--port 8766` 指定其他端口。
仅绑定本机127.0.0.1，不添加生产 API、依赖或基础设施。命令行 Ctrl+C 停止；
已保存的草稿可在下次启动时恢复。

## 使用方式

1. 首次输入真实姓名或可识别的评审署名。界面显示当前操作系统账户供核对，但
   不会把系统账户或 AI 名称自动当成真实人工评审。后续题目自动沿用你的署名。
2. 逐题查看原始用户问题、实际可见回答和 completed/failed 状态。失败案例显示
   原记录的错误代码和失败提示，没有成功回答，不展示中间分析作为补充回答。
3. 六项分数初始为空，需逐项选择1–5；完整英文锚点直接来自原评分包，中文仅为
   维度名称。automated_proxy 不出现在评分表单中，也不会自动代填。
4. 输入理由，点“保存草稿”可保留未完成输入；上一题、下一题及题号导航也保存
   当前草稿。点“保存本题并下一题”时，服务器校验六项分数、理由和署名，并记录
   实际提交时间（UTC ISO8601；界面按浏览器本地时间显示）。
5. 可返回任意题修改；修改后需重新提交本题。关闭页面前先保存草稿，尚未保存
   的修改会触发浏览器离开提醒。多窗口并发保存发生版本冲突时拒绝覆盖。
6. 全部15题提交后，点“生成评分 JSON 与人工评审汇总”。工具只更新各题的
   scores/reviewer/reviewed_at/reason；原来的 result、output_sha256、proxy、
   规则和顺序保持不变。

草稿位置：`.cache/human-review-ui/progress.json`，包含真实署名和人工意见，
默认被 Git 忽略。本工具不以登录系统证明现实身份；署名由实际操作的人填写。

完成后的产物：

- 更新 `evals/agent/results/human-review-15.json`。
- 生成 `evals/agent/results/human-review-summary.md`，包含六项均分、现有标准下的
  可接受比例、各题状态、分数、理由、署名和时间。
- 初始评分包备份为 `.cache/human-review-ui/original-human-review-15.json`。

生成文件前检查结果哈希、全部评分及原文件是否被外部修改；未完成时不覆盖正式
评分包。进度写入采用临时文件加原子替换。最终 JSON、报告及进度是分别落盘的
文件；若中途磁盘故障，草稿和原始备份保留，下次启动能识别已发布的同一评分
内容并再次生成报告。不可在确认恢复前删除进度目录。

人工评分完成也不自动宣布 Phase11 PASS：原20例运行完成率75%、结构有效率92%
仍未达门槛。历史 aggregate-final.json 和原验收报告不被自动覆盖。

## 本次定向验证

```powershell
uv --cache-dir .cache/uv --no-managed-python run --locked pytest -q --tb=short --basetemp=.cache/human-review-ui-tests-final tests/test_human_review_ui.py
node tests/human_review_ui.browser.cjs
```

7个 Python 测试通过；Chrome/Playwright 实际浏览器流程通过：空白分数、30条锚点、
失败展示、草稿保存/刷新/返回、全部15题填写/导出、署名与时间、手机宽度布局。
测试只在 `.cache` 下的临时副本写入明确标注的合成评分，从未向真实评分包代填。
浏览器测试复用仓库已安装的 Playwright 和系统 Chrome，可用已有
PLAYWRIGHT_CHROME_PATH 指定浏览器，不安装依赖。Ruff及格式检查通过。
未请求模型、未运行全项目测试。正式人工评分仍等待用户实际填写。
