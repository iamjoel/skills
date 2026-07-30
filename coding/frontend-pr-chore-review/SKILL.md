---
name: frontend-pr-chore-review
description: Review only frontend chore and engineering-maintenance changes in a pull request by validating dependency and lockfile integrity, build and test tooling, code generation, CI parity, configuration compatibility, reproducibility, and absence of unintended product behavior changes. Use when the user asks to review a frontend, web, UI, React, Next.js, browser, or client-side chore, dependency update, build/config change, test-tooling change, codegen update, documentation maintenance, or other engineering-only PR.
---

# 前端 PR Chore Review

只对前端工程维护改动形成结论和 findings。验证依赖、构建、测试工具、代码生成、CI、配置与文档是否可复现、兼容且不会意外改变产品行为，不把 Chore 当成无需审查的低风险标签。

## 范围与路由

包含：

- `package.json`、lockfile、Node/包管理器版本和依赖升级；
- bundler、transpiler、lint、format、test、Storybook、codegen 和开发脚本；
- 前端 CI、缓存、环境变量、浏览器目标、发布与构建配置；
- 生成产物、测试夹具、工程文档及其他预期不改变产品行为的维护改动；
- 为验证工程改动影响所必需的前端运行时代码、调用方和构建上下文。

后端工具链只在被前端构建或测试直接消费时作为背景读取。finding 的位置和修复方向必须落在本次 PR 的前端 Chore 改动上。

独立调用时，如果 PR 没有前端 Chore 改动，输出 `No frontend chore changes to review.` 并停止。由 `$frontend-pr-code-review` 根据 `chore:` 标题分发时，接受路由包中的 declared intent；若 diff 实际引入产品行为或不属于工程维护，把它作为 intent mismatch 返回编排层，不要静默改派或直接停止。

## 工作流

1. 解析 PR。
   - 从用户提供的 URL、编号或当前分支定位 PR；无法唯一定位时请求 PR。
   - 读取 PR 标题、描述、关联 issue、changed files、完整 patch、评论和检查状态。
   - 读取适用的根级与目录级项目指令、前端包配置和测试约定。按用户要求、作用域更具体的 `AGENTS.override.md`、`AGENTS.md` 和仓库 fallback 指令解析；更具体的规则优先。
   - 只执行只读检查和验证。除非用户明确要求修复，否则不要修改代码、安装依赖、发布评论或改变 PR 状态。
2. 建立 Chore 契约。
   - 写明维护目标、工程表面、允许变化和必须保持的产品/构建不变量。
   - 判断改动是依赖、构建、测试工具、codegen、CI、配置、文档还是混合 Chore。
   - 区分源文件、生成文件和 source of truth。
3. 建立 Chore Map。
   - 按工程职责或可独立验证的维护单元分配 `c1..cN`；共享工具链、配置或发布风险使用 `x1..xN`。
   - 把配置入口、依赖/脚本、消费方、生成产物、CI 和验证映射到对应 ID。
   - 不要为每个配置文件创建一个 ID。
4. 确定审查深度。
   - 综合文件数、工作区/包跨度、构建阶段、环境差异和生产影响判断 `small | medium | large`。
   - 生产依赖、lockfile 大幅变化、Node/包管理器升级、bundler、浏览器目标、codegen、发布配置和安全更新提升审查等级。
   - 读取 [references/review-focus.md](references/review-focus.md)，执行对应 Chore 检查和最多两个风险叠加项。
5. 验证改动。
   - 阅读 changed config/scripts 及必要的 consumers、CI、生成入口、测试和运行时 context。
   - 验证 clean checkout、本地、CI、SSR 和 production build 的命令、版本与环境是否一致。
   - 对依赖检查 manifest/lockfile 一致性、prod/dev/peer 分类、transitive 变化、运行时兼容和 bundle 影响。
   - 对 codegen 检查 source of truth、确定性、生成命令和产物同步。
   - 对测试/工具检查错误实现是否仍会失败、glob/ignore 是否正确、缓存是否会隐藏问题。
   - 运行仓库已有且与风险相称的只读验证；不要安装依赖。区分“已运行”“仅阅读”和“未验证”。
6. 形成 findings。
   - 先收集所有 candidate findings，再完成 coverage pass。
   - 读取 [references/finding-rubric.md](references/finding-rubric.md)，执行准入、归因、去重和完整性检查。
   - 证据不足时归入 `Not verified` 或提出明确问题，不要伪装成确定缺陷。
   - 对合格问题分配稳定 finding ID、priority 和 confidence，并挂到 `cN` 或 `xN`。
7. 模板化输出。
   - 输出前完整读取 [references/output-protocol.md](references/output-protocol.md) 和 [references/output-template.md](references/output-template.md)。
   - 默认一次性输出所有适用 Chore 单元、工程契约、findings 和 validation，严格遵循 template 的标题顺序、字段和空状态；不要自创另一套格式。
   - 被 `$frontend-pr-code-review` 分发时，只返回填充后的 template 作为专审 payload，不加外围说明，供入口 skill 原样嵌入。
   - 独立调用时也使用同一 template；用户后续可用稳定 ID 下钻。
   - 同一次审查中保持 ID 稳定；新增单元只追加 ID。

## Chore Review 判定

- `Frontend correctness: patch is correct`：维护目标可复现、工具链与产物一致、兼容边界成立，且没有真实前端 bug。
- `Frontend correctness: patch is incorrect`：存在无法执行的脚本、manifest/lockfile 不一致、CI/本地分叉、错误生成产物、构建/运行时破坏或其他真实前端 bug。
- Chore 不应有意改变产品行为。发现行为变化时记录具体影响并返回编排层处理 intent mismatch。

`Frontend correctness` 描述补丁是否正确，`Frontend verdict` 描述是否阻塞合并；两者不要混为一谈。结论只覆盖前端 Chore 切片。

## 优先级

- `P0`：供应链或配置导致安全边界失守、敏感数据暴露、不可恢复发布或大范围不可用。
- `P1`：生产构建/发布失败、运行时依赖破坏、关键 CI 失效或高影响兼容回归。
- `P2`：特定环境下不可复现、测试/代码生成失真、缓存/脚本可靠性问题或重要验证缺口。
- `P3`：低影响但具体可行动的工程维护问题；不要用于纯格式或个人工具偏好。

## 导航

- `c2`：展开一个 Chore 单元。
- `c2.i1`：展开一个 finding。
- `x1`：展开跨 Chore 单元关注点。
- `blockers`、`map`、`all`、`next`、`prev`、`back`：按当前层级导航。

收到未知 ID 时，只返回合法 ID 的精简 Frontend Chore Map，不重新执行审查。
