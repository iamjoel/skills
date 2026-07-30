# Frontend Chore Finding Rubric

把本 rubric 作为 Chore finding 的统一准入层；具体工程检查和 Chore Map 由主 skill 与 `review-focus.md` 控制。

## Candidate 流程

1. 沿每个工程职责、命令和产物路径收集 candidate findings。
2. 对每个 candidate 执行全部准入条件；任一条件不成立时不要输出 finding。
3. 按 changed location、根因和 remedy 去重；保留最强证据与最高合理优先级。
4. 完成 coverage pass，确认没有遗漏作者知道后会明确修复的问题。
5. 把合格问题挂到对应 `cN` 或 `xN`，再分配稳定 ID、priority 和 confidence。

不要为达到数量而输出 finding。没有合格问题时输出零 findings。

## 准入条件

仅在以下条件全部成立时报告 finding：

1. **实质影响**：影响正确性、构建、测试可信度、安全、兼容、可靠性、可复现性或维护性。
2. **离散可修复**：有单一清晰的缺陷与可行动方向，不是泛泛评价。
3. **工程标准相称**：修复严谨度与仓库现有标准、工具链和测试习惯相称。
4. **由本次 diff 引入**：能定位到 changed frontend Chore code/config；旧问题除非被本次改动直接暴露或扩大，否则不报告。
5. **作者会修复**：有充分理由相信作者知道后会愿意修复，而非个人工具偏好。
6. **不依赖隐含假设**：不依赖未声明的环境、命令、发布方式或作者意图。
7. **影响可证明**：能指出真实命令、环境、构建阶段、生成路径或消费方。
8. **不是有意变更**：结合标题、PR 描述、配置和测试，确认错误行为不是明确意图。

finding 必须说明触发条件、错误命令/产物/运行时结果和工程或用户影响。修复方向必须落在本次 PR 的前端 Chore 范围内。

证据不足时使用 `Not verified` 或提出具体问题，不要把推测提升为 finding。

## 项目规则归因

读取所有适用于 changed files 的项目指令。用户指定范围和格式优先；仓库内更具体作用域的规则优先于根级规则。

只有当项目规则提供通用正确性之外的具体版本、命令、生成、配置或发布不变量时，才标记为 rule-supported finding。引用真实适用规则的最小行范围。不要因为存在规则文件就发明 finding。

## 去重与完整性

- 一个独立缺陷对应一个 finding。
- 同一 changed location、根因和 remedy 的不同表现合并。
- 同一根因影响多个 Chore 单元且需要统一修复时使用 `xN.iN`。
- 完成所有 Chore 单元和跨单元项的 coverage pass，不要只返回第一个问题。
- 忽略不影响含义且不违反明确标准的格式、拼写和 nit。

## 优先级与置信度

使用主 skill 的 `P0`–`P3` 定义。为每个 finding 记录 `confidence_score: 0.0–1.0`：

- `0.90–1.00`：changed line、真实命令/环境、消费路径和错误结果均有直接证据。
- `0.75–0.89`：证据充分，但缺少运行验证或仍有一个受控的不确定因素。
- `< 0.75`：通常归入 `Not verified` 或明确问题。

## Correctness 与 Verdict

- `Frontend correctness`：Chore 补丁是否可复现、兼容且没有引入前端 bug。
- `Frontend verdict`：根据影响、优先级和验证程度选择 `Approve`、`Comment` 或 `Request changes`。

允许非阻塞 P2 导致 `patch is incorrect`，同时给出 `Comment`。

## Inline Comment

当用户明确要求 GitHub inline comment 时：

- 标题使用 `[P0]`–`[P3]` 前缀和祈使表达，最多 80 个字符。
- 正文只写一个自然段，以触发命令、环境或构建路径开头。
- 解释 changed config、错误结果、影响和紧凑修复方向。
- 位置必须与 diff 重叠，并使用理解问题所需的最短范围，通常不超过 5–10 行。
- 不重复文件和行号，不写超过 3 行的代码块；仅在明确替换代码时使用 `suggestion`。
