---
name: submit-git-changes
description: Inspect current Git changes, generate exactly three English candidate commit messages, optionally draft a Markdown pull request description, then wait for the user to select one, commit, and push. When the submission request explicitly asks to create a pull request, create it after a successful push and return its URL. For the branch's first commit, output a generated pull request description with an optional Linear ID unless the same description was already provided with the candidates. If remote integration causes conflicts, list the conflicted files and ask before resolving them automatically. Use whenever the user says “提交”, “提交当前改动”, “提交并提供描述”, “提交并创建 PR”, “commit”, “commit and push”, or otherwise asks to submit the current repository changes.
---

# 提交 Git 改动

严格按顺序完成候选信息、可选的 Markdown 描述草稿、用户选择、提交、推送、可选的 PR 创建、首次提交的 PR 描述输出和冲突处理。把用户说“提交”视为提交并推送当前仓库改动的请求；把“提交并提供描述”“提交并生成 PR 描述”或同义请求视为还要在候选信息阶段提供 Markdown PR 描述草稿；把“提交并创建 PR”或同义请求视为推送成功后创建 PR，并返回 PR 链接。不得跳过下面的确认点。

## 不可跳过的确认点

- 所有候选和最终 commit 信息都必须使用英文，即使用户或仓库使用其他语言。
- 在用户选择 commit 信息前，不得暂存、commit、push 或创建 PR。
- 在用户明确同意自动解决冲突前，不得编辑冲突文件、完成 merge 或继续 push。
- 不得使用 force push、`reset --hard`、丢弃改动、绕过 hooks，或自行 amend 已有 commit。
- 保留用户的全部现有改动；任何额外变更都必须服务于解决已确认的 merge 冲突。
- 只有用户在提交请求或当前对话中明确提供 Linear ID 时，才在 PR 描述中输出 Linear 关联行；不得猜测、补全或主动创建 Linear ID。根据实际改动的主要性质选择动词：功能使用 `Implements <Linear ID>`，重构使用 `Completes <Linear ID>`，只有 Bug 修复使用 `Fixes <Linear ID>`。不得把功能或重构统一写成 `Fixes`；如果一次改动包含多种性质，按主要目标选择。
- 只有用户明确要求在提交时提供描述或创建 PR，才在阶段一提前输出 Markdown PR 描述；普通“提交”请求不提前输出。
- 提前输出的描述是基于当时 diff 和验证结果生成的草稿。如果等待用户选择期间改动发生实质变化，必须与 commit 候选一起重新生成。
- 每次实际输出 PR 描述时，都必须把完整描述包裹在带 `markdown` 语言标记的 fenced code block 中，方便用户直接复制；代码块内不得包含额外说明。
- 只有用户在提交请求或当前对话中明确要求创建 PR，才可以在推送成功后创建 PR；仅要求“提供描述”不得创建 PR。
- 创建 PR 前必须检查相同 head 与 base 是否已有 open PR，避免重复创建。创建成功后必须获取并返回 PR 的规范链接。
- 每次执行 `git push` 前，都必须在同一个 shell 会话中设置阶段二指定的代理环境变量；不要把代理写入 shell profile 或 Git 全局配置。

## 阶段一：检查改动并生成候选信息

1. 确认当前目录属于 Git worktree；否则说明问题并停止。
2. 检查分支、upstream、remote、工作区状态、已暂存与未暂存 diff，并查看未跟踪文件中与提交有关的内容。不要输出密钥或凭据的内容。
3. 如果没有可提交的改动，告知用户并停止。
4. 如果仓库已处于 merge、rebase、cherry-pick 或 revert 中，先报告当前状态和未解决文件，不要启动新的提交流程。
5. 如果发现疑似密钥、凭据、`.env`、异常大的二进制文件或嵌套仓库，先指出风险并询问是否排除；不要打印敏感值。
6. 在 commit 前判定本次是否为当前分支的第一个提交：
   - 按以下顺序解析 base：用户明确指定的 base、`branch.<current>.gh-merge-base`、唯一 remote 的默认分支或 `origin` 的默认分支。无法唯一解析时，列出候选并询问用户，不要猜测。
   - 以 commit 前的状态运行等价于 `git rev-list --count <base>..HEAD` 的只读检查。结果为 `0` 时记录为“本次是分支第一个提交”；大于 `0` 时记录为“分支已有提交”。
7. 如果用户提供了 Linear ID，保留用户提供的单行 ID 原文；如果值为空、包含换行或控制字符，要求用户重新提供，不要自行修正。
8. 记录用户是否明确要求创建 PR，以及是否指定 draft、base 或 title。没有明确要求时记录为“不创建 PR”；仅要求提供 PR 描述不等于要求创建 PR。
9. 根据全部当前改动生成恰好 3 条单行 commit 信息。每条都必须：
   - 严格以 `feat: `、`fix: ` 或 `chore: ` 之一开头；不要使用带 scope 的 `feat(x):` 形式。
   - 准确反映主要改动，不把维护工作误写成新功能，也不虚构未发生的修改。
   - 冒号后的自然语言全部使用英文；不要因为用户或仓库使用中文或其他语言而切换语言。
   - 简洁、具体。遇到非英文文件名、术语或标识符时，用英文描述其作用，不要把非英文自然语言写入 commit 信息。
10. 先用一句话概括准备提交的改动，再按 `1`、`2`、`3` 列出英文候选信息。
11. 如果用户明确请求在提交时提供描述或创建 PR，紧接候选信息按“Markdown 描述格式”输出一份基于当前 diff 和已完成验证的草稿。不要添加“PR description”等额外标题；必须把完整描述包裹在带 `markdown` 语言标记的 fenced code block 中。创建 PR 时使用这份描述作为 PR body。
12. 请用户回复序号，或提供一条同时符合前缀规则和全英文规则的修改版信息，然后停止并等待回复。

## 阶段二：按用户选择提交并推送

1. 收到选择后重新检查状态和 diff。如果等待期间改动发生了实质变化，重新生成 3 条候选信息；若用户已明确请求描述或创建 PR，同时重新生成 Markdown 描述，然后再次等待选择。
2. 验证最终信息严格匹配 `^(feat|fix|chore): .+`，并确认冒号后的自然语言全部为英文。如果用户提供的信息包含中文或其他非英文自然语言，给出一条英文改写并再次请求确认；不要直接提交，也不要未经确认自行替换。
3. 在通过敏感文件检查后，用 `git add -A` 暂存当前改动。确认 staged diff 非空且与刚才概括的范围一致，并运行 `git diff --cached --check`。
4. 使用用户选定的完整信息创建 commit。把信息作为单个安全引用的参数传给 Git；不要让其中的 shell 字符被执行。
5. 如果 commit hook 或 commit 命令失败，报告原始错误和当前状态，不要使用 `--no-verify`。
6. 推送当前分支。每次执行 `git push` 前，包括远端分歧处理后的重试，都先在同一个 shell 会话中执行：

   ```sh
   export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897 all_proxy=socks5://127.0.0.1:7897
   ```

   设置代理后再按以下规则推送：

   - 已有 upstream 时使用普通 `git push`。
   - 没有 upstream、但只有一个明确 remote 或存在 `origin` 时，用普通的 `git push -u <remote> HEAD` 建立 upstream。
   - 有多个可能的 remote、没有 remote，或处于 detached HEAD 时，列出可用信息并询问目标，不要猜测。
7. 推送成功后：
   - 如果用户明确要求创建 PR，无论本次是否为分支第一个提交，都继续执行“阶段四：输出描述或创建 PR”。
   - 如果用户没有要求创建 PR，但阶段一确认本次是分支第一个提交且尚未在候选信息阶段输出描述，继续执行阶段四输出首次提交的 PR 描述。
   - 其他情况直接进入完成报告。已经提前输出的描述不要原样重复；只有实际提交 diff 或验证结果使描述内容失实时，才输出更新后的版本。

## 阶段三：处理远端分歧与冲突

只在 push 因 non-fast-forward 或远端领先而被拒绝时执行本阶段；认证失败、权限不足、受保护分支或网络错误不属于 merge 冲突，应直接报告。冲突处理后 push 成功时，如果用户明确要求创建 PR，继续阶段四创建 PR；否则仅在这是分支第一个提交且尚未提前输出描述时继续阶段四。已经提前输出的描述仅在合并结果使其失实时更新。

1. 确认刚创建的 commit 完整且工作区适合合并，然后 fetch 目标 remote。
2. 使用普通 merge 将对应远端分支合入当前分支，不要 rebase，不要 force push。
3. 如果 merge 无冲突，完成 merge 后按阶段二步骤 6 重新设置代理，再次普通 push。
4. 如果 merge 产生冲突：
   - 使用 Git 的 unmerged 状态获取文件列表，例如 `git diff --name-only --diff-filter=U`。
   - 只列出冲突文件路径和必要的简短说明。
   - 明确询问：是否允许自动解决这些 merge 冲突、验证结果并继续 push？
   - 停止并等待明确确认。
5. 用户确认后：
   - 分别检查 base、ours、theirs 和周边代码，按双方意图解决每个冲突；除非语义明显，否则不要整文件套用 ours 或 theirs。
   - 删除所有冲突标记，确认 Git 不再报告 unmerged paths，并运行 `git diff --check`。
   - 按仓库约定运行与冲突范围相称的测试或检查。若验证发现由合并造成的失败，报告失败且不要 push。
   - 暂存已解决文件，完成 merge commit，然后按阶段二步骤 6 重新设置代理，再次使用普通 push。
6. 用户拒绝或尚未确认时，不修改冲突文件、不完成 merge、不 push；明确说明仓库仍处于 merge conflict 状态。

## 阶段四：输出描述或创建 PR

先根据实际 commit diff 和已完成的验证生成或更新“Markdown 描述格式”中的完整 PR 描述。提前输出的草稿仍然准确时直接复用；commit diff、merge 结果或验证结果使其失实时必须更新。

如果用户明确要求创建 PR：

1. 确认当前分支不是 detached HEAD、目标 commit 已成功推送、base 分支已经按阶段一的规则解析，且远端托管平台支持当前可用的 PR 创建工具。缺少必要信息时列出已知分支、remote 和 base，并询问用户，不要猜测。
2. 使用当前分支作为 head、已解析或用户指定的分支作为 base；创建 PR 时把 `origin/main` 这类 remote-tracking ref 转换为托管平台需要的分支名 `main`。用户没有指定 title 时，使用最终 commit 信息作为 PR title；用户没有指定 draft 时，创建 ready-for-review PR，不要自行改成 draft。
3. 创建前通过托管平台工具或 CLI 查询相同 head 与 base 的 open PR。如果已经存在，不要重复创建；返回现有 PR 链接，并在完成报告中说明未新建 PR。
4. 推送成功后再创建 PR。使用最终 Markdown 描述作为 PR body，并优先使用已认证的托管平台工具；对于 GitHub remote，可使用 GitHub connector，或在其不可用时使用 `gh pr create`。
5. 从创建结果中获取规范 PR URL；若结果未包含 URL，再查询刚创建的 PR。只有获得可访问的 URL 后，才报告 PR 创建成功。
6. 如果创建或查询 PR 失败，保留已经完成的 commit 和 push，报告原始错误及当前状态，不要声称 PR 已创建，也不要回滚或重复 push。

如果用户没有要求创建 PR，仅在本次是分支第一个提交且候选阶段尚未输出描述时，按下面格式输出 PR 描述。若候选阶段已输出且仍然准确，不要重复。

## Markdown 描述格式

根据实际 diff 和已完成的验证生成 1–3 条具体的英文 Summary bullet。优先描述用户可观察的行为、关键流程变化和必要的防护，不要只改写 commit subject，也不得虚构测试、行为或依赖。

如果用户提供了 Linear ID，输出以下 Markdown，将占位符替换为实际 Summary、根据主要改动性质选定的 Linear 动词和 Linear ID。功能使用 `Implements`，重构使用 `Completes`，只有 Bug 修复使用 `Fixes`：

```markdown
## Summary

- <specific change summary>
- <specific change summary>

<Linear verb> <Linear ID>

## Checklist

- [x] I've added a test for each change that was introduced, and I tried as much as possible to make a single atomic change.
```

如果用户没有提供 Linear ID，完全省略 Linear 关联行：

```markdown
## Summary

- <specific change summary>
- <specific change summary>

## Checklist

- [x] I've added a test for each change that was introduced, and I tried as much as possible to make a single atomic change.
```

实际输出时必须保留示例中的 `markdown` 代码围栏，并把完整描述放在同一个代码块中。代码块外只保留流程所需的候选信息、选择提示或完成报告，不要重复描述正文。

## 完成报告

最终只报告实际完成的结果：提交与推送是否成功、commit SHA、信息、分支、remote，是否创建 merge commit，以及运行了哪些验证。如果用户要求创建 PR，还必须报告 PR 是否新建成功；成功或已存在时返回 PR 链接，失败时报告错误且不得虚构链接。如果用户没有要求创建 PR，且这是分支第一个提交且尚未提前输出描述，按阶段四直接追加 PR 描述 Markdown；若描述已经提前输出且仍然准确，不要重复。不要声称尚未完成的动作已经成功。
