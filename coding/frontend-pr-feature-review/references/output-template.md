# Frontend Feature Review Output Template

## 目录

- 使用规则
- Template

## 使用规则

- 最终输出不要包裹在代码块中。
- 保持下列 H1/H2 顺序；按实际数量重复 `Feature Review` 和 `Finding Detail` 块。
- 替换所有占位符并删除 HTML 注释。无 P0/P1 时使用指定 Blockers 空状态；无 finding 时使用指定 Findings 空状态。
- Code 使用可点击的本地绝对路径或规范 GitHub URL，并包含准确行号。

## Template

```markdown
# Frontend PR Feature Review

## Overview

- Frontend verdict: <Approve | Comment | Request changes>
- Frontend correctness: <patch is correct | patch is incorrect>
- Frontend change type: <Feature Add | Feature Change | Mixed Feature>
- Frontend size: <small | medium | large>
- Frontend risk: <low | medium | high>
- Features reviewed: <number>
- Frontend files reviewed: <number>
- Blocking findings: <number>
- Review confidence: <0.0-1.0>

结论仅覆盖该 PR 的前端 Feature 切片。

## Blockers

<!-- 重复 P0/P1；没有时只写 No frontend blocking findings. -->
- `<finding-id>` `[P0|P1]` <一句话摘要>

## Frontend Feature Map

| id | 功能 | 类型 | 规模 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `f1` | <用户可感知功能> | <Feature Add/Feature Change> | <Small/Medium/Large> | <Low/Medium/High> | <Pass/Issues/Not fully verified> | <P0-P3/—> | <number> |

## Feature Reviews

<!-- 每个 fN/xN 重复以下完整块 -->
### `<feature-id>` — <功能名称>

- Type: <Feature Add | Feature Change>
- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

#### Feature Contract

- Target user: <目标用户>
- Purpose: <目标>
- Entry: <入口与前置条件>
- Before: <旧行为或 Not available>
- After: <新行为>
- Success result: <用户可见结果>
- Invariants: <必须保持的行为>
- Non-goals / Questions: <明确非目标、问题或 None>

#### State Matrix

| Dimension | Covered | Evidence / Gap |
|---|---|---|
| Loading / empty / success / error | <yes/no/n/a> | <证据> |
| Permission / flag / unavailable | <yes/no/n/a> | <证据> |
| Repeat / cancel / switch / recover | <yes/no/n/a> | <证据> |
| Old data / URL / cache / response | <yes/no/n/a> | <证据> |

#### Frontend Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<feature-id>.c1` | <Entry/UI/State/Async/Rendering/Tests> | <clickable file:line> | <职责> |

#### Review Focus

- Feature core check: <检查结果>
- Risk overlay 1: <检查结果或 N/A>
- Risk overlay 2: <检查结果或 N/A>

#### Findings

| id | Priority | Confidence | 问题 | Frontend code |
|---|---|---:|---|---|
| `<feature-id>.i1` | <P0-P3> | <0.0-1.0> | <摘要> | <clickable file:line> |

<!-- 当前功能无 finding 时，用 No actionable frontend findings for this feature. 代替表格 -->

#### Validation

- User paths reviewed: <路径>
- Frontend tests reviewed: <测试>
- Frontend tests executed: <命令与结果>
- Contract context checked: <契约背景>
- Not verified: <未验证或 None>
- Residual risks: <残余风险或 None>

## Finding Details

<!-- 每个 finding 重复；全局无 finding 时只写 No actionable frontend findings. -->
### `<finding-id>` — [P1] <问题标题>

- Feature: `<feature-id>` — <名称>
- Frontend location: <clickable file:line>
- Trigger: <真实触发条件>
- Introduced by diff: <changed line 如何引入问题>
- Affected path: <被证明受影响的路径>
- Intentional change check: <为什么不是有意行为>
- Problem: <为什么实现不正确>
- User impact: <影响>
- Evidence: <调用链、状态、契约或测试证据>
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
