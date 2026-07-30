---
name: frontend-pr-feature-review
description: Review only frontend feature additions and intentional behavior changes in a pull request by validating user journeys, acceptance criteria, UI state matrices, integration completeness, compatibility, and tests. Use when the user asks to review a new or changed frontend, web, UI, React, Next.js, browser, or client-side feature.
---

# 前端 PR Feature Review

只对 PR 中新增或有意改变的前端能力形成结论和 findings。按用户可感知功能组织审查，验证需求是否完整落到入口、状态、请求、渲染、异常与测试，而不是按文件列表复述实现。

## 范围与路由

包含：

- 新增或有意改变用户行为的组件、hooks、状态、样式、i18n、浏览器逻辑和测试；
- 被功能直接消费的共享类型、生成契约和 UI 包；
- 为理解新旧行为、兼容性和用户流程所必需的未修改调用方与上下文。

后端 endpoint、schema、错误码、权限和事件格式只作为前端契约背景读取。finding 的问题位置和修复方向必须落在本次 PR 的前端改动上。

独立调用时，如果 PR 没有前端功能新增或行为变更，输出 `No frontend feature changes to review.` 并停止；混合 PR 只审查 Feature 切片，把独立 Bug、Refactor 或 Chore 列为未覆盖范围。由 `$frontend-pr-code-review` 根据 `feat:` 标题分发时，接受路由包中的全部前端 scope 和 declared intent；若 diff 与功能意图冲突，把它作为 intent mismatch 返回编排层，不要静默改派或直接停止。

## 工作流

1. 解析 PR。
   - 从用户提供的 URL、编号或当前分支定位 PR；无法唯一定位时请求 PR。
   - 读取 PR 描述、关联 issue、changed files、完整 patch、评论和检查状态。
   - 读取适用的根级与目录级项目指令、前端包配置和测试约定。按用户要求、作用域更具体的 `AGENTS.override.md`、`AGENTS.md` 和仓库 fallback 指令解析；更具体的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、发布评论或改变 PR 状态。
2. 识别 Feature 范围。
   - 独立调用时比较 PR 描述、issue、测试和实现，区分 Feature Add 与 Feature Change；由编排层按 `feat:` 标题分发时，使用路由包给出的 scope，不重新分类。
   - 根据仓库结构、manifest、构建配置和 import graph 判断前端文件，不要只依赖目录名。
   - 按前端 feature 切片单独计算规模和风险。
3. 建立功能契约。
   - 从 issue、PR 和现有产品行为提炼目标用户、入口、前置条件、成功结果和明确非目标。
   - 对 Feature Change 写明 Before、After、必须保持的不变量和迁移/降级要求。
   - 区分已声明需求、从代码可证明的不变量和仍需确认的产品问题。
4. 建立 Feature Map。
   - 按用户行为或 UI 流程分配 `f1..fN`；共享组件、缓存、契约、可访问性等跨功能问题使用 `x1..xN`。
   - 把入口、权限/开关、状态、异步数据、浏览器副作用、渲染、错误处理和测试映射到对应 ID。
   - 不要为每个文件或组件创建一个功能。
5. 确定审查深度。
   - 综合前端有效改动行数、文件数、调用链跨度和影响范围判断 `small | medium | large`。
   - 认证、敏感数据、公共契约、异步竞态、缓存、SSR/水合、持久化、文件处理和生产依赖提升审查等级。
   - 读取 [references/review-focus.md](references/review-focus.md)，选择 Feature Add 或 Feature Change 检查，并执行最多两个风险叠加项。
6. 验证实现。
   - 阅读 changed frontend code 及必要的 unchanged context、调用方、契约和测试。
   - 沿真实用户操作验证入口、权限、loading、empty、success、error、disabled、取消、重复和恢复状态。
   - 对 Feature Change 搜索旧调用方、旧 URL、旧缓存、旧持久化数据、feature flag 和降级路径。
   - 验证测试覆盖用户可见结果和关键边界，而不是只验证 mock 或内部实现。
   - 运行与风险相称的测试、类型检查或静态检查；不要安装依赖。区分“已运行”“仅阅读”和“未验证”。
7. 形成 findings。
   - 先收集所有 candidate findings，再完成 coverage pass。
   - 读取 [references/finding-rubric.md](references/finding-rubric.md)，执行准入、归因、去重和完整性检查。
   - 证据不足时归入 `Not verified` 或提出明确问题，不要伪装成确定缺陷。
   - 对合格问题分配稳定 finding ID、priority 和 confidence，并挂到 `fN` 或 `xN`。
8. 模板化输出。
   - 输出前完整读取 [references/output-protocol.md](references/output-protocol.md) 和 [references/output-template.md](references/output-template.md)。
   - 默认一次性输出所有适用功能、状态矩阵、findings 和 validation，严格遵循 template 的标题顺序、字段和空状态；不要自创另一套格式。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审 payload，不加外围说明，供入口 skill 原样嵌入。
   - 独立调用时也使用同一 template；用户后续可用稳定 ID 下钻。
   - 同一次审查中保持 ID 稳定；新增功能只追加 ID。

## Feature Review 判定

- `Frontend correctness: patch is correct`：声明的功能在可证明范围内完整接入，关键状态和兼容路径正确，且没有真实前端 bug。
- `Frontend correctness: patch is incorrect`：存在缺失或错误的可达状态、调用方遗漏、契约不匹配、兼容性回归或其他真实前端 bug。
- 未声明的产品偏好不构成 finding；无法从 issue、PR、现有行为或代码契约证明时，放入问题或 `Not verified`。

`Frontend correctness` 描述补丁是否正确，`Frontend verdict` 描述是否阻塞合并；两者不要混为一谈。结论只覆盖前端 feature 切片。

## 优先级

- `P0`：安全边界失守、敏感数据暴露、不可恢复的数据操作或大范围不可用。
- `P1`：主要用户流程不可用、破坏性兼容问题或明确的高影响回归。
- `P2`：特定条件下的功能错误、重要状态缺失、可访问性阻断、可靠性问题或重要测试缺口。
- `P3`：低影响但具体可行动的维护问题；不要用于纯风格偏好。

## 导航

- `f2`：展开一个功能。
- `f2.i1`：展开一个 finding。
- `x1`：展开跨功能关注点。
- `blockers`、`map`、`all`、`next`、`prev`、`back`：按当前层级导航。

收到未知 ID 时，只返回合法 ID 的精简 Frontend Feature Map，不重新执行审查。
