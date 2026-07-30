# Frontend PR Code Review Output Template

## 使用规则

- 最终输出不要包裹在代码块中。
- 保持下列 H1/H2 顺序，替换所有占位符并删除 HTML 注释。
- `Specialist Reviews` 必须包含本次实际执行的每个专审完整 template 输出，顺序固定为 Bug、Feature、Refactor、Chore；未执行的类型不输出占位。
- 专审输出除稳定 ID 归一化外必须完整保留。入口层的收口内容放在专审输出之后。
- 无 P0/P1 时使用指定 Blockers 空状态；无 consolidated finding 时使用指定 Findings 空状态。

## Template

```markdown
# Frontend PR Code Review

## Routing and Coverage

- PR title: <title>
- Routing source: <title: feat|fix|chore|refactor | fallback analysis>
- Specialists executed: <Bug/Feature/Refactor/Chore list>
- Frontend coverage: <complete | partial>
- Frontend files reviewed: <number>
- Changed frontend hunks reviewed: <number>
- Excluded backend/context-only scope: <scope or None>
- Unresolved frontend scope: <scope or None>

## Frontend Review Map

| id | 类型 | 审查单元 | 规模 | 风险 | 结论 | 最高级别 | Findings |
|---|---|---|---|---|---|---|---:|
| `<bN/fN/rN/cN/xN>` | <Bug/Feature/Refactor/Chore/Cross-type> | <审查单元> | <Small/Medium/Large> | <Low/Medium/High> | <Pass/Issues/Not fully verified> | <P0-P3/—> | <number> |

## Specialist Reviews

<!-- 只嵌入实际执行的类型；按以下固定顺序。每个占位符替换为对应专审完整 output-template 结果。 -->
{{BUG_REVIEW_OUTPUT}}

{{FEATURE_REVIEW_OUTPUT}}

{{REFACTOR_REVIEW_OUTPUT}}

{{CHORE_REVIEW_OUTPUT}}

## Consolidated Blockers

<!-- 重复最终去重后的 P0/P1；没有时只写 No frontend blocking findings. -->
- `<finding-id>` `[P0|P1]` <一句话摘要>

## Consolidated Findings

| id | Type | Priority | Confidence | 问题 | Frontend code/config |
|---|---|---|---:|---|---|
| `<finding-id>` | <Bug/Feature/Refactor/Chore/Cross-type> | <P0-P3> | <0.0-1.0> | <摘要> | <clickable file:line> |

<!-- 没有最终 finding 时，用 No actionable frontend findings. 代替表格 -->

## Cross-type Review

<!-- fallback 多路分发且存在真实跨类型问题时重复；否则只写 No cross-type frontend issues. -->
### `<cross-id>` — <跨类型关注点>

- Related units: <bN/fN/rN/cN>
- Shared invariant: <共享不变量>
- Root cause: <统一根因>
- Risk: <风险>
- Findings: <xN.iN list or None>
- Validation: <跨类型验证>

## Combined Validation

- Frontend paths/config reviewed: <去重后的范围>
- Tests/commands reviewed: <去重后的测试与命令>
- Commands executed: <命令与结果>
- Static/contract checks: <检查>
- Not verified: <未验证或 None>
- Residual frontend risks: <残余风险或 None>

## Final Verdict

- Frontend verdict: <Approve | Comment | Request changes>
- Frontend correctness: <patch is correct | patch is incorrect>
- Frontend risk: <low | medium | high>
- Overall confidence: <0.0-1.0>
- Rationale: <1-3 句最终收口说明>

结论仅覆盖该 PR 的前端改动。
```
