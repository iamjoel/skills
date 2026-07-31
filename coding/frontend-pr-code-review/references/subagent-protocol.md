# Frontend Review Subagent Protocol

使用 subagent 加速独立取证，不拆分核心审查推理。

## 启用条件

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

## 收口门槛

主 review owner 对每条 candidate 重新确认：

1. 位于或直接归因于本次 changed frontend code/config；
2. 存在真实可达路径；
3. 影响具体且不是明确的有意变化；
4. 满足对应 `risk-rubric.md` 的全部条件；
5. 与其他 candidate 不重复。

未经 owner 复核的 candidate 不得进入风险项。

## 并发约束

- 单类型 review：一个 owner，加一至三个证据 subagent。
- fallback 多类型 review：可以并行专审，但只并行这一层；专审不得继续递归分发。
- 始终为 owner 保留一个执行槽，并根据可用并发数减少任务。
