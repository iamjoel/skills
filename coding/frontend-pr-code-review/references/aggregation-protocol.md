# Frontend Review Aggregation Protocol

## 目录

- 输入契约
- ID 归一化
- Finding 去重
- 冲突裁决
- 跨类型问题
- 整体结论
- 完整性检查

## 输入契约

每个专审结果至少包含：

```yaml
review_type: bug | feature | refactor | chore
scope: <reviewed slices and changed hunks>
correctness: patch is correct | patch is incorrect
verdict: Approve | Comment | Request changes
map_items: <stable specialist IDs>
findings: <id, priority, confidence, location, trigger, root cause, impact, remedy>
validation:
  reviewed: <paths and tests>
  executed: <commands and results>
  not_verified: <gaps>
residual_risks: <risks>
rendered_output: <完整填充后的 specialist output-template 内容>
```

缺少 scope、location 或 finding 证据时，不要猜测补全；退回专审补充或把 coverage 标为 partial。

`rendered_output` 是入口最终输出的组成部分。除稳定 ID 归一化外，不得删减、改写或用摘要替代；在入口 `Specialist Reviews` 中按 Bug、Feature、Refactor、Chore 顺序完整嵌入。

## ID 归一化

- 保留 Bug 的 `bN`、Feature 的 `fN`、Refactor 的 `rN`、Chore 的 `cN`。
- 专审内部的 `xN` 在总 review 中重映射为：Bug `bxN`、Feature `fxN`、Refactor `rxN`、Chore `cxN`。
- 只有 fallback 多路分发中真正跨两个或更多类型的问题使用总 review 的 `xN`。
- finding 与 code ID 继承归一化后的 scope ID，例如 `bx1.i1`。
- 保存 source ID 映射；用户下钻时必须返回同一项，不重新编号。

## Finding 去重

两个 finding 同时满足以下条件时视为重复：

- 指向相同或重叠的 changed frontend location；
- 触发路径相同；
- 根因相同；
- 修复方向实质相同。

合并重复项时：

1. 选择最接近根因的主 owner；
2. 合并非重复证据和受影响路径；
3. 根据实际影响重新判定 priority，不机械取最高值；
4. confidence 由合并后最弱的关键证据约束，不机械取最高值；
5. 保留所有 source IDs 供内部追踪，只公开一个 finding ID。

相同位置但根因或 remedy 不同的离散缺陷不要合并。

## 冲突裁决

### 类型冲突

- `routing.source: title`：标题类型保持权威，不重新分发。记录 specialist 提供的 intent mismatch；只有能证明具体错误结果时才形成 finding，否则放入 `Not verified` 或说明。
- `routing.source: fallback-analysis`：回到 `routing-protocol.md`，按用户范围、产品/工程意图和 Before/After 重新确定主 owner。不要让同一 hunk 保持两个主类型。

### Finding 冲突

一个专审认为是 intentional change、另一个认为是 bug 时：

1. 检查 PR/issue 的明确意图；
2. 检查旧行为、契约和测试；
3. 检查真实受影响调用方；
4. 证据仍不足时移入 `Not verified`，不要输出确定 finding。

### Priority 冲突

按触发概率、影响范围、可恢复性、安全/数据边界和用户路径重要性重判。不要投票或默认取最高。

## 跨类型问题

仅在问题无法由一个专审切片独立修复时创建 `xN`，例如：

- Feature 与 Bug 修复使用同一共享状态但产生互相覆盖；
- Refactor 改变的契约让 Feature 新路径与 Bug 旧路径出现不一致；
- Chore 修改的构建或 codegen 配置让 Feature/Refactor 的运行时产物与源码不一致；
- 多个 fallback 切片共同修改同一缓存、路由、权限、持久化、生成或发布不变量。

`xN` 必须列出涉及的 `bN/fN/rN/cN`、共享不变量、统一根因和单一修复方向。仅“多个类型都碰到同一文件”不构成跨类型问题。

## 整体结论

### Correctness

- 任一最终 finding 证明 patch 含真实前端 bug：`patch is incorrect`。
- 没有最终 finding 证明 patch 含 bug：`patch is correct`。
- 验证不足不自动制造 bug；通过 `coverage`、`not_verified`、confidence 和 verdict 表达。

### Verdict

- `Request changes`：存在 P0/P1，或仓库规则明确要求阻塞的正确性、安全、兼容性、数据或可访问性问题。
- `Comment`：存在非阻塞 finding、重大未验证风险，或 coverage partial。
- `Approve`：coverage complete、无 actionable findings，且验证足以支撑结论。

### Risk 与 Confidence

- 整体 risk 以最高实质切片风险为起点；跨类型共享状态、契约或发布路径可再提升一级。
- 整体 confidence 受最低关键专审 confidence、未验证关键路径和未执行验证约束；不要简单平均。

## 完整性检查

最终输出前确认：

- Coverage Ledger 中没有静默遗漏或重复 owner；
- 所有专审结果使用同一 PR commit/patch 快照；
- findings 已执行归因、去重和冲突裁决；
- correctness 与 verdict 分别计算；
- validation 区分已执行、仅阅读和未验证；
- 后端问题没有被包装成前端 finding；
- 最终 ID 唯一且稳定；
- 每个已执行专审的完整 `rendered_output` 已嵌入入口 template；
- partial coverage 时没有给出 `Approve`。
