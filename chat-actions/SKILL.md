---
name: chat-actions
description: "在当前聊天中用 #help 查看说明、#setting 配置命令目录、#init 选择命令文件、#ls 查看选中文件、#la 查看全部命令、#cv 查看并配置共享变量。用 JSON 中配置的 # 快捷命令打开对应卡片，支持填写变量、复制、运行，以及处理确认后的 #increment、#reset 和已配置的「喝水 +n」记录。"
---

# 聊天命令

## `#help`

收到 `#help` 时，原样输出下面对应语言的 Markdown 表格。以用户在当前会话中最近一条自然语言消息判断中文或英文，忽略纯命令、路径和表单生成的消息。用户明确指定语言时以其指定为准。无法判断或会话使用其他语言时用英文。只输出一张表格，无需运行脚本或配置命令目录。

### 中文

| 命令 | 说明 |
| --- | --- |
| `#help` | 查看聊天命令及其用法。 |
| `#setting` | 查看和更新当前聊天的命令目录。 |
| `#init` | 从下拉框选择或更改当前聊天使用的 JSON 命令文件。 |
| `#ls` | 查看当前选中的文件里的命令。 |
| `#la` | 查看命令目录中的全部命令，按文件分标签展示。 |
| `#cv` | 查看和配置选中文件的共享变量。 |
| `#<快捷命令>` | 打开对应的命令卡片，例如 `#cb`。 |

### English

| Command | Description |
| --- | --- |
| `#help` | Show the chat commands and how to use them. |
| `#setting` | View or update the command directory for this chat. |
| `#init` | Choose or change the JSON command file for this chat from a dropdown. |
| `#ls` | Show commands from the selected file. |
| `#la` | Show all commands in the command directory, with a tab for each file. |
| `#cv` | View and configure shared variables for the selected file. |
| `#<shortcut>` | Open the matching command card, for example `#cb`. |

## 命令操作

命令目录由用户通过 `#setting` 或直接提供的路径配置。以当前聊天的可写 visualization 目录作为 `OUT`，同一聊天持续使用该目录保存命令目录和选中的文件。若客户端没有该目录，在当前任务的持久可写目录中为该聊天选一个独立子目录，并沿用其绝对路径。

在本技能目录运行对应操作。

| 用户输入 | 操作 |
| --- | --- |
| 单独输入 `#setting` | `python3 -B scripts/chat_actions.py settings --output-dir "$OUT"` |
| 单独输入 `#init` | `python3 -B scripts/chat_actions.py init --output-dir "$OUT"` |
| `#ls` | `python3 -B scripts/chat_actions.py list --output-dir "$OUT"` |
| `#la` 或明确要求输出所有命令 | `python3 -B scripts/chat_actions.py list-all --output-dir "$OUT"` |
| 单独输入 `#cv` | `python3 -B scripts/chat_actions.py variables --output-dir "$OUT"` |
| 单独输入快捷命令，例如 `#cb` | `python3 -B scripts/chat_actions.py shortcut --shortcut '#cb' --output-dir "$OUT"`。把用户输入的快捷命令作为独立参数传入。 |
| `#setting` 后跟 `{"directory":"/绝对/目录"}`，或用户直接要求更新路径 | 将 JSON 通过标准输入传给 `python3 -B scripts/chat_actions.py save --output-dir "$OUT"`。 |
| `#init` 后跟 `{"directory":"/绝对/目录","file":"文件名.json"}` | 将 JSON 通过标准输入传给 `python3 -B scripts/chat_actions.py select --output-dir "$OUT"`。 |
| `#cv` 后跟 `{"directory":"/绝对/目录","file":"文件名.json","values":{"变量名":"新值"}}` | 将 JSON 通过标准输入传给 `python3 -B scripts/chat_actions.py save-variables --output-dir "$OUT"`。 |

`#setting` 和 `#init` 可重复打开，表单会显示当前设置。`#init` 的下拉框只列出命令目录直属的 JSON 文件名。用户在选择框点击「确定」或在设置页点击「保存」后，确认请求会作为消息发回当前聊天。通过标准输入或安全引用的 heredoc 原样传入 JSON。每次提交都更新当前聊天的设置，成功后返回脚本的确认文字。更换目录后需要重新选择命令文件。

`#ls` 每次重读选中的文件并直接展示命令。用户输入 `#la` 或明确要求读取整个目录的命令时，重新读取目录中的 JSON 并按文件分组。单个列表的标题和全部列表的标签使用各 JSON 顶层的 `name`，缺省时使用去掉 `.json` 后缀的文件名。读取错误显示在对应的组内。尚未配置目录时引导用户用 `#setting`。尚未选择文件或文件已删除时，引导用户用 `#init`。若保存目录失败，说明具体错误并重新展示设置页，保留之前的目录。

命令可选配 `"shortcut": "#cb"`。右侧动作按钮用灰色英文括号显示快捷命令，例如 `运行 (#cb)`。优先标在「运行」按钮，只有「复制」时标在那里。快捷命令以 `#` 开头，之后可使用字母、数字、下划线或连字符。单独输入时，在当前命令目录的所有 JSON 中忽略大小写查找。给不同命令配置唯一的名称，内建命令和 `#increment`、`#reset` 为保留名称。找到时展示对应卡片，由用户在卡片内填写变量、复制或确认运行。未找到或重复时返回脚本错误。

界面操作成功时返回生成片段的绝对路径。将路径放进下面的内容标记，单独占一行。设置页用标题 `命令设置`，选择页用 `选择命令文件`，`#ls` 用分组名称，`#la` 用 `命令列表`，`#cv` 用 `变量配置`，快捷命令面板用对应的快捷命令作标题。

```text
visualize{"path":"<脚本返回的绝对路径>","title":"命令列表"}
```

每个 JSON 顶层的 `info` 在分组顶部显示自定义 HTML，也接受文本列表。文本中的 `{name}` 引用分组变量。HTML 支持常见展示标签、`class` 和无障碍标签，渲染时会移除脚本和事件属性。用 `info-progress-ring` 配合 `data-progress-value` 和 `data-progress-max` 绘制环形进度，这两个属性可直接填写数值或用 `{name}` 引用分组变量。环旁添加可读文本，例如 `今天喝水 {waterCount} / {waterGoal} 杯`。可用数值属性 `data-progress-yellow-min` 和 `data-progress-yellow-max` 指定黄色区间，包含两个端点，较低为红色，较高为绿色。

信息区也支持外链卡片，例如 `<a class="card info-link-card" href="https://example.com/">收藏网站</a>`。使用绝对 HTTP 或 HTTPS 地址。点击链接会交给客户端的外部链接接口。将需要并排的项目放入 `<div class="info-row">`，宽度不足时自动换行。

顶层 `variables` 定义共享变量，集中在 `#cv` 面板展示。`#cv` 的「保存」会请求用户确认，并提交改过的值。值按当前聊天和命令文件保存，新打开的 `#ls`、`#la` 和快捷命令面板使用这些值。只读变量可查看。`commands[].variables` 定义仅在该命令内生效的局部变量，优先于同名的共享变量。数字变量使用 `"type": "number"`，可以设置 `default` 和 `step`。旧文件中的 `counter` 和 `count` 仍可读取。

命令以等高卡片排列，宽屏每行四张。在同一个 JSON 中，`commands[].card` 相同的命令显示在同一张卡里，例如 `"card": "喝水"`。每条命令独立编辑和运行，卡片按首次出现的位置排列。

命令模板支持 `{name}` 和 `{?name:可选片段 {name}}`。点击命令右上角的齿轮可原位编辑。编辑时，右下角的「取消」丢弃草稿，「运行」使用新值生成确认请求。未通过必填或数字校验时禁用提交按钮。只有复制动作的命令使用「复制」，仅编辑变量的命令使用「保存」。同组命令共享分组变量，局部变量各自保存。预览中的变量值用行内代码高亮，复制和运行使用展开后的纯文本。按每条命令的 `actions` 提供「复制」和「运行」。「运行」请求用户确认后，把文本发回当前聊天。

命令可用 `"increment": {"variable": "waterCount", "by": "cups"}`，将局部数字变量 `cups` 加到分组数字变量 `waterCount`。另一个命令可用 `"reset": "waterCount"` 将当天累计值重置为 0。累计变量在当前聊天中按日期保存，每天从 0 开始。

- 收到用户确认的 `#increment` 与其 JSON 时，将 JSON 原样传给 `python3 -B scripts/chat_actions.py increment --output-dir "$OUT" --date <用户所在地的今天>`。JSON 包含 `file`、`command`、字符串 `amount` 和 `requestId`。保留 `requestId`，使重试只计一次。
- 收到用户确认的 `#reset` 与其 JSON 时，将 JSON 原样传给 `python3 -B scripts/chat_actions.py reset --output-dir "$OUT" --date <用户所在地的今天>`。JSON 包含 `file`、`command` 和 `requestId`。保留 `requestId`，使重试只生效一次。
- 用户直接发送 `喝水 +n` 或 `喝水 +n杯` 时，若当前目录的 `life.json` 已配置 `water` 累加命令，用同一操作记录，传入文件名 `life.json`、命令 ID `water`、字符串数量和该次记录的唯一 `requestId`。每一条新记录使用新的编号。
- 返回累计结果，用同一日期重新生成命令列表，让分组信息显示更新后的总数。生成命令或变量面板时，如果用户所在地日期与执行主机不同，使用 `--date` 指定用户所在地的日期。

如果当前客户端只支持文字，为查询操作加 `--text`。`#setting`、`#init` 和 `#cv` 同时提供上述可直接发回聊天的提交格式。
