# Frontend Refactor Review Output Protocol

## Template 契约

默认输出必须完整读取并严格填充 [output-template.md](output-template.md)。一次性输出 Overview、Blockers、Refactor Map、全部 Refactor Reviews、Finding Details 和 Review Validation。不得改变 template 的 H1/H2 顺序；本文件其余章节用于解释字段、下钻、inline comment 和 JSON 变体。若两者冲突，以 template 为准。

## 顶部摘要字段

Template 顶部的 Overview、Blockers 和 Frontend Refactor Map 使用：

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

结论仅覆盖该 PR 的前端 refactor 切片。

## Blockers

- `<finding-id>` `[P0|P1]` <一句话摘要>

没有阻塞问题时写：`No frontend blocking findings.`

## Frontend Refactor Map

| id | 重构单元 | 关键不变量 | 迁移范围 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `r1` | <职责/迁移单元> | <行为不变量> | Medium | Medium | Pass | — | 0 |
| `x1` | <跨单元风险> | <共享不变量> | Large | High | Issues | P1 | 1 |

回复一个 `id` 查看完整重构单元，例如：`r1`。
```

## 重构单元下钻

Medium 或 Large 单元使用：

```markdown
# <refactor-id> — <重构单元>

- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

## Refactor Contract

- Intent: <内部结构目标>
- Allowed changes: <允许变化>
- Invariants: <必须保持的渲染/事件/状态/请求/副作用/契约>
- Old structure: <旧职责与所有权>
- New structure: <新职责与所有权>
- Complexity result: <可证明的减少或未证明>

## Migration Coverage

| Surface | Status | Evidence / Gap |
|---|---|---|
| Production call sites | <complete/incomplete/not verified> | <证据> |
| Dynamic/re-export/registry | <complete/incomplete/n/a> | <证据> |
| Tests/mocks/stories | <complete/incomplete/n/a> | <证据> |
| Compatibility/dead code | <complete/incomplete/n/a> | <证据> |

## Frontend Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<refactor-id>.c1` | Old behavior | <clickable file:line> | <旧路径> |
| `<refactor-id>.c2` | New abstraction | <clickable file:line> | <新结构> |
| `<refactor-id>.c3` | Call-site migration | <clickable file:line> | <迁移> |
| `<refactor-id>.c4` | Equivalence tests | <clickable file:line> | <验证> |

## Review Focus

<只输出等价性、迁移、抽象检查结果和最多两个风险叠加项。>

## Findings

| id | Priority | Confidence | 问题 | Frontend code |
|---|---|---:|---|---|
| `<refactor-id>.i1` | P1 | 0.96 | <摘要> | <clickable file:line> |

## Validation

- Invariants checked: <不变量>
- Call sites searched: <范围>
- Frontend tests reviewed: <测试>
- Frontend tests executed: <命令与结果>
- Not verified: <未验证>
- Residual risks: <残余风险>
```

Small 单元使用 `review-focus.md` 的固定卡片。没有 finding 时写 `No actionable frontend findings for this refactor unit.`

## Finding 下钻

```markdown
# <finding-id> — [P1] <问题标题>

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
- Repository rule: <仅有实质支持时提供最小引用>
- Confidence: <0.0-1.0> (<high | medium | low>)
```

## GitHub inline comment

只有用户明确要求时才转换 finding：

```markdown
[P1] <最多 80 字符的祈使标题>

<一个自然段：触发条件、changed logic、被破坏的不变量、影响和修复方向。>
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

- 首次分配 `r1..rN`；跨单元项分配 `x1..xN`。
- 过滤、排序、展开或上下文压缩后不得重新编号；新单元追加下一个 ID。
- finding 使用 `<scope-id>.iN`，代码位置使用 `<scope-id>.cN`。
- 未知 ID 只返回精简 Frontend Refactor Map，不重做审查。
