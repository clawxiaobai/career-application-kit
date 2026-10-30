# 数据格式

所有路径相对工作区根目录，只有 `source` 字段允许出现公开网址。

| 路径 | 作用 |
|---|---|
| `data/profile.md` | 本人事实总档，来源与待确认项都保留 |
| `data/preferences.json` | 筛选边界与排版偏好；**不是提交授权** |
| `data/current-state.md` | 最新结果、阻碍、下一步 |
| `data/ledger.jsonl` | 追加式投递事件，每行一个 JSON |
| `data/history/attachments/` | 按内容哈希去重的已投附件（审计用） |
| `data/history/proofs/` | 按哈希去重的成功凭证截图 |
| `assets/templates/` | 可复制的简历基础版 |
| `output/jobs/<slug>/` | 每个岗位的定制材料 |
| `manifest.json` | 相对路径 + 字节数 + SHA256 清单，用于检测拷贝损坏 |

## 台账字段

```json
{
  "key": "official-portal:example-co:REQ123",
  "at": "2026-03-01T03:00:00Z",
  "company": "公司真实名称",
  "title": "岗位名称",
  "location": "实际工作城市",
  "salary": "面议，待核实",
  "source": "https://example.com/careers/REQ123",
  "channel": "official_careers_portal",
  "actionType": "new_application",
  "status": "success",
  "resumePath": "output/jobs/example-co-role/resume.pdf",
  "proof": "output/jobs/example-co-role/submitted.png"
}
```

必填：`key`、`at`、`company`、`title`、`location`、`salary`、`source`、`channel`、`actionType`、`status`。

- `actionType`：`new_application` / `supplement` / `status_update`
- `status`：`success` / `pending` / `uncertain` / `failed` / `delivery_failed`
- `status=success` 时必须有 `proof` 与 `resumePath`，脚本会自动记录 `resumeHash`
- 同一 `key` 已有 success 时，再记 `new_application` 会被拒绝；补发用 `supplement`
- 退信：同 key 追加 `delivery_failed` 事件，不删除原记录

统计口径：每个 `key` 只看**最新**事件；`supplement` 不计新申请；`failed` / `uncertain` / `pending` 不计成功。

## 常用命令

```bash
python scripts/kit.py record --file job-record.json
python scripts/kit.py status
python scripts/kit.py seal
python scripts/kit.py pack --out ../backup.zip
```

## 迁移与并发

- 整目录复制后先 `validate`，再 `doctor`。
- manifest 不一致时不要直接 `seal` 抹平：先查是不是本人改过、丢文件或损坏。
- 两台机器同时改会分叉，按 `key` 与时间人工合并，不要用「哪边复制得晚」覆盖。
- 脚本只支持单写者，不联网同步，不读取浏览器数据库或令牌。
