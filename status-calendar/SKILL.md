---
name: status-calendar
description: 在当前聊天中配置或查看状态日历，按月记录跑步、健身和自定义状态。支持连接 Supabase 云存储和跨设备查看自己的日历。
---

# 状态日历

按用户这次的意图，在当前回复中嵌入一个视图。`OUT` 取本次聊天明确可写的 visualization 目录，没有该目录则使用当前任务持久可写的输出目录。

**查看或编辑前先确定来源。** 在 `scripts/` 中运行 `python3 -B -m providers.supabase.private_calendar target`。若已有私人项目绑定，按[私人日历的读写方式](references/supabase-auto.md#在聊天中查看和保存)从该项目读取最新记录，使用返回的行生成视图或提交编辑。未绑定私人项目时，从本技能目录执行下表的本机或已有账号命令。

| 用户意图 | 执行 |
| --- | --- |
| 配置、编辑状态或调整颜色和 emoji | `python3 -B scripts/render_card.py configure --output-dir "$OUT"` |
| 看日历、打开日历、查看结果或某月记录 | `python3 -B scripts/render_card.py month --month YYYY-MM --output-dir "$OUT"` |
| 想看看云同步设置 | `python3 -B scripts/render_card.py storage --month YYYY-MM --output-dir "$OUT"` |
| 开启云同步、自动配置/连接 Supabase、重新登录，或收到 `auto_connect` | 直接执行[自动连接流程](references/supabase-auto.md)，沿用当前月份和视图 |

将 `YYYY-MM` 换成用户所指的月份，缺省按用户当地日期取本月。首次查看直接展示真实记录和预设图例。未连接时，日历使用本机记录，配置和月历下方显示「已存本机 · 开启云同步」。完成连接后从云端读写。

用生成命令输出的**绝对路径**替换下列占位符，将对应标记单独放在最终回复中。配置只嵌入表单，结果只嵌入宽幅月历。两个视图都直接在聊天中操作。

```text
visualize{"path":"<配置表单路径>","title":"状态配置"}
visualize{"path":"<月历路径>","title":"状态日历","mode":"wide"}
visualize{"path":"<云存储表单路径>","title":"连接 Supabase"}
```

## 保存后续消息

卡片的保存按钮会请求向当前聊天发送一条带 JSON 的消息。私人项目使用上述项目读写流程。其他存储的 `configure` 和 `day` 操作，将原 JSON 对象作为标准输入传给 `python3 -B scripts/save_edit.py`，保留存储来源及修订号。通过安全的标准输入传入。

- `configure` 保存配置后，生成并嵌入用户当地**本月**的月历。
- `day` 更新指定日期后，生成并嵌入**该日期所属月份**的月历。
- 返回码为 3 时，其他编辑已经更新过日历。提示刚才的修改尚未保存，并重新展示最新配置或对应月份，供用户继续编辑。

如果当前客户端只支持文字，直接用聊天表格展示相应的配置或七列月历；用户可用下一条消息描述修改。保存时沿用同一脚本和日期、修订号规则。

## 运动记录

用户给出运动时长、距离或部位时，从当前快照取状态配置，按实际记录生成 `day` 操作。新预设如下。

| 记录 | 状态 ID |
| --- | --- |
| 力量训练不足 60 分钟 / 至少 60 分钟 | `short-gym` / `long-gym` |
| 跑步不足 5 公里，或其他有氧 | `short-run` |
| 跑步 5 至 10 公里，包含 5 和 10 | `mid-run` |
| 跑步严格大于 10 公里 | `over-ten-run` |

同一天可以各有一档力量和一档有氧。混合日的左半格显示力量颜色，右半格显示有氧颜色。未运动时清除当天的运动记录，保留与这次修改无关的自定义记录。力量条目使用 `{"stateId":"short-gym","emoji":"","parts":["🐻","🪽"]}` 的形式，部位取自配置中的 `bodyParts`，最多三个且不重复。未提到部位时留空，有氧条目只需状态 ID 和空的 `emoji`。

保留用户提供的实际运动量。力量条目的 `durationMinutes` 记录分钟数，跑步条目的 `distanceKm` 记录公里数，均使用数值。只知道档位时省略相应字段。

归档的 `long-run` 只表示旧记录中的「至少 5 公里」。按用户给出的实际距离再归入新档。若用户预设以外的日历已有自己的状态 ID 或分类，沿用其现有配置。

## 云连接

Supabase 是默认云数据源。用户提出连接时，直接通过[自动连接流程](references/supabase-auto.md)检查项目授权和数据库，建立一份私人日历。配置和月历按钮会提交相同的 `auto_connect` 意图。保留原先的 `resume` 和 `month`，在授权、选项目或确认建表后继续同一次连接。

旧卡片已经提交的 `action: "connect"` 仍可将原 JSON 安全地经 stdin 交给 `python3 -B scripts/connect_cloud.py`。旧消息未标明提供方时使用 Supabase。已连接时网络失败应报告错误，以免产生两套不同的记录。

## 接入新的数据源

在 [存储接口与注册表](scripts/storage_providers.py) 注册一个提供方，参照 [Supabase 适配器](scripts/providers/supabase/__init__.py) 实现连接、会话恢复及读写。每个提供方指定自己的聊天连接表单资源；表单沿用 `renderStorageSetup(root, data)` 并在连接消息中传回 `data.provider`。读取返回独立快照；首次写入仅在日历不存在时创建，更新按原修订号原子提交，过期写入抛出 `Conflict`。[内存提供方测试](tests/test_storage_providers.py) 演示了从注册、连接到生成月历的完整调用。
