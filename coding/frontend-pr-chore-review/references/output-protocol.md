# Frontend Chore Review Output Protocol

## Template 契约

默认输出必须完整读取并严格填充 [output-template.md](output-template.md)。一次性输出 Overview、Blockers、Chore Map、全部 Chore Reviews、Finding Details 和 Review Validation。不得改变 template 的 H1/H2 顺序；本文件其余章节用于解释字段、下钻、inline comment 和 JSON 变体。若两者冲突，以 template 为准。

## 目录

- 顶部摘要字段
- Chore 单元下钻
- Finding 下钻
- GitHub inline comment
- 机器可读输出
- ID 与导航

## 顶部摘要字段

Template 顶部的 Overview、Blockers 和 Frontend Chore Map 使用：

```markdown
# Frontend PR Chore Review

## Overview

- Frontend verdict: <Approve | Comment | Request changes>
- Frontend correctness: <patch is correct | patch is incorrect>
- Chore type: <Dependency | Build | Test tooling | Codegen | CI | Config | Docs | Mixed>
- Frontend size: <small | medium | large>
- Frontend risk: <low | medium | high>
- Chore units reviewed: <number>
- Frontend files reviewed: <number>
- Blocking findings: <number>

结论仅覆盖该 PR 的前端 Chore 切片。

## Blockers

- `<finding-id>` `[P0|P1]` <一句话摘要>

没有阻塞问题时写：`No frontend blocking findings.`

## Frontend Chore Map

| id | 工程单元 | 类型 | 规模 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `c1` | <依赖/构建/工具职责> | Build | Medium | High | Issues | P1 | 1 |
| `x1` | <跨单元工具链风险> | Cross-cutting | Large | Medium | Review | P2 | 1 |

回复一个 `id` 查看完整 Chore 单元，例如：`c1`。
```

## Chore 单元下钻

Medium 或 Large 单元使用：

```markdown
# <chore-id> — <Chore 单元>

- Type: <Dependency | Build | Test tooling | Codegen | CI | Config | Docs>
- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

## Engineering Contract

- Goal: <维护目标>
- Source of truth: <配置/生成源>
- Allowed changes: <允许变化>
- Invariants: <产品、构建、测试和发布不变量>
- Environments: <local/CI/SSR/production>
- Consumers: <脚本、包、产物或运行时消费方>

## Frontend Config/Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<chore-id>.c1` | Source/config | <clickable file:line> | <入口> |
| `<chore-id>.c2` | Command/tool | <clickable file:line> | <执行> |
| `<chore-id>.c3` | Consumer/artifact | <clickable file:line> | <消费或产物> |
| `<chore-id>.c4` | CI/verification | <clickable file:line> | <验证> |

## Review Focus

<只输出对应 Chore 类型检查结果和最多两个风险叠加项。>

## Findings

| id | Priority | Confidence | 问题 | Frontend code/config |
|---|---|---:|---|---|
| `<chore-id>.i1` | P1 | 0.96 | <摘要> | <clickable file:line> |

## Validation

- Paths/config reviewed: <范围>
- Commands reviewed: <命令>
- Commands executed: <实际运行和结果>
- Environments checked: <环境>
- Not verified: <未验证>
- Residual risks: <残余风险>
```

Small 单元使用 `review-focus.md` 的固定卡片。没有 finding 时写 `No actionable frontend findings for this chore unit.`

## Finding 下钻

```markdown
# <finding-id> — [P1] <问题标题>

- Chore unit: `<chore-id>` — <名称>
- Frontend location: <clickable file:line>
- Trigger: <真实命令、环境或构建路径>
- Introduced by diff: <changed config/code 如何引入问题>
- Affected path: <消费方、产物或用户路径>
- Intentional change check: <为什么不是有意行为>
- Problem: <为什么工程改动不正确>
- Impact: <工程或用户影响>
- Evidence: <命令、配置、产物、调用链或测试证据>
- Suggested direction: <修复方向>
- Verification: <验证方式>
- Repository rule: <仅有实质支持时提供最小引用>
- Confidence: <0.0-1.0> (<high | medium | low>)
```

## GitHub inline comment

只有用户明确要求时才转换最终 finding：

```markdown
[P1] <最多 80 字符的祈使标题>

<一个自然段：触发命令/环境、changed config、错误结果、影响和修复方向。>
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

- 首次分配 `c1..cN`；跨 Chore 单元项分配 `x1..xN`。
- 过滤、排序、展开或上下文压缩后不得重新编号；新单元追加下一个 ID。
- finding 使用 `<scope-id>.iN`，代码位置使用 `<scope-id>.cN`。
- 未知 ID 只返回精简 Frontend Chore Map，不重做审查。
