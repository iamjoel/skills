---
name: frontend-pr-refactor-review
description: Review only behavior-preserving frontend refactors in a pull request by validating explicit UI and client invariants, call-site migration completeness, dependency boundaries, state and effect equivalence, dead-code removal, and concrete complexity reduction. Use when the user asks to review a frontend, web, UI, React, Next.js, browser, or client-side refactor, cleanup, extraction, migration, or internal rewrite that should not change user behavior.
---

# 前端 PR Refactor Review

只对 PR 中声称保持行为不变的前端重构形成结论和 findings。先建立可验证的不变量，再比较新旧结构是否等价、迁移是否完整、复杂度是否真实下降，而不是把“代码能编译”当作重构正确。

## 范围与路由

包含：

- 重组、抽取、迁移或清理前端组件、hooks、状态、样式、i18n、浏览器逻辑和测试；
- 被重构直接消费的共享类型、生成契约和 UI 包；
- 为比较行为、调用方、依赖方向和迁移完整性所必需的未修改上下文。

后端 endpoint、schema、错误码和服务实现只作为前端契约背景读取。finding 的问题位置和修复方向必须落在本次 PR 的前端改动上。

独立调用时，如果 PR 没有行为保持型前端重构，输出 `No frontend refactor changes to review.` 并停止；混合 PR 只审查 Refactor 切片，把独立 Bug、Feature 或 Chore 列为未覆盖范围。由 `$frontend-pr-code-review` 根据 `refactor:` 标题分发时，接受路由包中的全部前端 scope 和 declared intent；若 diff 与行为保持意图冲突，把它作为 intent mismatch 返回编排层，不要静默改派或直接停止。

独立调用时，如果“重构”包含有意的用户可见行为变化，不要把变化本身误报为等价性缺陷；把对应切片重新归类为 Feature Change 并排除出本 skill 的结论。标题路由模式下只返回 intent mismatch，由编排层收口。

## 工作流

1. 解析 PR。
   - 从用户提供的 URL、编号或当前分支定位 PR；无法唯一定位时请求 PR。
   - 读取 PR 描述、关联 issue、changed files、完整 patch、评论和检查状态。
   - 读取适用的根级与目录级项目指令、前端包配置和测试约定。按用户要求、作用域更具体的 `AGENTS.override.md`、`AGENTS.md` 和仓库 fallback 指令解析；更具体的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、发布评论或改变 PR 状态。
2. 识别 Refactor 范围。
   - 独立调用时比较 PR 描述、测试和实现，判断哪些切片声明行为保持；由编排层按 `refactor:` 标题分发时，使用路由包给出的 scope，不重新分类。
   - 根据仓库结构、manifest、构建配置和 import graph 判断前端文件，不要只依赖目录名。
   - 按前端 refactor 切片单独计算规模和风险。
3. 建立不变量。
   - 从旧实现、调用方、测试和契约提炼渲染、事件、状态、请求、副作用、错误、可访问性和性能不变量。
   - 明确允许变化的内部结构和不允许变化的用户/客户端行为。
   - 对无法从证据确定的不变量标记 `Not verified`，不要凭个人偏好补需求。
4. 建立 Refactor Map。
   - 按重构职责或迁移单元分配 `r1..rN`；共享依赖、契约、状态或迁移风险使用 `x1..xN`。
   - 把旧实现、新实现、调用方迁移、兼容层、删除项和测试映射到对应 ID。
   - 不要为每个文件创建一个 ID。
5. 确定审查深度。
   - 综合前端有效改动行数、文件数、调用链跨度、调用方数量和架构边界判断 `small | medium | large`。
   - 公共组件/hook、路由、状态、缓存、SSR/水合、持久化、生产依赖和跨包迁移提升审查等级。
   - 读取 [references/review-focus.md](references/review-focus.md)，执行等价性与迁移检查，并选择最多两个风险叠加项。
6. 验证重构。
   - 阅读 changed frontend code 及必要的旧/新实现、unchanged 调用方、契约和测试。
   - 沿真实用户路径比较渲染、事件顺序、状态生命周期、请求、错误恢复、焦点和副作用。
   - 搜索所有导入、调用、注册、动态引用、测试夹具和生成入口，确认迁移完整。
   - 检查兼容层、重复实现和死代码；验证依赖方向与模块所有权是否更清晰。
   - 对抽象收益给出具体证据，例如减少重复状态机、统一不变量或收窄 API；不要只按文件变少判断。
   - 运行与风险相称的测试、类型检查、静态检查或构建；不要安装依赖。区分“已运行”“仅阅读”和“未验证”。
7. 形成 findings。
   - 先收集所有 candidate findings，再完成 coverage pass。
   - 读取 [references/finding-rubric.md](references/finding-rubric.md)，执行准入、归因、去重和完整性检查。
   - 证据不足时归入 `Not verified` 或提出明确问题，不要伪装成确定缺陷。
   - 对合格问题分配稳定 finding ID、priority 和 confidence，并挂到 `rN` 或 `xN`。
8. 模板化输出。
   - 输出前完整读取 [references/output-protocol.md](references/output-protocol.md) 和 [references/output-template.md](references/output-template.md)。
   - 默认一次性输出所有适用重构单元、不变量、迁移覆盖、findings 和 validation，严格遵循 template 的标题顺序、字段和空状态；不要自创另一套格式。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审 payload，不加外围说明，供入口 skill 原样嵌入。
   - 独立调用时也使用同一 template；用户后续可用稳定 ID 下钻。
   - 同一次审查中保持 ID 稳定；新增单元只追加 ID。

## Refactor Review 判定

- `Frontend correctness: patch is correct`：所有可证明的不变量保持，调用方迁移完整，且没有真实前端 bug。
- `Frontend correctness: patch is incorrect`：存在行为漂移、调用方遗漏、状态/副作用生命周期改变、契约破坏或其他真实前端 bug。
- “抽象收益不明显”本身不自动意味着 patch incorrect；只有形成具体维护风险、重复来源或错误所有权且作者会明确修复时，才作为 finding。

`Frontend correctness` 描述补丁是否正确，`Frontend verdict` 描述是否阻塞合并；两者不要混为一谈。结论只覆盖前端 refactor 切片。

## 优先级

- `P0`：安全边界失守、敏感数据暴露、不可恢复的数据操作或大范围不可用。
- `P1`：主要用户路径行为漂移、公共契约破坏、关键调用方遗漏或高影响回归。
- `P2`：特定条件下的不等价、状态/副作用错误、迁移遗漏、可访问性阻断或重要测试缺口。
- `P3`：低影响但具体可行动的维护问题；不要用于主观抽象偏好或纯风格意见。

## 导航

- `r2`：展开一个重构单元。
- `r2.i1`：展开一个 finding。
- `x1`：展开跨单元关注点。
- `blockers`、`map`、`all`、`next`、`prev`、`back`：按当前层级导航。

收到未知 ID 时，只返回合法 ID 的精简 Frontend Refactor Map，不重新执行审查。
