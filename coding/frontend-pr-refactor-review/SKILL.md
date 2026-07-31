---
name: frontend-pr-refactor-review
description: Review only behavior-preserving frontend refactors in a pull request by stating the refactor goal, determining whether the patch completes that goal without changing observable behavior, identifying incomplete-refactor, newly introduced, code-quality, and performance risks, explaining the old-to-new structure through commit-pinned GitHub code links, and running a dedicated Vercel React Best Practices subagent review. Use when the user asks to review a frontend, web, UI, React, Next.js, browser, or client-side refactor, cleanup, extraction, migration, or internal rewrite that should not change user behavior.
---

# 前端 PR Refactor Review

围绕三个问题审查前端重构：重构目标是什么、目标是否完成且行为保持不变、是否引入新问题；另用独立 subagent 检查 Vercel React Best Practices。最终只按 `output-template.md` 输出总结、风险项和结合代码的功能 Review；经复核的代码质量与性能问题归入风险项。

## 范围与路由

包含：

- 重组、抽取、迁移或清理前端组件、hooks、状态、样式、i18n、浏览器逻辑和测试；
- 被重构直接消费的共享类型、前端契约和 UI 包；
- 为比较行为、依赖方向和迁移完整性所必需的未修改前端调用方。

后端 endpoint、schema、错误码和服务实现只作为前端契约背景，不形成后端 review 结论。

独立调用时，如果没有行为保持型前端重构，输出 `No frontend refactor changes to review.` 并停止。由 `$frontend-pr-code-review` 根据 `refactor:` 标题分发时，接受路由包中的前端 scope；标题或描述与代码不一致本身不构成风险，只有能证明具体影响时才输出。

## Vercel React Best Practices Subagent（必执行）

- 每次 review 都启动一个独立 subagent，并把以下指令原样放入 subagent task：

  ```text
  Use `$vercel-react-best-practices`.
  Resolve it from the active Codex global skill catalog and read its `SKILL.md`
  completely before reviewing.
  ```
- subagent 使用 owner 已冻结的 base/head SHA、assigned frontend diff、适用项目规则和必要上下文；不得重新获取 PR、修改代码、发布评论或改变 PR 状态。
- subagent 完整读取该 skill，并只加载与本次改动相关的 rule files；检查所有 assigned 改动后返回问题、head commit GitHub 代码链接、逐字核心代码、修复建议和命中的 rule。
- 没有适用的 React/Next.js 改动或没有发现问题时也必须明确返回，不得为了填充输出制造问题。
- owner 必须复核每项问题确由本次 changed code 引入、规则适用、代码链接和片段准确，去重并分类为 `代码质量问题` 或 `性能问题` 后写入 `风险项`。
- 没有具体影响的偏好或泛化建议不得写入风险项；准入条件以 `risk-rubric.md` 为准。
- subagent 无法执行时不得静默跳过；把原因记录到 `not_verified`，由入口 review 纳入最终验证说明。

## 其他 Subagent 加速（可选）

- 主 review owner 必须读取完整前端 diff，并连续完成旧新结构、行为不变量、等价性判断、风险准入和最终模板；这些核心判断不得拆分。
- 只有中大型 PR 存在至少两个独立取证任务时才使用 subagent。小型或强耦合重构由 owner 独立完成。
- PR 只解析一次并冻结 base/head SHA；subagent 使用同一只读 packet，不重新获取 PR，也不接收 owner 的疑似 finding。
- 只可分发：旧 API、import、re-export、调用方、mock 和 story 的迁移残留搜索；公共契约与等价性测试检查。
- subagent 只返回 candidate evidence 和未验证项，不判断重构或行为是否完成、不选择风险类型、不生成模板、不修改外部状态。
- owner 必须回到冻结快照复核每条 candidate，并仅在满足 `risk-rubric.md` 全部条件时纳入风险项。

## 工作流

1. 读取 PR 上下文。
   - 定位 PR，读取标题、描述、关联 issue、前端 changed files、完整 patch、相关评论和检查状态。
   - 读取适用的项目指令、前端包配置和测试约定；更具体作用域的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、安装依赖、发布评论或改变 PR 状态。
2. 写出重构目标。
   - 从 PR、issue、旧实现和测试提炼旧结构的具体问题，以及新结构要达到的结果。
   - 使用一句话：`将 <旧职责/重复路径/耦合> 重构为 <新结构>，并保持 <关键用户或客户端行为> 不变。`
   - 不把文件移动、改名或“代码更干净”本身当作目标。
3. 建立行为不变量。
   - 按实际适用性比较渲染、事件、状态、请求、副作用、错误、可访问性、性能和前端契约。
   - 从旧实现、调用方和测试中取证；无法证明的行为不要凭个人偏好补成要求。
4. 判断重构是否完成。
   - 说明 patch 如何重新分配职责、收窄接口或消除重复，并压缩成一句“当前重构方式”。
   - 搜索静态与动态 import、re-export、注册入口、调用方、测试、mock 和 story，检查迁移、兼容层与死代码。
   - 只有目标结构已落地、相关调用方已迁移且旧的多源实现不再造成分叉时，才把“完成重构目标”写为 `是`。
5. 判断行为是否保持。
   - 沿真实用户和客户端路径比较重构前后的条件、顺序、状态生命周期、请求参数、错误恢复、焦点和副作用。
   - 只有可证明的不变量均保持，且没有合格的新增问题时，才把“行为保持”写为 `是`。
   - 检查等价性测试是否能覆盖旧、新实现的相同行为；没有测试时只说明事实，不自动构造风险。
6. 执行 React 最佳实践专审。
   - 按“Vercel React Best Practices Subagent（必执行）”启动专用 subagent，并等待其完成。
   - 复核、去重并把合格结果分类为 `代码质量问题` 或 `性能问题` 风险；不得用该结果替代结构迁移和行为等价审查。
7. 形成风险项。
   - 完整读取 [references/risk-rubric.md](references/risk-rubric.md)。
   - 风险类型只能是 `没有完成重构目标`、`引入了新的问题`、`代码质量问题` 或 `性能问题`。
   - 每项风险必须有 changed frontend code、真实触发或消费路径、具体影响、GitHub 代码链接与核心片段，以及可执行建议；证据不足时不输出风险。
8. 编写功能 Review。
   - 按独立的重构职责、迁移边界或行为不变量拆成多个详情单元；每个单元都按旧结构、新结构、调用方迁移、等价性测试的顺序解释 patch，不要按文件机械拆分或把不相关重构压缩成一个单元。
   - 建立内部 coverage ledger，把每个 changed frontend hunk 归入一个主详情单元或标为该单元的支撑改动；存在未覆盖 hunk 时继续审查，不得输出最终结果。
   - 每一步同时提供带准确行号的 GitHub blob URL，以及与链接行号一致的最小核心代码片段；旧结构固定到 base SHA，其余固定到 head SHA。代码逐字引用，通常保持 3–15 行，不用改写代码代替证据。
   - 未新增或未找到等价性测试时直接说明，并省略该步的链接和代码块，不生成虚构证据。
9. 模板化输出。
   - 完整读取 [references/output-template.md](references/output-template.md)。
   - 标题使用 PR 关联 issue 的编号；没有关联 issue 时按 template 规则回退到 PR 编号。
   - 只输出 `总结`、`风险项`、`功能 Review`，保持 template 的顺序和空状态。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审输出，供入口 skill 完整嵌入。
