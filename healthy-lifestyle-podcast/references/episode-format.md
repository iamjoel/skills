# 脚本与交付合同

`episode.json` 是唯一脚本源。修改文字稿后须回写此文件并重新审稿。下面仅说明结构，生产文件须填实际资料。

```json
{
  "schema_version": 1,
  "title": "本集标题",
  "language": "zh-CN",
  "sources": [{"id": "s01", "title": "实际来源标题", "url": "https://example.org/source", "accessed_at": "2026-10-23", "type": "guideline"}],
  "claims": [{"id": "c01", "text": "经核实的核心结论", "source_ids": ["s01"], "population": "实际人群", "outcome": "实际测量结局", "limitations": "实际局限", "applicability": "对听众的适用条件", "certainty": "来源分级或基于研究的谨慎描述"}],
  "chapters": [{"id": "ch01", "title": "本集的问题"}],
  "turns": [
    {"id": "t01", "speaker": "female", "chapter_id": "ch01", "text": "这个结论适用于哪些人？", "claim_ids": []},
    {"id": "t02", "speaker": "male", "chapter_id": "ch01", "text": "此处填写经核实的解释与必要条件。", "claim_ids": ["c01"], "pause_after_ms": 350}
  ],
  "reviews": {
    "evidence": {"status": "pending", "reviewer": "", "reviewed_at": "", "notes": "待查证"},
    "editorial": {"status": "pending", "reviewer": "", "reviewed_at": "", "notes": "待审稿"}
  }
}
```

## 约束

- 各集合 ID 唯一，仅用字母、数字、连字符、下划线，不超过 64 字符。
- sources 可补 `published_at`、`funding`、`scope`、`notes`，记录日期、利益关系和实际核对范围。
- claims 填写示例中的字段；缺数据写“来源未报告”，不编造，不以“无”掩盖尚未查证。
- turns 顺序即播出顺序；两位主持、所有章节、所有结论均须使用。章节依 chapters 顺序连续出现，不返回已结束的章节。
- 可选 `tts_text` 仅作发音规范化，语义须与 text 相同，由实际审稿检查。链接、引用编号和制作提示不进入配音。
- 可选 pause_after_ms 范围 0–2000 毫秒，技术分段停顿独立设置。
- reviews 的 passed 需要真实执行者、日期、检查说明与 `content_sha256`。先对 pending 稿运行校验，获得 `review_content_sha256`，实际审稿后将该值分别填入两条通过记录。它绑定除 reviews 外的当前全部内容，修改后必须重新检查；用户授权、JSON 校验通过、生成完成均不能代替审稿。

## 阶段与结果

1. `validate_episode.py episode.json` 检查结构和引用；加 `--export-dir /absolute/script` 导出 transcript.md、show-notes.md、evidence.json。拒绝覆盖已有不同内容。
2. `render_episode.py plan episode.json` 显示技术分段，不启动模型。
3. `render_episode.py render episode.json --output-dir /absolute/render` 要求两轮审稿通过，生成片段和 manifest，完整装配后生成 draft.wav 与 audio-review.json。
4. 根据实际回听填写 audio-review.json，再 `render_episode.py finalize /absolute/render` 生成以当前指纹命名的交付目录。

audio-review.json 包含 `manifest_fingerprint`、整体 `status/reviewer/reviewed_at/notes` 及逐段 `id/sha256/status/notes`。逐段通过与整体通过分别记录；改稿、换声线或重做后核对当前版本。没有实际听审时保留 pending。

## 交付文件

- episode.wav：48 kHz 单声道 16-bit PCM 母版；有 FFmpeg 时额外生成 episode.mp3。
- episode.json、evidence.json、transcript.md、show-notes.md：脚本、证据与说明。
- render-manifest.json、audio-review.json：实测时长、片段哈希、参数和审核。
- 章节时间点按实际片段和停顿计算；初稿仅列章节，不冒充实测时间轴。
- 定稿目录按指纹区分版本，不静默覆盖其他版本的成品。
