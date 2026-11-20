---
name: chat-actions
description: "在当前聊天中用 #setting 配置本地命令目录，用 #ls 按 JSON 文件查看、填写、复制或运行命令。适用于聊天命令面板和已配置命令目录的查看或更新。"
---

# 聊天命令

默认命令目录为 `/Users/joel/joel/storage-for-ai/actions`。以当前聊天的可写 visualization 目录作为 `OUT`，同一聊天持续使用该目录保存设置。若客户端没有该目录，在当前任务的持久可写目录中为该聊天选一个独立子目录，并沿用其绝对路径。

在本技能目录运行对应操作。

| 用户输入 | 操作 |
| --- | --- |
| `#setting` | `python3 -B scripts/chat_actions.py settings --output-dir "$OUT"` |
| `#ls` | `python3 -B scripts/chat_actions.py list --output-dir "$OUT"` |
| `#setting save` 后跟 `{"directory":"/绝对/目录"}`，或用户直接要求更新路径 | 将该 JSON 作为标准输入传给 `python3 -B scripts/chat_actions.py save --output-dir "$OUT"`。保持原始路径内容，通过安全引用的 heredoc 或标准输入直接传入。 |

保存请求来自设置表单的「保存」按钮，确认后会作为一条消息发回当前聊天。保存时读取该目录的所有直接子级 JSON 文件，并展示新列表。若目录不可读，说明具体错误并重新展示设置页，保留之前的目录。列表每次重读，且为无效 JSON 保留错误提示标签。

脚本成功时返回生成片段的绝对路径。将路径放进下面的内容标记，单独占一行。设置页使用标题 `命令设置`，列表页使用标题 `命令列表`。

```text
visualize{"path":"<脚本返回的绝对路径>","title":"命令列表"}
```

每个 JSON 使用 `variables` 定义共享参数，`commands` 定义命令，支持 `{name}` 和 `{?name:可选片段 {name}}`。按每条命令的 `actions` 提供「复制」和「运行」。「运行」由用户点击后将展开的文本发回当前聊天，请求确认后作为普通用户消息处理。列出或保存目录时只读取数据。

如果当前客户端只支持文字，给出 `#setting` 的有效路径和可直接发回聊天的保存格式，或用 `list` 加 `--text` 输出分组命令。用户可继续指明文件、命令与参数。
