# Frontend Review Subagent Protocol

每个专审都使用一个强制的 Vercel React Best Practices subagent；其他 subagent 只用于加速独立取证。任何 subagent 都不拆分核心审查推理。

## 强制 Vercel React Best Practices 任务

每个 Bug、Feature、Refactor、Chore 专审都必须：

1. 启动一个独立 subagent，并把以下指令原样放入 subagent task：

   ```text
   Use `$vercel-react-best-practices`.
   Resolve it from the active Codex global skill catalog and read its `SKILL.md`
   completely before reviewing.
   ```
2. 传递冻结的 base/head SHA、该专审的完整 assigned frontend diff、适用项目规则和必要上下文。
3. 要求它检查全部 assigned 改动，只加载相关 rule files，并返回问题、head commit GitHub 链接、逐字核心代码、修复建议和命中的 rule。
4. 对无适用 React/Next.js 改动、无问题和未完成三种状态分别明确返回。
5. 由专审 owner 复核、去重，分类为 `代码质量问题` 或 `性能问题` 后写入专审风险项；未经 owner 复核的结果不得进入输出。

该任务不受下方“可选取证 subagent”的启用条件限制。

## 可选取证 Subagent 的启用条件

仅在以下条件同时成立时启用：

1. PR 已冻结 base/head commit SHA，并完成一次统一解析。
2. 主 review owner 已明确审查目标、核心执行链和行为或工程不变量。
3. 至少存在两个互不依赖的只读取证任务。
4. 并行收益明显高于上下文传递和结果复核成本。

小型、强耦合或必须连续追踪同一状态链的 PR 不启用 subagent。

## Owner 边界

主 review owner 必须：

- 阅读完整前端 diff 和核心调用链；
- 连续完成根因/目标、实现效果和最终风险判断；
- 读取适用项目规则和专审 `risk-rubric.md`；
- 复核每条 candidate evidence；
- 独立生成最终 `output-template.md`。

不得把以下任务交给 subagent：

- 决定根因、功能目标或行为不变量；
- 判断“是/否”、风险类型或最终 verdict；
- 生成最终模板；
- 发布评论、修改文件或改变 PR 状态。

Vercel subagent 可以判断某段 changed code 是否命中该 skill 的具体 rule，但不得决定专审的根因、目标完整性、行为等价性、风险类型或 verdict。

## 冻结 Review Packet

所有 subagent 使用同一份最小 packet，不重新获取或刷新 PR：

```yaml
pr:
  identifier: <url-or-number>
  title: <title>
  intent: <issue-or-pr-declared-intent>
snapshot:
  base_sha: <base>
  head_sha: <head>
scope:
  changed_frontend_files: [<path>]
  assigned_question: <single-independent-question>
context:
  applicable_rules: [<path-and-scope>]
  relevant_contracts: [<path>]
  tests: [<path>]
constraints:
  read_only: true
  do_not_refetch_pr: true
  do_not_render_final_template: true
required_prompt: |
  Use `$vercel-react-best-practices`.
  Resolve it from the active Codex global skill catalog and read its `SKILL.md`
  completely before reviewing.
```

传递原始代码和约束，不传递主 owner 的疑似 finding 或预期答案。

## 可并行任务

| Review | Owner 保留 | 可交给 subagent |
|---|---|---|
| Bug | 触发路径、根因、修复是否命中根因 | 同根因调用方搜索；相邻回归与回归测试检查 |
| Feature | 用户路径、验收条件、功能完整性 | 兼容路径与调用方覆盖；边界状态与功能测试检查 |
| Refactor | 旧新结构、行为不变量、等价性判断 | 旧 API/迁移残留搜索；公共契约与等价性测试检查 |
| Chore | source of truth、工程链路、最终影响 | manifest/lockfile/codegen 一致性；CI/环境与消费者检查 |

每个 subagent 只接收一个边界明确的问题。不要按文件数量平均拆分。

## Candidate Evidence 契约

subagent 只返回：

```yaml
question: <assigned-question>
checked: [<paths-or-commands>]
candidates:
  - changed_location: <path:lines>
    trigger_or_path: <reachable-condition>
    observed_impact: <specific-result>
    evidence: <code-test-contract>
    suggested_direction: <actionable-direction>
not_found: <what was searched with no candidate>
not_verified: <remaining-gap>
```

允许返回零 candidates。不要为了证明 subagent 有用而制造问题。

Vercel subagent 使用以下附加契约：

```yaml
status: completed | not-applicable | incomplete
checked: [<assigned paths and relevant rules>]
issues:
  - problem: <命中的 rule 和具体影响>
    suggested_risk_type: <代码质量问题 | 性能问题>
    github_url: <head commit GitHub blob URL with exact lines>
    code: <verbatim changed code>
    fix_suggestion: <actionable direction>
    rule: <vercel-react-best-practices rule id>
reason: <仅 not-applicable 或 incomplete 时填写>
```

## 收口门槛

主 review owner 对每条 candidate 重新确认：

1. 位于或直接归因于本次 changed frontend code/config；
2. 存在真实可达路径；
3. 影响具体且不是明确的有意变化；
4. 满足对应 `risk-rubric.md` 的全部条件；
5. 与其他 candidate 不重复。

未经 owner 复核的 candidate 不得进入风险项。最终风险类型由 owner 决定，subagent 的 `suggested_risk_type` 只作为候选。

## 并发约束

- 单类型 review：一个 owner、一个强制 Vercel subagent；可用槽位允许时再加一至两个可选取证 subagent。
- fallback 多类型 review：可并行专审，但每个专审都必须获得一次 Vercel subagent 执行机会；槽位不足时串行专审。
- 作为 subagent 运行的专审只允许继续启动其强制 Vercel subagent，不得递归启动可选取证 agent。
- 始终为 owner 保留一个执行槽，并优先保证强制 Vercel subagent。
