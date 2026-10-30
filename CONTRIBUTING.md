# 贡献指南

## 可以提什么

- **新模板**：非机械类专业（电子、化工、土木、产品、数据等）的中英文一页模板，尤其是中文求职市场常用的版式。
- **排版修复**：Overfull、缺字、日期错位、字体回退后版式崩坏。
- **脚本改进**：`kit.py` 的健壮性、校验规则、Windows/macOS 兼容性。
- **文档**：把含糊的规则写清楚，或补一个真实使用流程的例子。

## 提交前自检

```bash
cd scripts && python test_kit.py        # 必须全绿
cd .. && python scripts/kit.py validate # 需要先 init 过，或用 CI 的方式
```

模板改动还要：

```bash
# 在临时副本里编译，确认仍是一页、无 Overfull / 缺字
python scripts/kit.py prepare --template <name> --job check-<name>
python scripts/kit.py build --job check-<name> --allow-demo
```

## 隐私红线

提交前请确认 PR 里**没有**：

- 真实姓名、手机号、邮箱、住址、身份证、学校与公司的真实组合
- 真实投递记录、截图凭证、聊天记录
- 任何 token、Cookie、密码、会话 URL

模板里的单位/学校/项目请保持「示例大学」「某装备制造企业」这类明显示例，并保留文件头的 `DEMO-CONTENT` 注释——`build` 依赖它拦截误投。

## 代码风格

- `kit.py` 只用 Python 标准库，不引入第三方依赖。
- 所有路径必须相对工作区根目录，不接受绝对路径与反斜杠。
- 新增校验规则时，同步在 `scripts/test_kit.py` 补一个测试。

## 提交信息

用一句话说明改了什么，例如：

- `feat(template): add zh-electronics one-page template`
- `fix(kit): reject ledger rows with absolute resume paths`
- `docs: clarify salary screening rule`
