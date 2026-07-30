# Frontend Bug Review Output Template

## 使用规则

- 最终输出不要包裹在代码块中。
- H1 标题使用 `#<issueId> Review 结果`；`issueId` 取 PR 关联的 issue 编号。没有关联 issue 时使用 `PR #<prId> Review 结果`。
- 只输出 `总结`、`风险项`、`Review 详情` 三个 H2 模块，并保持顺序。
- `Review 详情` 中的代码链接只能使用带准确行号、固定到被审 commit 的 GitHub URL；不要使用本地文件路径。

## Template

```markdown
# #<issueId> Review 结果

## 总结

- 问题描述：<逻辑问题使用“在 <条件> 下，预期 <结果>，实际 <结果>”；UI 问题使用“在 <页面> 的 <位置>，<元素/布局/交互> 实际 <问题>，预期 <结果>”>
- 从根因上修复：<是 | 否>
- 当前修复方式：<一句话说明当前 patch 如何修复>

## 风险项

<!-- 每个风险重复以下块；风险类型只能二选一。没有风险时只写“无风险项。” -->
### 风险 <number>

- 类型：<没有从根因修复 | 引入了新的问题>
- 具体说明：<结合真实触发路径和代码说明风险>
- 建议修复：<给出可执行的根因修复或回归消除方向>

## Review 详情

<!-- 结合代码按真实执行顺序说明修复过程。所有链接使用被审 commit 的 GitHub blob URL。 -->
1. [触发入口](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<缺陷如何进入该路径>
2. [根因位置](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<原逻辑为什么产生问题>
3. [修复位置](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<patch 具体改变了什么，以及为何生效>
4. [回归测试](https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>#L<start>-L<end>)：<测试如何覆盖该问题；未新增或未找到时直接说明>
```
