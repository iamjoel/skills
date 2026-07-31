# Frontend Chore Review Output Template

## 使用规则

- 最终输出不要包裹在代码块中。
- H1 标题使用 `#<issueId> Review 结果`；`issueId` 取 PR 关联的 issue 编号。没有关联 issue 时使用 `PR #<prId> Review 结果`。
- 只输出 `总结`、`风险项`、`Review 详情` 三个 H2 模块，并保持顺序。
- `Review 详情` 至少包含一个详情单元，并按独立依赖、配置、工具、生成或发布职责重复；不要把不相关维护合并为一个单元。
- 每一步同时保留带准确行号、固定到 base 或 head commit SHA 的 GitHub URL 和逐字对应这些行的最小核心代码片段；不要使用本地文件路径。
- 未新增或未找到验证时，在对应步骤直接说明，并省略链接和代码块。

## Template

````markdown
# #<issueId> Review 结果

## 总结

- 维护目标：<使用“将 <旧依赖/工具/配置/产物> 维护为 <新状态>，并保持 <产品、构建、测试或发布不变量> 不变”>
- 完成维护目标：<是 | 否>
- 产品行为保持：<是 | 否>
- 当前维护方式：<一句话说明当前 patch 如何同步依赖、配置、命令或产物>

## 风险项

<!-- 每个风险重复以下块；风险类型只能二选一。没有风险时只写“无风险项。” -->
### 风险 <number>

- 类型：<没有完成维护目标 | 引入了新的问题>
- 具体说明：<结合真实工程或用户路径和代码说明未完成的目标或新问题>
- 建议修复：<给出可执行的维护补全或回归消除方向>

## Review 详情

<!-- 按独立依赖、配置、工具、生成或发布职责重复整个详情单元，直到覆盖全部前端改动。 -->
### 详情 <number> — <维护单元名称>

- 审查范围：<该单元覆盖的 source of truth、命令、产物、环境或消费者>

1. [维护前状态](https://github.com/<owner>/<repo>/blob/<base-commit-sha>/<path>#L<start>-L<end>)：<原依赖、配置、命令或产物状态，以及需要保持的不变量>

   ```<language>
   <与链接行号一致的维护前核心代码或配置>
   ```

2. [维护改动](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)：<patch 如何更新 source of truth、配置或工具>

   ```<language>
   <与链接行号一致的维护核心代码或配置>
   ```

3. [消费或工程链路](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)：<脚本、CI、生成产物或运行时消费方如何同步>

   ```<language>
   <与链接行号一致的消费或工程链路核心代码>
   ```

4. [验证](https://github.com/<owner>/<repo>/blob/<head-commit-sha>/<path>#L<start>-L<end>)：<测试、构建或生成检查如何证明维护目标>

   ```<language>
   <与链接行号一致的核心验证代码或配置>
   ```

<!-- 未新增或未找到验证时，第 4 步改写为“4. 验证：未新增或未找到覆盖该单元的验证。”，不保留链接或代码块。 -->
````
