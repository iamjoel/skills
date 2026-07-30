# Frontend Feature Review Output Protocol

## Template 契约

默认输出必须完整读取并严格填充 [output-template.md](output-template.md)。一次性输出 Overview、Blockers、Feature Map、全部 Feature Reviews、Finding Details 和 Review Validation。不得改变 template 的 H1/H2 顺序；本文件其余章节用于解释字段、下钻、inline comment 和 JSON 变体。若两者冲突，以 template 为准。

## 顶部摘要字段

Template 顶部的 Overview、Blockers 和 Frontend Feature Map 使用：

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

结论仅覆盖该 PR 的前端 feature 切片。

## Blockers

- `<finding-id>` `[P0|P1]` <一句话摘要>

没有阻塞问题时写：`No frontend blocking findings.`

## Frontend Feature Map

| id | 功能 | 类型 | 规模 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `f1` | <用户可感知功能> | Feature Add | Medium | Medium | Pass | — | 0 |
| `x1` | <跨功能风险> | Cross-cutting | Large | High | Issues | P1 | 1 |

回复一个 `id` 查看完整功能，例如：`f1`。
```

## 功能下钻

Medium 或 Large 功能使用：

```markdown
# <feature-id> — <功能名称>

- Type: <Feature Add | Feature Change>
- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

## Feature Contract

- Target user: <目标用户>
- Purpose: <目标>
- Entry: <入口与前置条件>
- Before: <旧行为；新增功能写 Not available>
- After: <新行为>
- Success result: <用户可见结果>
- Invariants: <必须保持的行为>
- Non-goals / Questions: <明确非目标或待确认项>

## State Matrix

| Dimension | Covered | Evidence / Gap |
|---|---|---|
| Loading / empty / success / error | <yes/no/n/a> | <证据> |
| Permission / flag / unavailable | <yes/no/n/a> | <证据> |
| Repeat / cancel / switch / recover | <yes/no/n/a> | <证据> |
| Old data / URL / cache / response | <yes/no/n/a> | <证据> |

## Frontend Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<feature-id>.c1` | Entry/UI | <clickable file:line> | <入口> |
| `<feature-id>.c2` | State/Async | <clickable file:line> | <状态与请求> |
| `<feature-id>.c3` | Rendering | <clickable file:line> | <结果> |
| `<feature-id>.c4` | Tests | <clickable file:line> | <验证> |

## Review Focus

<只输出 Feature Add 或 Feature Change 检查结果和最多两个风险叠加项。>

## Findings

| id | Priority | Confidence | 问题 | Frontend code |
|---|---|---:|---|---|
| `<feature-id>.i1` | P1 | 0.96 | <摘要> | <clickable file:line> |

## Validation

- User paths reviewed: <路径>
- Frontend tests reviewed: <测试>
- Frontend tests executed: <命令与结果>
- Contract context checked: <契约背景>
- Not verified: <未验证>
- Residual risks: <残余风险>
```

Small 功能使用 `review-focus.md` 的固定卡片。没有 finding 时写 `No actionable frontend findings for this feature.`

## Finding 下钻

```markdown
# <finding-id> — [P1] <问题标题>

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
- Repository rule: <仅有实质支持时提供最小引用>
- Confidence: <0.0-1.0> (<high | medium | low>)
```

## GitHub inline comment

只有用户明确要求时才转换 finding：

```markdown
[P1] <最多 80 字符的祈使标题>

<一个自然段：触发条件、changed logic、错误结果、用户影响和修复方向。>
```

## 机器可读输出

只有用户明确要求 Codex JSON 时，严格输出以下结构且不加 Markdown fence：

```json
{
  "findings": [
    {
      "title": "<[P0]-[P3] 标题>",
      "body": "<单段 Markdown finding>",
      "confidence_score": 0.0,
      "priority": 0,
      "code_location": {
        "absolute_file_path": "<绝对路径>",
        "line_range": {"start": 1, "end": 1}
      }
    }
  ],
  "overall_correctness": "patch is correct",
  "overall_explanation": "<1-3 句说明>",
  "overall_confidence_score": 0.0
}
```

`overall_correctness` 只能是 `patch is correct` 或 `patch is incorrect`。`code_location` 必须与 diff 重叠且尽可能短。远程-only review 无法提供绝对路径时，说明限制并继续使用规范 GitHub URL，除非用户接受非严格 schema。

## ID 与导航

- 首次分配 `f1..fN`；跨功能项分配 `x1..xN`。
- 过滤、排序、展开或上下文压缩后不得重新编号；新功能追加下一个 ID。
- finding 使用 `<scope-id>.iN`，代码位置使用 `<scope-id>.cN`。
- 未知 ID 只返回精简 Frontend Feature Map，不重做审查。
