---
name: chat-actions
description: "在当前聊天中用 #help 查看命令说明，用 #setting 配置本地命令目录，用 #init 选择 JSON 命令文件，用 #ls 查看选中文件里的命令，用 #la 查看全部命令。支持在命令面板填写参数、复制或运行命令。"
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

### English

| Command | Description |
| --- | --- |
| `#help` | Show the chat commands and how to use them. |
| `#setting` | View or update the command directory for this chat. |
| `#init` | Choose or change the JSON command file for this chat from a dropdown. |
| `#ls` | Show commands from the selected file. |
| `#la` | Show all commands in the command directory, with a tab for each file. |

## 命令操作

命令目录由用户通过 `#setting` 或直接提供的路径配置。以当前聊天的可写 visualization 目录作为 `OUT`，同一聊天持续使用该目录保存命令目录和选中的文件。若客户端没有该目录，在当前任务的持久可写目录中为该聊天选一个独立子目录，并沿用其绝对路径。

在本技能目录运行对应操作。

| 用户输入 | 操作 |
| --- | --- |
| 单独输入 `#setting` | `python3 -B scripts/chat_actions.py settings --output-dir "$OUT"` |
| 单独输入 `#init` | `python3 -B scripts/chat_actions.py init --output-dir "$OUT"` |
| `#ls` | `python3 -B scripts/chat_actions.py list --output-dir "$OUT"` |
| `#la` 或明确要求输出所有命令 | `python3 -B scripts/chat_actions.py list-all --output-dir "$OUT"` |
| `#setting` 后跟 `{"directory":"/绝对/目录"}`，或用户直接要求更新路径 | 将 JSON 通过标准输入传给 `python3 -B scripts/chat_actions.py save --output-dir "$OUT"`。 |
| `#init` 后跟 `{"directory":"/绝对/目录","file":"文件名.json"}` | 将 JSON 通过标准输入传给 `python3 -B scripts/chat_actions.py select --output-dir "$OUT"`。 |

`#setting` 和 `#init` 可重复打开，表单会显示当前设置。`#init` 的下拉框只列出命令目录直属的 JSON 文件名。用户在选择框点击「确定」或在设置页点击「保存」后，确认请求会作为消息发回当前聊天。通过标准输入或安全引用的 heredoc 原样传入 JSON。每次提交都更新当前聊天的设置，成功后返回脚本的确认文字。更换目录后需要重新选择命令文件。

`#ls` 每次重读选中的文件并直接展示命令。仅当用户输入 `#la` 或明确要求输出所有命令时，才读取和展示整个目录的命令。全部列表按文件分标签，无效 JSON 在所属标签内显示错误。尚未配置目录时引导用户用 `#setting`。尚未选择文件或文件已删除时，引导用户用 `#init`。若保存目录失败，说明具体错误并重新展示设置页，保留之前的目录。

界面操作成功时返回生成片段的绝对路径。将路径放进下面的内容标记，单独占一行。设置页用标题 `命令设置`，选择页用 `选择命令文件`，列表页用 `命令列表`。

```text
visualize{"path":"<脚本返回的绝对路径>","title":"命令列表"}
```

每个 JSON 使用 `variables` 定义共享参数，`commands` 定义命令，支持 `{name}` 和 `{?name:可选片段 {name}}`。含变量的命令可点「编辑变量」原位填写，再点右侧「保存」。输入的值在当前面板中应用到该条命令的预览、「复制」和「运行」。按每条命令的 `actions` 提供「复制」和「运行」。「运行」由用户点击后将展开的文本发回当前聊天，请求确认后作为普通用户消息处理。

如果当前客户端只支持文字，为查询操作加 `--text`。`#setting` 和 `#init` 同时提供上述可直接发回聊天的提交格式。
