# Frontend Review Output Protocol

## 目录

- 首次输出
- 前端功能下钻
- Finding 下钻
- 跨功能下钻
- ID 与导航规则

## 首次输出

首次回复只输出 Overview、Blockers 和 Frontend Feature Map。不要提前展开 Code Map、完整检查表或所有 findings。

```markdown
# Frontend PR Code Review

## Overview

- Frontend verdict: <Approve | Comment | Request changes>
- Frontend change type: <primary type>
- Frontend size: <small | medium | large>
- Frontend risk: <low | medium | high>
- Frontend files reviewed: <number>
- Features reviewed: <number>
- Blocking findings: <number>

结论仅覆盖该 PR 的前端改动。

## Blockers

- `<finding-id>` `[P0|P1]` <一句话摘要>

没有阻塞问题时写：

No frontend blocking findings.

## Frontend Feature Map

| id | 功能 | 类型 | 规模 | 风险 | 结论 | Findings |
|---|---|---|---|---|---|---:|
| `f1` | <用户可感知的功能名称> | feature-add | Medium | Medium | Pass | 0 |
| `f2` | <用户可感知的功能名称> | bug-fix | Medium | High | Issues | 2 |
| `x1` | <跨功能前端关注点> | cross-cutting | Large | Medium | Review | 1 |

回复一个 `id` 查看完整前端 review，例如：`f2`。

其他命令：`f1 f2`、`f2.i1`、`blockers`、`map`、`all`。
```

功能名使用用户语言描述 UI 或客户端行为，不要使用文件名、组件名或内部类名充当功能名。

## 前端功能下钻

Medium 或 Large 功能使用：

```markdown
# <feature-id> — <功能名称>

- Change type: <type>
- Verdict: <Pass | Issues | Not fully verified>
- Size: <small | medium | large>
- Risk: <low | medium | high>
- Findings: <number>

## Frontend Behavior

- Purpose: <目标>
- Before: <改动前行为；新增功能可写 Not available>
- After: <改动后行为>
- Invariants: <必须保持的 UI、状态或交互>
- Edge cases: <关键边界>

## Frontend Code Map

| id | Role | Code | 说明 |
|---|---|---|---|
| `<feature-id>.c1` | Entry/UI | <clickable frontend file:line> | <用户入口> |
| `<feature-id>.c2` | State | <clickable frontend file:line> | <状态变化> |
| `<feature-id>.c3` | Async data | <clickable frontend file:line> | <请求与缓存> |
| `<feature-id>.c4` | Rendering | <clickable frontend file:line> | <输出和交互> |
| `<feature-id>.c5` | Tests | <clickable frontend file:line> | <验证> |

只列当前功能需要的角色。使用本地绝对路径或规范 GitHub URL，并包含准确行号。
后端位置不能作为 Code Map 主项；必要时只在说明中作为契约背景引用。

## Review Focus

<只输出当前类型对应的前端检查结果和最多两个风险叠加项。>

## Findings

| id | Priority | 问题 | Frontend code |
|---|---|---|---|
| `<feature-id>.i1` | P1 | <摘要> | <clickable frontend file:line> |

没有问题时写：

No actionable frontend findings for this feature.

## Validation

- Frontend paths reviewed: <路径>
- Frontend tests reviewed: <测试>
- Frontend tests executed: <实际运行的命令和结果>
- Contract context checked: <只列为理解前端而读取的契约>
- Not verified: <未验证内容>
- Residual frontend risks: <残余风险>

回复 finding `id` 查看证据，例如：`<feature-id>.i1`。回复 `map` 返回 Frontend Feature Map。
```

Small 功能使用 `review-focus.md` 中的小改动固定卡片，不输出空章节。

## Finding 下钻

```markdown
# <finding-id> — [P1] <问题标题>

- Feature: `<feature-id>` — <功能名称>
- Frontend location: <clickable frontend file:line>
- Trigger: <真实可达的用户、浏览器或渲染触发条件>
- Problem: <前端代码为什么不正确>
- User impact: <用户可见或客户端影响>
- Evidence: <前端调用链、状态、契约或测试证据>
- Suggested direction: <前端修复方向，不要求完整重写>
- Verification: <修复后的前端验证方式>
- Confidence: <high | medium | low>

回复 `<feature-id>` 返回功能详情，回复 `map` 返回 Frontend Feature Map。
```

如果用户要求 GitHub inline comment，可把 finding 转换成紧凑评论；保持标题、前端位置、触发条件和用户影响，不复制整段审查报告。

## 跨功能下钻

使用 `xN` 表示共享前端风险：

```markdown
# <cross-id> — <前端关注点>

- Scope: <受影响功能 ID>
- Frontend invariant: <共享状态、组件、缓存或契约>
- Risk: <风险>

## Frontend Code Map

<共享组件、状态、查询、路由、权限展示或前端契约位置>

## Findings

<使用 x1.i1 等 ID>
```

不要用 `xN` 承载纯后端问题。

## ID 与导航规则

- 首次按用户流程分配 `f1..fN`；跨功能前端项分配 `x1..xN`。
- 保持 ID 与功能的映射直到本次 PR 前端审查结束。
- 过滤、排序、展开或上下文压缩后不得重新编号。
- 新发现的前端功能追加下一个未使用 ID。
- 用户回复多个 ID 时，按回复顺序输出。
- `next` 和 `prev` 在当前 Frontend Feature Map 顺序中移动。
- `back` 从 finding 返回功能，从功能返回 map。
- 未知 ID 只返回合法 ID 的精简表，不重新执行审查。
- `all` 对大型前端审查可能产生长输出；先给一句提示，再继续展开。

