# career-application-kit

一个**本地优先、可整目录迁移**的求职工作区，同时是一个 agent skill。

把求职过程拆成四件可核查的事：**事实档案 → 岗位核查 → 一页简历定制 → 投递台账**。
数据全部存在你自己的磁盘上，不含账号密码，脚本不会向任何网站提交。

> A local-first job application workspace that also works as an agent skill.
> Verified facts, JD screening, one-page LaTeX resumes, and a de-duplicated application ledger.
> No cloud, no credentials, no auto-submitting bot.

---

## 它解决什么问题

求职最难的不是"写简历"，而是**不把自己搞乱**：

- 投过哪家、投的哪个编号、用的哪版简历？——靠记忆，迟早重复投或投错版本。
- 简历越改越"漂亮"，但有些数字其实没出处。——面试被追问就崩。
- 每个岗位都要改抬头、改重点、改文件名。——手工复制粘贴最容易漏改公司名。
- 换电脑就重来一遍。——聊天记录里的资料、截图、模板全散掉。

这个工具用四个文件把这些问题钉死：

| 文件 | 作用 |
|---|---|
| `data/profile.md` | 唯一事实来源，每条事实标「本人确认 / 旧稿 / 待确认」 |
| `data/preferences.json` | 筛选边界（城市、薪资下限、排除公司）与排版偏好 |
| `data/ledger.jsonl` | 追加式投递台账，一岗位一 key，按最新状态统计 |
| `output/jobs/<slug>/` | 每个岗位的 JD 快照、简历源码、PDF、预览、凭证 |

---

## 特点

- **纯标准库脚本**：`scripts/kit.py` 只用 Python 内置模块，不需要 pip、不需要 API Key、不需要联网。
- **哈希台账**：每份投递简历记录 SHA256，`validate` 能发现"PDF 被换过但台账没更新"。
- **防重复投递**：同一岗位 key 已成功时，脚本拒绝再记新申请；跨渠道换平台也不重复计数。
- **防示例内容误投**：模板里的单位/项目都是示例，带 `DEMO-CONTENT` 标记，未替换时 `build` 直接拒绝。
- **防占位符漏填**：`{{NAME}}` 这类占位符没填完，`validate` / `build` 都会报错，不会把 "NAME" 印在简历上。
- **一页强约束**：编译后自动查页数、查 Overfull 与缺字警告，生成每页 PNG 供目检。
- **可整目录迁移**：相对路径 + manifest 清单，复制到新机器 `validate` 就能验证完整性。

---

## 快速开始

```bash
git clone <this-repo> career-application-kit
cd career-application-kit

# 1. 检查环境
python scripts/kit.py doctor

# 2. 初始化你的档案（只需一次）
python scripts/kit.py init --name "张三" --phone "13800000000" \
  --email "zhangsan@example.com" --city "上海" \
  --role "机械结构设计" --degree "2027届硕士"

# 3. 补全 data/profile.md 里的真实经历与「待确认」项
python scripts/kit.py validate

# 4. 为某个岗位生成简历工作目录
python scripts/kit.py prepare --template zh-mechanical --job acme-structural \
  --company "ACME" --title "结构设计工程师"

# 5. 改内容 → 删掉文件头的 DEMO-CONTENT 注释 → 编译
python scripts/kit.py build --job acme-structural

# 6. 投递成功后记账
python scripts/kit.py record --file job-record.json
python scripts/kit.py status
```

Windows 下若 `python` 不在 PATH，用 `py -3` 代替。

---

## 环境要求

| 用途 | 依赖 | 说明 |
|---|---|---|
| 所有脚本 | Python 3.10+ | 只用标准库 |
| 生成 PDF | XeLaTeX（TeX Live / MacTeX） | 需要 `ctex`、`fontspec`、`geometry`、`graphicx`、`xcolor`、`enumitem`、`hyperref`、`titlesec`、`fancyhdr`、`xifthen` |
| 页数与预览 | Poppler：`pdfinfo`、`pdftotext`、`pdftoppm` | 需在 PATH 中 |
| 中文字体 | 优先微软雅黑，缺失时回退 Fandol 宋体 | 不捆绑商业字体 |
| 英文字体 | 优先 Arial，缺失时回退 TeX Gyre Heros | 换字体会改变排版，需重新目检 |
| 投递 | agent 的浏览器/连接器，或你本人 | 脚本本身不投递 |

`doctor` 会把缺失的依赖直接列出来，不会自动联网安装。

---

## 命令

| 命令 | 作用 |
|---|---|
| `init` | 从 `assets/scaffold/` 生成 `data/`，替换个人信息占位符 |
| `doctor` | 检查 Python 与 LaTeX/Poppler |
| `validate` | 校验清单哈希、台账引用、未填占位符、禁止文件 |
| `status` | 去重后的投递统计（成功岗位数、事件数） |
| `prepare` | 复制模板到 `output/jobs/<slug>`，填充抬头占位符 |
| `build` | XeLaTeX 两遍、查页数/溢出/缺字、生成预览 PNG |
| `record` | 追加一条投递事件，成功时校验凭证与简历哈希 |
| `seal` | 重建 `manifest.json` 哈希清单 |
| `pack` | 校验后打包为 zip（必须输出到目录外） |

---

## 模板

| 模板 | 适用 |
|---|---|
| `zh-mechanical` | 机械 / 结构 / 机器人方向，中文一页带照片 |
| `zh-cadcae` | CAD / 几何内核 / C++ 研发方向 |
| `zh-cae-analysis` | CAE 仿真分析方向 |
| `en-classic` | 英文简历 + 求职信（一页，含页脚公司/岗位标识） |

模板是**排版骨架**，内容全是示例。真实内容只从 `data/profile.md` 里取。

---

## 隐私

- `data/`、`output/`、`manifest.json` 已在 `.gitignore` 中，你填的真实资料不会被误提交。
- 仓库本身不含任何真实个人信息：模板里是"示例大学""某装备制造企业"，占位图是灰色剪影。
- 台账不存密码、Cookie、会话令牌；`record` 会拒绝带 `token=` / `sid=` 的 URL。
- 截图凭证可能含个人信息，分享前请另做脱敏副本。

---

## 作为 agent skill 使用

**WorkBuddy / Claude Code / Codex 等支持 skill 的环境**：把整个目录放到 skill 目录下（例如 `~/.workbuddy-ai/skills/career-application-kit` 或 `~/.codex/skills/career-application-kit`），重新加载会话后即可触发。

**没有 skill 机制的环境**：直接把 `SKILL.md` 作为工作说明交给 agent 读，效果一样。

给 agent 的开场白可以直接用：

> 读 `SKILL.md`，先 `doctor` + `validate`，然后告诉我档案里还缺哪些待确认信息。按 `data/preferences.json` 的城市与薪资边界筛岗位，先确认这轮是只搜岗、只做材料还是授权投递；不要重复投台账里已成功的岗位。

---

## 设计取舍

- **为什么不直接存"最新简历.pdf"？** 因为你需要知道**哪一版**投给了**哪个岗位**。台账按 key + 哈希记录，才能回答这个问题。
- **为什么强制 `DEMO-CONTENT` 标记？** 示例内容和真实内容长得太像，靠自觉迟早出事。让脚本挡住比让人记住更可靠。
- **为什么不做自动投递？** 自动投递会绕过条款同意、身份核对与验证码，风险和误投代价远高于省下的几分钟。工具负责把材料做到可投，提交这一步留给人。
- **为什么用 LaTeX 而不是 Word？** 版式可控、可 diff、可批量生成，且不会因为字体缺失在你不知道的时候悄悄改版。

---

## 贡献

欢迎提 issue 或 PR：新增模板（尤其非机械类专业）、修排版问题、补测试。
`python scripts/test_kit.py` 是全部测试，不需要额外依赖。

## License

MIT，见 [LICENSE](LICENSE)。
