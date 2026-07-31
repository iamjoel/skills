---
name: frontend-pr-bug-review
description: Review only frontend bug-fix changes in a pull request by describing the failure as a one-sentence test case, determining whether the patch fixes the root cause, identifying only root-cause or newly introduced risks, and explaining the repair through commit-pinned GitHub code links. Use when the user asks to review a frontend, web, UI, React, Next.js, browser, or client-side fix for a bug, defect, regression, incident, or broken behavior.
---

# 前端 PR Bug Review

围绕三个问题审查前端 Bug 修复：原问题是什么、是否从根因修复、是否引入新问题。最终只按 `output-template.md` 输出总结、风险项和结合代码的 Review 详情。

## 范围与路由

包含：

- 修复前端组件、hooks、状态、样式、i18n、浏览器逻辑和用户交互的改动；
- 被修复路径直接消费的共享类型、前端契约和测试；
- 为证明触发条件、根因和修复效果所必需的未修改前端调用方。

后端 endpoint、schema、错误码和服务实现只作为前端契约背景，不形成后端 review 结论。

独立调用时，如果没有前端 Bug 修复改动，输出 `No frontend bug-fix changes to review.` 并停止。由 `$frontend-pr-code-review` 根据 `fix:` 标题分发时，接受路由包中的前端 scope；若代码与修复意图不符，在风险项中用可证明的实际影响说明，不自行改派。

## Subagent 加速（可选）

- 主 review owner 必须读取完整前端 diff，并连续完成触发路径、根因、修复效果、风险准入和最终模板；这些核心判断不得拆分。
- 只有中大型 PR 存在至少两个独立取证任务时才使用 subagent。小型或强耦合修复由 owner 独立完成。
- PR 只解析一次并冻结 base/head SHA；subagent 使用同一只读 packet，不重新获取 PR，也不接收 owner 的疑似 finding。
- 只可分发：同一根因下的其他调用方搜索；正常/相邻路径回归与回归测试检查。
- subagent 只返回 candidate evidence 和未验证项，不判断根因是否修复、不选择风险类型、不生成模板、不修改外部状态。
- owner 必须回到冻结快照复核每条 candidate，并仅在满足 `risk-rubric.md` 全部条件时纳入风险项。

## 工作流

1. 读取 PR 上下文。
   - 定位 PR，读取标题、描述、关联 issue、前端 changed files、完整 patch、相关评论和检查状态。
   - 读取适用的项目指令、前端包配置和测试约定；更具体作用域的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、安装依赖、发布评论或改变 PR 状态。
2. 写出问题描述。
   - 从 issue、PR、测试和旧实现还原真实触发路径。
   - 逻辑问题使用：`在 <条件> 下，预期 <结果>，实际 <结果>。`
   - UI 问题使用：`在 <页面> 的 <位置>，<元素/布局/交互> 实际 <问题>，预期 <结果>。`
   - 保持一句话，不混入根因、实现或建议。
3. 定位根因。
   - 沿入口、状态、请求、副作用和渲染链路定位导致错误结果的最早错误决策。
   - 区分根因、放大因素和表面症状。
   - 检查相同 hook、共享组件、缓存键、契约或浏览器条件下的其他可达路径。
4. 判断当前修复。
   - 说明 patch 在哪个代码层做了什么，并压缩成一句“当前修复方式”。
   - 只有 changed logic 直接消除真实根因，并覆盖所有已证明受影响路径时，才把“从根因上修复”写为 `是`。
   - 只隐藏症状、吞错误、强制刷新/重置、添加局部 guard，或遗漏同根因路径时写为 `否`。
5. 检查新增问题。
   - 比较修复前后的正常路径、异常路径和相邻调用方。
   - 按实际适用性检查重复操作、快速切换、取消、卸载、重试、缓存、旧数据、权限、可访问性和布局。
   - 检查回归测试是否能在旧实现下失败、在新实现下通过；没有测试时只说明事实，不自动构造风险。
6. 形成风险项。
   - 完整读取 [references/risk-rubric.md](references/risk-rubric.md)。
   - 风险类型只能是 `没有从根因修复` 或 `引入了新的问题`。
   - 每项风险必须有 changed frontend code、真实触发路径、具体影响和可执行建议；证据不足时不输出风险。
7. 编写 Review 详情。
   - 按独立缺陷、根因或受影响路径拆成多个详情单元；每个单元都按触发入口、根因位置、修复位置、回归测试的执行顺序解释 patch，不要把不相关路径压缩成一个单元。
   - 建立内部 coverage ledger，把每个 changed frontend hunk 归入一个主详情单元或标为该单元的支撑改动；存在未覆盖 hunk 时继续审查，不得输出最终结果。
   - 每一步同时提供固定到被审 commit SHA、带准确行号的 GitHub blob URL，以及与链接行号一致的最小核心代码片段；代码逐字引用，通常保持 3–15 行，不用改写代码代替证据。
   - 未新增或未找到回归测试时直接说明，并省略该步的链接和代码块，不生成虚构证据。
8. 模板化输出。
   - 完整读取 [references/output-template.md](references/output-template.md)。
   - 标题使用 PR 关联 issue 的编号；没有关联 issue 时按 template 规则回退到 PR 编号。
   - 只输出 `总结`、`风险项`、`Review 详情`，保持 template 的顺序和空状态。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审输出，供入口 skill 完整嵌入。
