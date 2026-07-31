# Frontend Refactor Review Output Template

## 使用规则

- 最终输出不要包裹在代码块中。
- H1 标题使用 `#<issueId> Review 结果`；`issueId` 取 PR 关联的 issue 编号。没有关联 issue 时使用 `PR #<prId> Review 结果`。
- 只输出 `总结`、`风险项`、`Review 详情` 三个 H2 模块，并保持顺序。
- `Review 详情` 至少包含一个详情单元，并按独立重构职责、迁移边界或行为不变量重复；不要把不相关重构合并为一个单元。
- 每一步同时保留带准确行号、固定到 base 或 head commit SHA 的 GitHub URL 和逐字对应这些行的最小核心代码片段；不要使用本地文件路径。
- 未新增或未找到等价性测试时，在对应步骤直接说明，并省略链接和代码块。

## Template

````markdown
# #<issueId> Review 结果

## 总结

- 重构目标：<使用“将 <旧职责/重复路径/耦合> 重构为 <新结构>，并保持 <关键用户或客户端行为> 不变”>
- 完成重构目标：<是 | 否>
- 行为保持：<是 | 否>
- 当前重构方式：<一句话说明当前 patch 如何调整职责、接口或调用关系>

## 风险项

<!-- 每个风险重复以下块；风险类型只能二选一。没有风险时只写“无风险项。” -->
### 风险 <number>

- 类型：<没有完成重构目标 | 引入了新的问题>
- 具体说明：<结合真实调用路径和代码说明未完成的目标或新问题>
- 建议修复：<给出可执行的迁移补全、结构调整或回归消除方向>

## Review 详情

<!-- 按独立重构职责、迁移边界或行为不变量重复整个详情单元，直到覆盖全部前端改动。 -->
### 详情 <number> — <重构单元名称>

- 审查范围：<该单元覆盖的旧职责、新结构、调用方或行为不变量>

1. [旧结构](https://github.com/<owner>/<repo>/blob/<base-commit-sha>/<path>#L<start>-L<end>)：<原职责、重复路径或耦合，以及需要保持的不变量>

   ```<language>
   <与链接行号一致的旧结构核心代码>
   ```

2. [新结构](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)：<patch 如何重新分配职责、收窄接口或消除重复>

   ```<language>
   <与链接行号一致的新结构核心代码>
   ```

3. [调用方迁移](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)：<相关调用方、注册入口或兼容层如何完成迁移>

   ```<language>
   <与链接行号一致的迁移核心代码>
   ```

4. [等价性测试](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)：<测试如何证明行为保持>

   ```<language>
   <与链接行号一致的核心测试代码>
   ```

<!-- 未新增或未找到测试时，第 4 步改写为“4. 等价性测试：未新增或未找到覆盖该单元的等价性测试。”，不保留链接或代码块。 -->
````
