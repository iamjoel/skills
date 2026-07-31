---
name: frontend-pr-code-review
description: Route a frontend pull-request review to exactly one specialist skill by matching title prefixes feat, fix, chore, and refactor, falling back to the PR's single dominant intent only when no supported prefix exists. Use when the user asks for a general frontend, web, UI, React, Next.js, browser, or client-side PR/code review and has not already selected a specialist review skill.
---

# 前端 PR Review 任务分发

为一个 PR 选择并启动一个专审 Skill，原样返回专审结果。

## 路由

| PR title type | 专审 Skill |
|---|---|
| `fix` | `$frontend-pr-bug-review` |
| `feat` | `$frontend-pr-feature-review` |
| `refactor` | `$frontend-pr-refactor-review` |
| `chore` | `$frontend-pr-chore-review` |

标题匹配使用：

```regex
^(feat|fix|chore|refactor)(\([^)]+\))?!?:
```

匹配大小写不敏感，允许 scope 和 breaking marker，例如 `feat(ui):`、`fix!:`、`refactor(core)!:`。type 必须位于标题开头。

## 工作流

1. 定位 PR。
   - 从用户提供的 URL、编号或当前分支定位 PR；无法唯一定位时请求 PR。
   - 先只读取并规范化 PR title。
2. 选择一个专审 Skill。
   - 标题命中受支持 type 时按表固定路由。
   - 只有标题未命中时，才读取选择单一主意图所需的最少 PR 描述、关联 issue、changed files 和必要 patch 上下文。
   - fallback 语义：恢复失效行为选 Bug；新增或有意改变行为选 Feature；保持行为的运行时代码重组选 Refactor；保持行为的工程维护选 Chore。
   - fallback 选择一个占主导地位的 Skill；混合意图无法确定时请用户选择。
3. 分发任务。
   - 启动一个专审 subagent，并把 PR 标识、标题、路由来源、用户约束和 fallback 所用的最少上下文传给它。
   - 在 subagent task 中明确写入：

     ```text
     Use `$<selected-specialist-skill>`.
     Resolve it from the active Codex skill catalog and read its `SKILL.md`
     completely before reviewing.
     ```

   - 用实际 Skill 名替换占位符，只传递路由依据。
4. 返回结果。
   - 等待选中的专审完成，并把它的最终输出原样返回。
   - 专审 Skill 不可用或无法读取时，报告对应 Skill 名称并停止。
