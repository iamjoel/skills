# Frontend Feature Review Output Template

## 使用规则

- 最终输出不要包裹在代码块中。
- H1 标题使用 `#<issueId> Review 结果`；`issueId` 取 PR 关联的 issue 编号。没有关联 issue 时使用 `PR #<prId> Review 结果`。
- 只输出 `总结`、`风险项`、`功能 Review` 三个 H2 模块，并保持顺序。
- `功能 Review` 至少包含一个详情单元，并按独立用户能力或端到端用户路径重复；不要把不相关功能合并为一个单元。
- 每一步同时保留带准确行号、固定到被审 commit 的 GitHub URL 和逐字对应这些行的最小核心代码片段；不要使用本地文件路径。
- 未新增或未找到功能测试时，在对应步骤直接说明，并省略链接和代码块。
- `代码质量问题` 和 `性能问题` 由 Vercel React Best Practices subagent 提供候选证据，经 owner 复核后作为风险项输出。

## Template

````markdown
# #<issueId> Review 结果

## 总结

- 功能描述：<使用“对于 <目标用户>，在 <入口/条件> 下，可以 <操作> 并获得 <结果>”>
- 完成功能目标：<是 | 否>
- 当前实现方式：<一句话说明当前 patch 如何接入功能>

## 风险项

<!-- 每个风险重复以下块；没有风险时只写“无风险项。” -->
### 风险 <number>

- 类型：<没有完成功能目标 | 引入了新的问题 | 代码质量问题 | 性能问题>
- 具体说明：<结合真实用户或消费路径和代码说明功能、回归、代码质量或性能风险>
- 具体代码：[<path>#L<start>-L<end>](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)

  ```<language>
  <与链接行号一致的核心代码>
  ```

- 建议修复：<给出可执行的功能补全、回归消除、代码质量调整或性能优化方向>

## 功能 Review

<!-- 按独立用户能力或端到端用户路径重复整个详情单元，直到覆盖全部前端改动。 -->
### 详情 <number> — <用户能力或路径名称>

- 审查范围：<该单元覆盖的入口、状态、请求、渲染或调用方>

1. [功能入口](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<目标用户如何进入并触发功能>

   ```<language>
   <与链接行号一致的核心代码>
   ```

2. [核心实现](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<patch 如何实现主要能力>

   ```<language>
   <与链接行号一致的核心代码>
   ```

3. [状态与集成](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<权限、请求、状态、调用方或兼容路径如何接入>

   ```<language>
   <与链接行号一致的核心代码>
   ```

4. [功能测试](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<测试如何覆盖用户结果和关键边界>

   ```<language>
   <与链接行号一致的核心测试代码>
   ```

<!-- 未新增或未找到测试时，第 4 步改写为“4. 功能测试：未新增或未找到覆盖该路径的功能测试。”，不保留链接或代码块。 -->

````
