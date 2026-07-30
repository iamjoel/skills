# Frontend Chore Review Output Template

## 目录

- 使用规则
- Template

## 使用规则

- 最终输出不要包裹在代码块中。
- 保持下列 H1/H2 顺序；按实际数量重复 `Chore Review` 和 `Finding Detail` 块。
- 替换所有占位符并删除 HTML 注释。无 P0/P1 时使用指定 Blockers 空状态；无 finding 时使用指定 Findings 空状态。
- Code/config 使用可点击的本地绝对路径或规范 GitHub URL，并包含准确行号。

## Template

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
- Review confidence: <0.0-1.0>

结论仅覆盖该 PR 的前端 Chore 切片。

## Blockers

<!-- 重复 P0/P1；没有时只写 No frontend blocking findings. -->
- `<finding-id>` `[P0|P1]` <一句话摘要>

## Frontend Chore Map

| id | 工程单元 | 类型 | 规模 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `c1` | <依赖/构建/工具职责> | <Dependency/Build/Test tooling/Codegen/CI/Config/Docs> | <Small/Medium/Large> | <Low/Medium/High> | <Pass/Issues/Not fully verified> | <P0-P3/—> | <number> |

## Chore Reviews

<!-- 每个 cN/xN 重复以下完整块 -->
### `<chore-id>` — <Chore 单元>

- Type: <Dependency | Build | Test tooling | Codegen | CI | Config | Docs>
- Verdict: <Pass | Issues | Not fully verified>
- Correctness: <correct | incorrect>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

#### Engineering Contract

- Goal: <维护目标>
- Source of truth: <配置/生成源>
- Allowed changes: <允许变化>
- Invariants: <产品、构建、测试和发布不变量>
- Environments: <local/CI/SSR/production>
- Consumers: <脚本、包、产物或运行时消费方>

#### Frontend Config/Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<chore-id>.c1` | <Source/Config/Command/Tool/Consumer/Artifact/CI/Verification> | <clickable file:line> | <职责> |

#### Review Focus

- Chore core check: <检查结果>
- Risk overlay 1: <检查结果或 N/A>
- Risk overlay 2: <检查结果或 N/A>

#### Findings

| id | Priority | Confidence | 问题 | Frontend code/config |
|---|---|---:|---|---|
| `<chore-id>.i1` | <P0-P3> | <0.0-1.0> | <摘要> | <clickable file:line> |

<!-- 当前单元无 finding 时，用 No actionable frontend findings for this chore unit. 代替表格 -->

#### Validation

- Paths/config reviewed: <范围>
- Commands reviewed: <命令>
- Commands executed: <实际运行和结果>
- Environments checked: <环境>
- Not verified: <未验证或 None>
- Residual risks: <残余风险或 None>

## Finding Details

<!-- 每个 finding 重复；全局无 finding 时只写 No actionable frontend findings. -->
### `<finding-id>` — [P1] <问题标题>

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
- Repository rule: <最小引用或 N/A>
- Confidence: <0.0-1.0> (<high | medium | low>)

## Review Validation

- Frontend paths/config reviewed: <去重后的范围>
- Commands/tests reviewed: <命令与测试>
- Commands executed: <命令与结果>
- Not verified: <未验证或 None>
- Residual frontend risks: <残余风险或 None>
```
