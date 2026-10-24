# 本机 VoxCPM2

先运行 `render_episode.py doctor`。在 PATH 查 voxcpm，或用 `~/.local/bin/voxcpm`。模型由独立安装维护，Skill 不下载模型。当前安装和接口以 `voxcpm --help`、doctor 及本地实际运行时为准。

## 声音

assets/show.json 分别维护人格、风格和 reference。知夏轻松活泼、有自然笑意，关键结论和风险讨论放缓。姓名与音色长期保持，主讲职责轮换。

参考音频必须非空、单声道、16-bit PCM WAV，推荐 16 kHz；模型输出 48 kHz。相同 seed/style 不能保证固定音色，后续片段复用各自 reference。

```bash
python3 SKILL_DIR/scripts/render_episode.py audition --speaker male --output /absolute/male-audition.wav
python3 SKILL_DIR/scripts/render_episode.py audition --speaker female --output /absolute/female-audition.wav
afconvert -f WAVE -d LEI16@16000 -c 1 /absolute/male-audition.wav /absolute/male-reference.wav
```

保留清晰无背景音的短参考音频，试听疑问、解释和关怀表达。未实际回听的初始声线标为待试听，不声称用户已选定。声音来源与文件哈希记在 assets/voices/selection.json。

## 合成

- 正式节目先研究与审稿；不含医学断言的试音可独立执行。
- 逻辑回合内部按自然句界拆段，通常每段 30–60 个汉字，短问题保持完整；不得静默截断长句。
- max_steps=200 约为 32 秒上限，不是语速。长文分段，必要时有意提高上限并回听。
- 默认 seed 42、timesteps 10、cfg 2、temperature 1，与当前启动器一致。
- 优先常驻本地模型串行生成。脚本只停止自己启动的服务，复用有效的既有服务。
- 当前 HTTP 字段：model=voxcpm2、input、response_format=wav、reference_audio（WAV base64）、seed、max_steps、inference_timesteps、cfg_value、temperature。风格在 input 开头圆括号内。
- 男女角色通过各自 reference 绑定，不使用不存在的男女 voice 参数；无需把参考音频逐字稿拼进台词。
- 结果须非空、48 kHz、单声道、16-bit PCM。异常有限重试，失败则停止装配并保留合格缓存。
- 接近长度上限、时长异常等标记回听；文件头、时长和转写均不能单独证明正确。
- 缓存关联台词、reference、风格、参数、引擎版本；`--redo <segment-id>` 只重做指定片段。
- 重做请求先持久化失效状态；即使重做中断，下一次普通 render 也会继续补做，不复活旧声音和旧听审。同一目录同时只允许一项生成或定稿操作。

## 回听与装配

逐段检查首尾、数字、单位、否定词、药名、限制条件和音色；整集检查顺序、接续、停顿与完整含义。实际回听后才能更新通过状态。

默认回合停顿 280 毫秒、章节停顿 650 毫秒只是起点，按听感调整；技术分段停顿更短。首版保留自然语速和清晰人声，避免过度淡化吞字。

标准库拼接 PCM 并保留无损 WAV。FFmpeg 用于额外 MP3 编码，缺失时明确 WAV 交付，不自动安装依赖或伪造 MP3。编码失败不能报告成功。

依据：[VoxCPM 官方说明](https://github.com/OpenBMB/VoxCPM)，以及本机启动器与运行时接口。

## 维护验证

修改脚本后运行 `python3 -B -m unittest discover -s SKILL_DIR/tests -v`。测试使用合成 PCM 和独立临时目录，覆盖脚本导出、审核绑定、文件保护、片段恢复与定稿；不会调用真实模型，也不能证明医学正确性或真实语音听感。
