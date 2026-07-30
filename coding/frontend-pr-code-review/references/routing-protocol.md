# Frontend Review Routing Protocol

## 目录

- 标题优先路由
- 标题未命中的 fallback 分类
- 四类语义边界
- 辅助改动归属
- 分发包
- Coverage Ledger

## 标题优先路由

在解析 PR 描述、issue 或 diff 意图之前，先读取并规范化 PR title：

1. 去掉标题首尾空白。
2. 对 conventional type 做大小写不敏感匹配。
3. 支持精确前缀 `feat:`、`fix:`、`chore:`、`refactor:`。
4. 同时接受可选 scope 和 breaking marker，例如 `feat(ui):`、`fix!: `、`refactor(core)!:`。
5. type 必须位于标题开头；正文中偶然出现 `fix:` 不算命中。

等价匹配模式：

```regex
^(feat|fix|chore|refactor)(\([^)]+\))?!?:
```

命中后直接路由：

| Title type | Review type | Specialist |
|---|---|---|
| `feat` | `feature` | `$frontend-pr-feature-review` |
| `fix` | `bug` | `$frontend-pr-bug-review` |
| `chore` | `chore` | `$frontend-pr-chore-review` |
| `refactor` | `refactor` | `$frontend-pr-refactor-review` |

标题命中时：

- 把该 PR 的全部 changed frontend hunks 归给这个主类型；
- 只创建一个专审分发包；
- 仍需读取完整 diff、PR 描述、issue 和上下文来执行 review，但不要用这些内容重新分类；
- 若专审发现实际改动与标题意图冲突，把它作为 `intent mismatch` 返回编排层；
- 不因 diff 看起来像其他类型而静默改派。

## 标题未命中的 fallback 分类

只有 title 未命中四种类型时，才解析 PR 描述、issue、Before/After、测试和 diff 意图。

以“意图一致、能沿同一用户、客户端或工程路径解释的一组 changed hunks”为切片。每个 changed frontend hunk 必须有且只有一个主 owner：

- `bug`
- `feature`
- `refactor`
- `chore`

同一文件可以包含多个切片。同一 hunk 可记录次要风险标签，但不得交给多个专审生成重复 findings。

fallback 证据优先级：

1. 用户明确指定的审查范围；
2. issue 和 PR 描述中的产品/工程意图；
3. Before/After 行为；
4. changed tests、配置和调用方；
5. commit message 与作者标签。

无法归属的 frontend hunk 不得静默忽略；放入 `unresolved`，补读上下文后再分类。

## 四类语义边界

### Bug

恢复此前已经预期的行为，存在可描述的 `Observed != Expected`、缺陷路径、回归或 incident。

### Feature

新增能力或有意改变用户、UI、客户端契约、运行时行为或构建产物的可见能力。

### Refactor

保持产品行为不变，改变前端运行时代码的结构、所有权、依赖、抽象或性能实现。重点验证渲染、事件、状态、请求、副作用和契约等价。

### Chore

保持产品行为不变，维护依赖、lockfile、构建、测试工具、codegen、CI、配置、文档或其他工程系统。重点验证可复现性、环境一致性和工具链正确性。

Refactor 与 Chore 的边界：

- 主要修改前端运行时代码结构：Refactor。
- 主要修改工程系统、工具、依赖或配置：Chore。
- 工程改动有意改变产品或运行时能力：Feature。
- 维护改动恢复已损坏的工程路径且 title 未命中：有明确缺陷模型时可归 Bug。

## 辅助改动归属

仅用于 fallback 多类型分类：

- 回归测试跟随 Bug。
- 功能验收测试、用户文案、入口样式和 feature flag 跟随 Feature。
- 等价性测试、运行时代码重命名、抽取和死代码清理跟随 Refactor。
- 依赖、lockfile、构建、测试工具、codegen、CI、配置和工程文档跟随 Chore。
- 共享类型或契约根据它服务的主意图归属；同时影响多类时选择最直接的 changed consumer，并记录跨类型风险。

## 分发包

为每个非空类型构造独立分发包：

```yaml
review_type: bug | feature | refactor | chore
routing:
  source: title | fallback-analysis
  matched_title_type: feat | fix | refactor | chore | null
pr:
  identifier: <url-or-number>
  title: <title>
  description: <relevant intent>
scope:
  slice_ids: [<router-local-id>]
  changed_hunks: [<file-and-line>]
  user_or_engineering_paths: [<path>]
instructions:
  applicable: [<instruction-file-and-scope>]
context:
  related_callers: [<location>]
  contracts_or_config: [<location>]
  tests: [<location>]
validation:
  allowed_commands: [<read-only command>]
  constraints: [<constraint>]
```

要求专审使用对应 skill，接受 title-based declared intent，同时返回结构化字段和完整填充后的 specialist `output-template.md` 内容，不直接向用户发布最终报告。不要传递其他专审的 finding 或推断。

## Coverage Ledger

维护内部 ledger：

| Changed hunk | Frontend | Primary type | Routing source | Specialist | Status |
|---|---|---|---|---|---|
| `<file:lines>` | yes | chore | title | chore-review | reviewed |

完成分发后必须满足：

- 所有 changed frontend hunks 均有 owner；
- title 命中时所有 frontend hunks 使用同一 owner；
- fallback 时每个 hunk 只出现一次 primary type；
- 每个非空类型都有专审结果；
- excluded backend hunks 和原因可追踪；
- unresolved 为零，或在最终结果中明确标记 partial coverage。
