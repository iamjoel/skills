---
name: frontend-pr-chore-review
description: Review only frontend chore and engineering-maintenance changes in a pull request by stating the maintenance goal, determining whether the toolchain or configuration change is complete without unintended product behavior changes, identifying only incomplete-maintenance or newly introduced risks, and explaining the change through commit-pinned GitHub code links. Use when the user asks to review a frontend chore, dependency update, build or test tooling change, codegen update, CI or configuration change, documentation maintenance, or other engineering-only PR.
---

# 前端 PR Chore Review

围绕三个问题审查前端工程维护：维护目标是什么、目标是否完成且产品行为保持不变、是否引入新问题。最终只按 `output-template.md` 输出总结、风险项和结合代码的 Review 详情。

## 范围与路由

包含：

- 依赖、lockfile、Node 和包管理器版本；
- 构建、测试、lint、Storybook、codegen、CI、缓存和发布配置；
- 环境变量、浏览器目标、生成产物、工程文档及其他预期不改变产品行为的维护改动；
- 为验证工程链路和运行时影响所必需的前端消费者与上下文。

后端工具链只在被前端构建或测试直接消费时作为背景读取，不形成后端 review 结论。

独立调用时，如果没有前端 Chore 改动，输出 `No frontend chore changes to review.` 并停止。由 `$frontend-pr-code-review` 根据 `chore:` 标题分发时，接受路由包中的前端 scope；若代码与维护意图不符，在风险项中用可证明的实际影响说明，不自行改派。

## Subagent 加速（可选）

- 主 review owner 必须读取完整前端 diff，并连续完成维护目标、source of truth 到消费者的工程链路、最终影响、风险准入和最终模板；这些核心判断不得拆分。
- 只有中大型 PR 存在至少两个独立取证任务时才使用 subagent。小型或强耦合维护由 owner 独立完成。
- PR 只解析一次并冻结 base/head SHA；subagent 使用同一只读 packet，不重新获取 PR，也不接收 owner 的疑似 finding。
- 只可分发：manifest、lockfile、codegen 和生成产物一致性检查；CI、环境、缓存、命令和消费者覆盖检查。
- subagent 只返回 candidate evidence 和未验证项，不判断维护或行为是否完成、不选择风险类型、不生成模板、不修改外部状态。
- owner 必须回到冻结快照复核每条 candidate，并仅在满足 `risk-rubric.md` 全部条件时纳入风险项。

## 工作流

1. 读取 PR 上下文。
   - 定位 PR，读取标题、描述、关联 issue、前端 changed files、完整 patch、相关评论和检查状态。
   - 读取适用的项目指令、前端包配置、脚本和测试约定；更具体作用域的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、安装依赖、发布评论或改变 PR 状态。
2. 写出维护目标。
   - 从 PR、issue、旧配置和工程命令提炼要替换或同步的依赖、工具、配置、产物或文档，以及必须保持的不变量。
   - 使用一句话：`将 <旧依赖/工具/配置/产物> 维护为 <新状态>，并保持 <产品、构建、测试或发布不变量> 不变。`
   - 不把版本号或文件更新本身当作目标。
3. 建立工程链路。
   - 区分 source of truth、生成产物和消费者。
   - 沿 manifest、lockfile、配置入口、脚本、CI、缓存、产物和运行时消费方验证本地与 CI 路径。
   - 按实际适用性检查 Node、包管理器、OS、SSR、production build 和浏览器兼容性。
4. 判断维护是否完成。
   - 说明 patch 如何同步依赖、配置、命令或产物，并压缩成一句“当前维护方式”。
   - 检查 manifest/lockfile、source/generated files、脚本/CI、文档/实际命令和所有消费方是否一致。
   - 只有目标状态已落地，相关工程路径已同步且没有仍可达的新旧分叉时，才把“完成维护目标”写为 `是`。
5. 判断产品行为是否保持。
   - 比较维护前后的构建输出、运行时依赖、环境变量、浏览器目标和用户可见结果。
   - 只有可证明的不变量均保持，且没有合格的新增问题时，才把“产品行为保持”写为 `是`。
   - 检查验证是否能覆盖 clean checkout、构建、测试或生成链路；没有测试或无法运行时只说明事实，不自动构造风险。
6. 形成风险项。
   - 完整读取 [references/risk-rubric.md](references/risk-rubric.md)。
   - 风险类型只能是 `没有完成维护目标` 或 `引入了新的问题`。
   - 每项风险必须有 changed frontend config/code、真实工程或用户路径、具体影响和可执行建议；证据不足时不输出风险。
7. 编写 Review 详情。
   - 按独立的依赖、配置、工具、生成或发布职责拆成多个详情单元；每个单元都按维护前状态、维护改动、消费或工程链路、验证的顺序解释 patch，不要按文件机械拆分或把不相关维护压缩成一个单元。
   - 建立内部 coverage ledger，把每个 changed frontend hunk 归入一个主详情单元或标为该单元的支撑改动；存在未覆盖 hunk 时继续审查，不得输出最终结果。
   - 每一步同时提供带准确行号的 GitHub blob URL，以及与链接行号一致的最小核心代码片段；维护前状态固定到 base SHA，其余固定到 head SHA。代码逐字引用，通常保持 3–15 行，不用改写代码代替证据。
   - 未新增或未找到验证时直接说明，并省略该步的链接和代码块，不生成虚构证据。
8. 模板化输出。
   - 完整读取 [references/output-template.md](references/output-template.md)。
   - 标题使用 PR 关联 issue 的编号；没有关联 issue 时按 template 规则回退到 PR 编号。
   - 只输出 `总结`、`风险项`、`Review 详情`，保持 template 的顺序和空状态。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审输出，供入口 skill 完整嵌入。
