---
name: frontend-pr-code-review
description: Orchestrate and finalize a frontend pull-request code review by routing title prefixes feat, fix, chore, and refactor to matching specialist review skills, falling back to PR intent analysis only when no supported prefix exists, then reconciling findings and producing one unified verdict and review map. Use when the user asks for a general frontend, web, UI, React, Next.js, browser, or client-side PR/code review, or wants a consolidated result across specialist reviews. Do not use for an explicitly single-type review that directly names only a bug fix, feature, refactor, or chore.
---

# 前端 PR Code Review 编排与收口

作为前端 PR review 的唯一编排层。先读取 PR 标题：命中 `feat:`、`fix:`、`chore:`、`refactor:` 时直接分发给对应专用 skill；只有标题未命中任何受支持类型时，才解析 PR 意图并切分。专审完成后统一处理覆盖率、冲突、重复 findings、整体 correctness/verdict 和最终导航。

不要在本 skill 中复制四类专审的详细检查表。具体审查逻辑分别由：

- `$frontend-pr-bug-review`
- `$frontend-pr-feature-review`
- `$frontend-pr-refactor-review`
- `$frontend-pr-chore-review`

负责。

## 范围

只覆盖 PR 的前端改动：

- 前端运行时代码、组件、hooks、状态、样式、i18n、浏览器逻辑和测试；
- 被前端直接消费的共享类型、生成契约和 UI 包；
- 为理解前端行为所必需的未修改调用方与上下文。

后端 endpoint、schema、权限、错误码和服务实现只作为前端契约背景。不要对后端实现质量、数据库逻辑或服务架构形成 findings。

如果没有前端改动，输出 `No frontend changes to review.` 并停止。

## 编排工作流

1. 先确定标题路由。
   - 从用户提供的 URL、编号或当前分支定位 PR；无法唯一定位时请求 PR。
   - 首先只读取并规范化 PR title，完整读取 [references/routing-protocol.md](references/routing-protocol.md)。
   - 识别标题开头的 conventional type；允许可选 scope 和 breaking marker，例如 `feat(ui):`、`fix!: `。
   - 标题命中 `feat` 时选 Feature，命中 `fix` 时选 Bug，命中 `chore` 时选 Chore，命中 `refactor` 时选 Refactor。
   - 四种类型都未命中时，把 routing source 标记为 `fallback-analysis`。
2. 建立统一 PR 快照并识别前端范围。
   - 确定 routing source 后，再读取 PR 描述、关联 issue、changed files、完整 patch、评论和检查状态，用于实际 review。
   - 记录并冻结 base/head commit SHA；本次 review 的主 owner、专审和 subagent 必须使用同一快照，不重复解析或刷新 PR。
   - 读取适用的根级与目录级项目指令、前端包配置、测试约定和目录边界。按用户要求、作用域更具体的 `AGENTS.override.md`、`AGENTS.md` 和仓库 fallback 指令解析；更具体的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、发布评论或改变 PR 状态。
   - 根据仓库结构、manifest、构建配置和 import graph 判断前端文件，不要只依赖目录名。
   - 按前端 diff 单独计算规模和风险，不使用整个 PR 的总行数代替。
3. 分配前端改动。
   - 标题已命中时，把该 PR 的全部前端 changed hunks 交给一个对应专审；不要再解析 PR 内容来改派类型。
   - 只有标题未命中四种类型时，才按 PR 描述、issue、Before/After 和用户路径解析意图，为每个 changed frontend hunk 指定一个主类型：`bug | feature | refactor | chore`。
   - fallback 分类中同一文件可以包含多个切片，但同一 hunk 不得重复分发；支撑性改动跟随其服务的主切片。
4. 分发专审。
   - Bug 交给 `$frontend-pr-bug-review`；Feature 交给 `$frontend-pr-feature-review`；Refactor 交给 `$frontend-pr-refactor-review`；Chore 交给 `$frontend-pr-chore-review`。
   - 给每个专审传递统一 PR 上下文、适用项目指令、明确的切片清单、相关 changed hunks、必要的 unchanged context 和可运行验证边界。
   - 不向专审泄露其他专审的结论或预期 finding。
   - 完整读取 [references/subagent-protocol.md](references/subagent-protocol.md)。只有存在独立取证任务且预期收益高于调度成本时才启用 subagent。
   - 标题已命中的单类型 PR 始终只有一个对应专审 owner；owner 保留完整 diff、核心执行链、风险准入和最终模板，只把搜索、覆盖检查或独立验证交给 subagent。
   - fallback 多类型可以并行运行不同专审，但专审 subagent 不得递归再启动 agent；一次只并行一个层级。
   - 专审是只读任务。任何修复、评论发布或 PR 状态修改都需要用户另行明确授权。
5. 收集专审结果。
   - 把 subagent 返回内容视为 candidate evidence，不视为 finding 或结论；专审 owner 必须回到冻结快照复核 changed location、真实路径、影响和建议。
   - 要求每个专审返回其 scope、correctness、verdict、稳定 map IDs、findings、validation、not verified 和 residual risks。
   - 专审失败或结果不完整时先补跑缺失切片；仍无法覆盖时标为 `partial`，不得给出 `Approve`。
6. 聚合与裁决。
   - 完整读取 [references/aggregation-protocol.md](references/aggregation-protocol.md)。
   - 检查每个 changed frontend hunk 是否恰好有一个主 owner。
   - 去重同根因 findings，解决优先级或意图冲突，把真正跨类型的问题提升为总 review 的 `xN`。
   - 汇总测试与未验证项，计算整体 frontend correctness、verdict、risk 和 confidence。
7. 输出与导航。
   - 输出前完整读取 [references/output-protocol.md](references/output-protocol.md) 和 [references/output-template.md](references/output-template.md)。
   - 严格按照入口 template 输出统一收口；不要自创另一套格式。
   - 在 `Specialist Reviews` 中按 Bug、Feature、Refactor、Chore 的固定顺序，嵌入本次实际执行的每个专审完整 template 输出；未执行的类型省略。
   - 除聚合所需的稳定 ID 归一化外，不删减、重写或概括专审输出。
   - 用户回复稳定 ID 后，从已收集的专审结果展开；不要重新执行整个 PR review。
   - 同一次审查中保持所有 ID 稳定；新发现的单元只追加 ID。

## 分发边界

- `Bug`：恢复此前已预期但实际失效的行为，有具体缺陷或回归路径。
- `Feature`：新增能力或有意改变用户/客户端行为。
- `Refactor`：预期保持产品行为不变的运行时代码重组、抽取、迁移或优化。
- `Chore`：预期保持产品行为不变的依赖、构建、测试工具、codegen、CI、配置、文档和工程维护。

标题前缀是首要且权威的路由信号。只有 title 未命中 `feat/fix/chore/refactor` 时，才使用上述语义边界解析 PR。

## 整体判定

- `Request changes`：存在必须修复的正确性、安全、可访问性阻断或兼容性问题。
- `Comment`：存在非阻塞 finding、设计问题或重要未验证风险。
- `Approve`：所有实质前端切片已覆盖、没有 actionable findings，且验证足以支撑结论。

`Frontend correctness` 回答 patch 是否含 bug；`Frontend verdict` 回答是否阻塞合并。结论只覆盖 PR 的前端部分。

## 导航

- `bN`：Bug 修复路径。
- `fN`：Feature。
- `rN`：Refactor 单元。
- `cN`：Chore 单元。
- `bxN`、`fxN`、`rxN`、`cxN`：对应专审内部的跨单元项。
- `xN`：fallback 多路审查中的跨类型关注点。
- `<scope-id>.iN`：finding。
- `blockers`、`map`、`coverage`、`validation`、`all`、`next`、`prev`、`back`：按当前层级导航。

收到未知 ID 时，只返回合法 ID 的精简 Frontend Review Map，不重新执行审查。
