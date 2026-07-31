# Frontend Review Final Output Protocol

## Template 契约

默认入口输出必须完整读取并严格填充 [output-template.md](output-template.md)。入口 template 必须包含统一 Routing/Map、所有已执行专审的完整 template 输出、去重后的收口 findings、Combined Validation 和 Final Verdict。不得只输出汇总，也不得用摘要替换专审输出。若本文件与 template 冲突，以 template 为准。

## 目录

- 默认组合输出
- Review 单元下钻
- Finding 下钻
- 跨类型下钻
- Coverage 与 Validation
- GitHub inline comment
- 机器可读输出
- 导航规则

## 默认组合输出

严格使用入口 template 的顺序：

1. 输出 Routing and Coverage 与统一 Frontend Review Map。
2. 在 Specialist Reviews 中嵌入每个已执行专审的完整 template 输出；代码质量与性能结果已位于各专审的风险项中。
3. 对专审 findings 做归一化、去重和冲突裁决，再输出 Consolidated Blockers 与 Consolidated Findings。
4. 仅在 fallback 多路分发出现真实共享根因时输出 Cross-type Review 条目。
5. 汇总 Combined Validation，并用 Final Verdict 完成收口。

空类型不要输出专审占位。专审内部跨单元项使用 `bxN`、`fxN`、`rxN`、`cxN`；只有 fallback 多路分发才可能产生总 review 的 `xN`。

## Review 单元下钻

收到 `bN`、`fN`、`rN`、`cN`、`bxN`、`fxN`、`rxN` 或 `cxN` 时：

- 使用对应专审已生成的详情格式；
- 保留归一化后的 ID；
- 只展开请求的单元；
- 不重新运行其他专审；
- 在末尾提供 `map`、finding IDs 和相邻单元导航。

若专审结果只有摘要且不足以下钻，补取该单元证据，但不得重新编号。

## Finding 下钻

统一使用：

```markdown
# <finding-id> — [P1] <问题标题>

- Review type: <Bug | Feature | Refactor | Chore | Cross-type>
- Scope: <scope-id 和名称>
- Frontend location: <clickable file:line>
- Trigger: <真实可达条件>
- Introduced by diff: <changed frontend line 如何引入问题>
- Affected path: <被证明受影响的用户路径或调用方>
- Intentional change check: <为什么不是有意行为>
- Problem: <为什么代码不正确>
- User impact: <用户可见或客户端影响>
- Evidence: <调用链、状态、契约或测试证据>
- Suggested direction: <前端修复方向>
- Verification: <修复后验证方式>
- Repository rule: <仅有实质支持时提供最小引用>
- Confidence: <0.0-1.0> (<high | medium | low>)
```

## 跨类型下钻

总 review 的 `xN` 使用：

```markdown
# <cross-id> — <跨类型关注点>

- Related units: <bN/fN/rN/cN>
- Shared invariant: <共享状态、契约、缓存、路由或权限不变量>
- Root cause: <统一根因>
- Risk: <风险>

## Frontend Code Map

<各类型 changed frontend locations 与职责>

## Findings

<使用 xN.iN>

## Validation

<跨类型路径的已检查、已执行和未验证项>
```

不要仅因多个类型修改同一文件就创建 `xN`。

## Coverage 与 Validation

收到 `coverage` 时输出：

```markdown
## Frontend Coverage

| Type | Units | Changed hunks | Specialist status | Gaps |
|---|---:|---:|---|---|
| Bug | <n> | <n> | complete | — |
| Feature | <n> | <n> | complete | — |
| Refactor | <n> | <n> | partial | <gap> |
| Chore | <n> | <n> | complete | — |

- Excluded backend/context-only files: <scope>
- Unresolved frontend hunks: <none or locations>
```

收到 `validation` 时输出：

```markdown
## Frontend Validation

- Tests/code paths reviewed: <deduplicated list>
- Commands executed: <command and result>
- Static/contract checks: <checks>
- Not verified: <gaps>
- Residual risks: <risks>
```

不要把“阅读测试”写成“运行测试”，不要重复列出多个专审执行的同一命令。

## GitHub inline comment

只有用户明确要求发布或生成 inline comment 时，才把最终去重后的 finding 转换为：

```markdown
[P1] <最多 80 字符的祈使标题>

<一个自然段：以触发条件开头，解释 changed logic、错误结果、影响和修复方向。>
```

comment 位置必须与 diff 重叠且尽可能短。不要发布被聚合层判定为重复、冲突或 `Not verified` 的 specialist candidate。

## 机器可读输出

只有用户明确要求 Codex JSON 时，严格输出以下结构且不加 Markdown fence：

```json
{
  "findings": [
    {
      "title": "<以 [P0]-[P3] 开头、最多 80 字符>",
      "body": "<单段 Markdown finding>",
      "confidence_score": 0.0,
      "priority": 0,
      "code_location": {
        "absolute_file_path": "<绝对路径>",
        "line_range": {
          "start": 1,
          "end": 1
        }
      }
    }
  ],
  "overall_correctness": "patch is correct",
  "overall_explanation": "<1-3 句前端正确性说明>",
  "overall_confidence_score": 0.0
}
```

`overall_correctness` 只能是 `patch is correct` 或 `patch is incorrect`。`priority` 使用 `0`–`3`。`code_location` 必须与 diff 重叠且尽可能短。

严格 JSON 需要本地 checkout 提供绝对路径。远程-only review 无法提供绝对路径时，说明限制并继续使用规范 GitHub URL，除非用户接受非严格 schema。

## 导航规则

- 首次分配的 `bN/fN/rN/cN` 保持不变。
- 专审 `xN` 按来源稳定映射为 `bxN/fxN/rxN/cxN`。
- 聚合后新增的跨类型项追加 `xN`。
- 过滤、排序、下钻或上下文压缩后不得重新编号。
- `next` 和 `prev` 按 Frontend Review Map 顺序移动。
- `back` 从 finding 返回单元，从单元返回 map。
- 未知 ID 只返回合法 ID 的精简 map，不重做 review。
- `all` 对大型审查先提示输出较长，再展开。
