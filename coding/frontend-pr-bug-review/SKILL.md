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
   - 按触发入口、根因位置、修复位置、回归测试的执行顺序解释 patch。
   - 每个代码链接使用固定到被审 commit SHA、带准确行号的 GitHub blob URL。
   - 未新增或未找到回归测试时直接说明，不生成虚构链接。
8. 模板化输出。
   - 完整读取 [references/output-template.md](references/output-template.md)。
   - 标题使用 PR 关联 issue 的编号；没有关联 issue 时按 template 规则回退到 PR 编号。
   - 只输出 `总结`、`风险项`、`Review 详情`，保持 template 的顺序和空状态。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审输出，供入口 skill 完整嵌入。
