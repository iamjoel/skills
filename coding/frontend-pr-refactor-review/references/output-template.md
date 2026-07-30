# Frontend Refactor Review Output Template

## 目录

- 使用规则
- Template

## 使用规则

- 最终输出不要包裹在代码块中。
- 保持下列 H1/H2 顺序；按实际数量重复 `Refactor Review` 和 `Finding Detail` 块。
- 替换所有占位符并删除 HTML 注释。无 P0/P1 时使用指定 Blockers 空状态；无 finding 时使用指定 Findings 空状态。
- Code 使用可点击的本地绝对路径或规范 GitHub URL，并包含准确行号。

## Template

```markdown
# Frontend PR Refactor Review

## Overview

- Frontend verdict: <Approve | Comment | Request changes>
- Frontend correctness: <patch is correct | patch is incorrect>
- Frontend size: <small | medium | large>
- Frontend risk: <low | medium | high>
- Refactor units reviewed: <number>
- Frontend files reviewed: <number>
- Blocking findings: <number>
- Review confidence: <0.0-1.0>

结论仅覆盖该 PR 的前端 Refactor 切片。

## Blockers

<!-- 重复 P0/P1；没有时只写 No frontend blocking findings. -->
- `<finding-id>` `[P0|P1]` <一句话摘要>

## Frontend Refactor Map

| id | 重构单元 | 关键不变量 | 迁移范围 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `r1` | <职责/迁移单元> | <行为不变量> | <Small/Medium/Large> | <Low/Medium/High> | <Pass/Issues/Not fully verified> | <P0-P3/—> | <number> |

## Refactor Reviews

<!-- 每个 rN/xN 重复以下完整块 -->
### `<refactor-id>` — <重构单元>

- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

#### Refactor Contract

- Intent: <内部结构目标>
- Allowed changes: <允许变化>
- Invariants: <必须保持的渲染/事件/状态/请求/副作用/契约>
- Old structure: <旧职责与所有权>
- New structure: <新职责与所有权>
- Complexity result: <可证明的减少或未证明>

#### Migration Coverage

| Surface | Status | Evidence / Gap |
|---|---|---|
| Production call sites | <complete/incomplete/not verified> | <证据> |
| Dynamic/re-export/registry | <complete/incomplete/n/a> | <证据> |
| Tests/mocks/stories | <complete/incomplete/n/a> | <证据> |
| Compatibility/dead code | <complete/incomplete/n/a> | <证据> |

#### Frontend Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<refactor-id>.c1` | <Old behavior/New abstraction/Call-site migration/Equivalence tests> | <clickable file:line> | <职责> |

#### Review Focus

- Equivalence check: <检查结果>
- Migration/abstraction check: <检查结果>
- Risk overlay 1: <检查结果或 N/A>
- Risk overlay 2: <检查结果或 N/A>

#### Findings

| id | Priority | Confidence | 问题 | Frontend code |
|---|---|---:|---|---|
| `<refactor-id>.i1` | <P0-P3> | <0.0-1.0> | <摘要> | <clickable file:line> |

<!-- 当前单元无 finding 时，用 No actionable frontend findings for this refactor unit. 代替表格 -->

#### Validation

- Invariants checked: <不变量>
- Call sites searched: <范围>
- Frontend tests reviewed: <测试>
- Frontend tests executed: <命令与结果>
- Not verified: <未验证或 None>
- Residual risks: <残余风险或 None>

## Finding Details

<!-- 每个 finding 重复；全局无 finding 时只写 No actionable frontend findings. -->
### `<finding-id>` — [P1] <问题标题>

- Refactor unit: `<refactor-id>` — <名称>
- Frontend location: <clickable file:line>
- Trigger: <真实触发条件>
- Broken invariant: <被破坏的不变量>
- Introduced by diff: <changed line 如何引入问题>
- Affected path: <被证明受影响的调用方或用户路径>
- Intentional change check: <为什么不是有意行为>
- Problem: <为什么新旧结构不等价或迁移不完整>
- User impact: <影响>
- Evidence: <旧/新调用链、状态、契约或测试证据>
- Suggested direction: <修复方向>
- Verification: <验证方式>
- Repository rule: <最小引用或 N/A>
- Confidence: <0.0-1.0> (<high | medium | low>)

## Review Validation

- Frontend paths reviewed: <去重后的路径>
- Tests reviewed: <测试>
- Commands executed: <命令与结果>
- Not verified: <未验证或 None>
- Residual frontend risks: <残余风险或 None>
```
