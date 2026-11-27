# GuidePatch · 教程复活师

v1.1.0

把旧教程分解为原步骤、意图和预期状态，对照当前界面，只给变化的步骤写补丁。宿主负责理解截图、核对来源和与用户对话；Python 标准库负责生成、校验、导出和按版本检索记录。

## 试一个可复现的案例

克隆或解压仓库，进入含有 SKILL.md 的目录。Python 3.9 及以上可运行。

```shell
python -B scripts/build_patch.py build examples/vscode-settings.json output/settings.json
python -B scripts/build_patch.py next output/settings.json
python -B scripts/export_markdown.py output/settings.json output/settings.md
python -B -m unittest discover -s tests -v
```

第一条命令应输出两个决策，按次序为 keep、replace。第二条命令返回 preview，说明这是文档和本机截图构成的只读参考案例。打开 Markdown 可看到原步骤、替换动作、预期和来源。完整输入结构见 [输入契约](schemas/tutorial.schema.json)。

## 在技能宿主里使用

将仓库目录命名为 guidepatch，再放到宿主支持的项目级 skills 目录。也可以将目录压缩成 ZIP 后导入。码道支持从技能设置导入 ZIP。打开对话后可直接使用下面的请求。

> 用 guidepatch 帮我修一条旧教程。旧步骤让我按 Ctrl+, 查看用户设置 JSON。我在当前版本只看到图形设置。我的目标是查看用户配置文件。这是软件版本和当前界面，请保留有效步骤，并给我下一步以及应该看到的结果。

对话中收集适用环境和最小的已脱敏材料。用户授权保存在本地时，以 live 模式建立独立案例，先 build，再按 next 返回的位置记录反馈。

```shell
python -B scripts/build_patch.py verify output/patch.json feedback.json output/revision-1.json
python -B scripts/build_patch.py next output/revision-1.json
python -B scripts/export_markdown.py output/revision-1.json output/report.md
```

每次反馈包含 revision、environment、step_id、action_index、actor、outcome、expected_met、note、date，详见 [反馈契约](schemas/feedback.schema.json)。先确认具体动作和预期，再给最终目标单独写一条反馈，使用 __goal__ 和索引 0。失败会终止当前修订，需结合新增证据重建。复用查询仅返回同一目标与完整环境的用户已核验记录。

## 夹具与证据

examples/cases.json 中有 8 个虚构夹具和 2 个文档案例。运行 `python -B scripts/run_examples.py --out output` 可复现原案例集，模拟反馈终态是 simulated。examples/vscode-settings.json 另附本版的本机界面对照。

证据等级与软件真伪、执行者身份由宿主和使用者核对。引擎依据输入执行状态规则。版本哈希绑定内容，默认在本地读写。公开精简稿可通过 export_markdown.py 的 --public 选项生成；操作文字和原教程摘要仍需人工复核。
