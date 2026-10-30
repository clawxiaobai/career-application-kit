---
name: career-application-kit
description: 本地优先的求职工作区：维护个人事实档案、核查岗位 JD、用 XeLaTeX 定制并检查一页中英文简历、按去重台账记录投递并保存凭证。当用户提到求职、找工作、投递、简历、岗位筛选、JD 分析、投递记录、offer 跟进时使用。数据全部保存在本地，不含账号密码，不会自动投递。
---

# 求职工作区（career-application-kit）

一个可以整目录复制的求职工作区：事实档案 + 岗位核查 + 一页简历定制 + 投递台账。
纯本地运行，脚本只处理文件，**不会向任何网站提交**。投递动作由 agent 配合浏览器/连接器完成，或由本人手动完成。

## 目录

```
SKILL.md                 本文件：工作流程与边界
README.md                安装、环境、命令速查
data/profile.md          个人事实档案（唯一事实来源）
data/preferences.json    筛选边界与排版偏好（不是授权）
data/current-state.md    进度、停点、下一步
data/ledger.jsonl        投递台账（追加式）
data/history/            附件与凭证（按哈希去重）
assets/templates/        四套 LaTeX 模板
assets/scaffold/         首次初始化的空白档案
output/jobs/<slug>/      每个岗位的定制材料
scripts/kit.py           本地工具（标准库，无需 pip）
references/              细则：workflow / resume-rules / channels / data-format
```

## 首次使用

1. 确认环境：`python scripts/kit.py doctor`（需要 Python 3.10+；生成 PDF 另需 XeLaTeX 与 Poppler）。
2. 初始化档案（只需一次）：

```bash
python scripts/kit.py init --name "张三" --phone "13800000000" \
  --email "zhangsan@example.com" --city "上海" \
  --role "机械结构设计" --degree "2027届硕士"
```

   之后 `data/` 下会生成 profile / preferences / current-state / verification，`{{NAME}}` 一类占位符会被替换。
   也可以在对话里逐条问本人后手工填写 `data/profile.md`。
3. 读三份数据：`data/preferences.json`（筛选与排版偏好）、`data/current-state.md`（停点）、`data/profile.md`（事实与待确认项）。
4. `python scripts/kit.py validate` 确认档案没有未填占位符。
5. 问清本轮范围：只整理资料 / 只搜岗 / 只做材料 / 授权投递。**授权只对当次任务有效**。

## 工作流程

### 一、事实先行

- 新事实先写进 `data/profile.md`，标注来源（本人确认 / 旧稿 / 待确认）与日期。
- 旧简历、JD 措辞、AI 润色稿都不是新事实。
- 未知字段（到岗时间、住址、薪资期望、工作资格）先问，不猜。

### 二、岗位核查

- 打开具体 JD 页面，保存正文快照到 `output/jobs/<slug>/jd.md`，记录核查时间。
- 区分「要求」与「加分项」，区分「实际工作城市」与「公司总部」。
- 薪资按公开月薪下限判断；面议标「待核实」。
- 无正文、已失效、只有搜索摘要的岗位不投。
- 细则见 `references/workflow.md`。

### 三、定制简历

```bash
python scripts/kit.py prepare --template zh-mechanical --job example-co-structural \
  --company "示例公司" --title "结构设计工程师"
```

- `prepare` 会把 `{{NAME}}` `{{PHONE}}` `{{EMAIL}}` `{{ROLE}}` `{{CITY}}` `{{DEGREE}}` 等占位符用 preferences 里的值填好，`{{COMPANY}}` / `{{TITLE}}` 由参数填入。
- 然后编辑副本：只取与岗位相关的事实，调整顺序与篇幅，**不改事实**。
- 模板里的单位、学校、项目都是示例（文件头有 `DEMO-CONTENT` 标记）。换成真实内容后删掉那行注释，否则 `build` 会拒绝。
- 细则见 `references/resume-rules.md`。

### 四、编译与验收

```bash
python scripts/kit.py build --job example-co-structural
```

脚本做的是：XeLaTeX 两遍 → `pdfinfo` 查页数 → `pdftotext` 提取文本 → `pdftoppm` 生成每页 PNG → 检查 Overfull 与缺字警告。

**脚本通过不等于可以投。** 还要逐页目检：照片比例、日期对齐、长英文标题、字体回退、底部是否过空或过挤。

### 五、提交与留证

- 用当前环境真实具备的浏览器/连接器；没有就只准备材料与操作清单，让本人提交，**不能假装已投**。
- 登录、条款同意、最终提交是三个不同状态，条款需当次确认。
- 只有明确成功页面/申请记录/已发送邮件才算成功；上传成功 ≠ 申请成功。
- 截图存 `data/history/proofs/` 或 job 目录，台账只记相对路径。
- 细则见 `references/channels.md`。

### 六、记账

```bash
python scripts/kit.py record --file job-record.json
python scripts/kit.py status
```

- 同一 `key` 已有 success 时不允许再记 `new_application`，补发用 `supplement`。
- 退信记 `delivery_failed`，不删原记录。
- 格式见 `references/data-format.md`。

## 硬边界

- 不编造经历、指标、奖项、薪资承诺、到岗日期、工作资格。
- 不把「参与」写成「主导」，不把「用过」写成「精通」。
- 不保存密码、Cookie、会话令牌、验证码；不代持账号。
- 不继承上一次任务的授权、条款同意或登录状态。
- 未经本人同意不修改平台全局在线简历，不勾选默认发送。
- 个人资料含隐私，不要上传到公共仓库或第三方服务。

## 打包与迁移

```bash
python scripts/kit.py seal                    # 重建哈希清单
python scripts/kit.py pack --out ../backup.zip
```

整目录复制到新机器后：`validate` → `doctor` → 重新登录各渠道（登录状态不迁移）。
