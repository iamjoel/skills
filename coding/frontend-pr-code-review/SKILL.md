---
name: frontend-pr-code-review
description: Review only the frontend portion of a pull request by decomposing frontend changes into user-visible features, applying change-type and frontend-risk-specific review focus, mapping each feature to frontend code and tests, and using stable IDs for progressive drill-down. Use when the user asks to review the frontend, web, UI, React, Next.js, browser, or client-side changes in a GitHub pull request.
---

# 前端 PR Code Review

只对 PR 中的前端改动形成结论和 findings。按用户可感知功能组织审查，不按文件列表或严重级别组织一级输出。先建立 Frontend Feature Map；用户回复稳定 ID 后，再展开对应功能、前端代码、测试和 findings。

## 范围边界

包含：

- PR 中修改的前端运行时代码、组件、hooks、状态、样式、i18n、浏览器逻辑和前端测试；
- 被前端直接消费的共享类型、生成契约和 UI 包；
- 为理解前端行为所必需的未修改前端调用方和上下文。

仅作为背景读取：

- 后端 endpoint、schema、错误码、权限和事件格式；
- 数据库迁移、服务实现和后端测试。

不要对后端实现质量、数据库逻辑或服务架构给出 findings。需要引用后端代码时，只把它作为验证前端契约的证据；finding 的问题和修复方向必须落在本次 PR 的前端改动上。

如果 PR 没有前端改动，明确说明 `No frontend changes to review.` 并停止。

## 工作流

1. 解析 PR。
   - 从用户提供的 PR URL/编号或当前分支定位 PR；无法唯一定位时请求 PR。
   - 读取 PR 描述、关联 issue、changed files、完整 patch、评论和检查状态。
   - 读取适用的 `AGENTS.md`、前端包配置、测试约定和目录边界。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、提交评论或改变 PR 状态。
2. 识别前端范围。
   - 根据仓库结构、package manifest、构建配置和 import graph 判断前端文件，不要只依赖目录名。
   - 把后端和无关基础设施文件排除出审查统计。
   - 按前端 diff 单独计算规模和风险，不使用整个 PR 的总行数代替。
3. 理解意图。
   - 比较 PR 描述、issue、测试和实现，不要仅相信标题中的 `feat`、`fix` 或 `refactor`。
   - 区分新增功能、改动功能、Bug 修复、优化、重构、测试和工程改动。
4. 划分前端功能。
   - 按用户行为、UI 流程或客户端职责分组。
   - 把入口、渲染、状态、异步数据、浏览器副作用、错误处理和测试映射到对应功能。
   - 把共享组件、缓存、前端契约、可访问性等跨功能问题归入 `xN`。
   - 不要为每个文件或组件创建一个功能。
5. 确定审查深度。
   - 综合前端有效改动行数、文件数、调用链跨度和风险决定 `small | medium | large`。
   - 认证展示、敏感数据、公共前端契约、异步竞态、缓存、SSR/水合、文件处理和生产依赖会提升审查等级。
   - 读取 [references/review-focus.md](references/review-focus.md)，选择主要类型检查和最多两个相关前端风险叠加项。
6. 审查实现。
   - 阅读 changed frontend code 及必要的 unchanged context、调用方、类型、契约和测试。
   - 沿真实用户操作和渲染路径验证触发条件、状态变化、请求生命周期、错误恢复和 UI 结果。
   - 运行与风险相称的前端测试、类型检查或静态检查；不要安装依赖。明确区分“已运行”“仅阅读”和“未验证”。
7. 形成 findings。
   - 只报告具体、可触发、可行动且有前端代码证据的问题。
   - 每个 finding 必须说明前端位置、触发条件、错误行为、用户影响、证据和验证方向。
   - 不把个人风格偏好、无证据猜测、纯后端缺陷或与本次前端改动无关的旧问题当作 finding。
8. 渐进输出。
   - 输出前读取 [references/output-protocol.md](references/output-protocol.md)。
   - 首次回复只输出 Overview、Blockers 摘要和 Frontend Feature Map，不展开功能详情。
   - 提示用户回复功能 `id`。收到合法 ID 后直接展开，不重复询问。
   - 在同一次审查中保持所有 ID 稳定；发现新功能时追加 ID，不得重新编号。

## 功能与 ID

- 使用 `f1`、`f2`、`f3` 表示用户可感知的前端功能。
- 使用 `x1`、`x2` 表示跨功能的前端关注点。
- 使用 `f2.c1` 表示功能对应的前端代码位置。
- 使用 `f2.i1` 表示功能下的 finding。
- 按用户流程而非文件顺序分配功能 ID。
- 一个前端文件可以属于多个功能，但每个代码位置要说明它在当前功能中的职责。

## Finding 质量门槛

仅在以下条件全部成立时报告 finding：

1. 能指出本次 PR 修改的前端代码或直接消费的前端契约。
2. 能描述真实可达的用户、浏览器或渲染触发路径。
3. 能解释错误 UI、状态、请求或性能结果及其影响。
4. 问题由本次前端改动引入、暴露或应在本次前端范围内解决。
5. 建议方向不依赖虚构的接口、需求或测试结果。

如果证据不足，把它放入 `Not verified` 或提出明确问题，不要伪装成确定缺陷。

## 优先级

- `P0`：前端导致安全边界失守、敏感数据暴露、不可恢复的数据操作或大范围不可用。
- `P1`：主要用户路径错误、破坏性兼容问题或明确的高影响回归。
- `P2`：特定条件下的功能错误、可访问性阻断、可靠性问题或重要测试缺口。
- `P3`：低影响但可行动的维护问题；不要用于纯风格偏好。

在 Frontend Feature Map 中显示最高优先级和 finding 数量；在功能详情中按优先级排序。

## 审查结论

- `Request changes`：前端改动存在必须修复的正确性、安全、可访问性阻断或兼容性问题。
- `Comment`：存在非阻塞问题、设计疑问或重要的未验证风险。
- `Approve`：前端范围内没有 actionable findings，且验证范围足以支撑结论。

结论只覆盖 PR 的前端部分，不要暗示整个 PR 已通过审查。

## 导航行为

支持以下用户回复：

- `f2`：展开一个前端功能。
- `f1 f3`：按给定顺序展开多个功能。
- `f2.i1`：展开一个 finding。
- `blockers`：只显示前端 `P0/P1`。
- `map`：返回当前 Frontend Feature Map。
- `all`：展开所有前端功能；大型审查先提醒输出会较长。
- `next`、`prev`、`back`：在当前层级导航。

收到未知 ID 时，列出合法 ID 的精简 Frontend Feature Map；不要重做整个审查。

