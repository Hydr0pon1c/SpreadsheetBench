# Trace2Skill SpreadsheetBench Reproduction Plan

本文档记录本仓库中复现 `trace2skill.pdf` 的 SpreadsheetBench 部分的计划。当前目标已经收紧为：只关注 `spreadsheetbench_verified_400`，按论文设定拆成 200 条 evolve set 和 200 条 test set，复现论文里的 **Parametric + Creation** 路线：先让 LLM 从参数知识生成一个弱 `skill0`，再用轨迹证据演化出真正有用的 spreadsheet skill。

## 1. 当前结论与边界

不做或暂缓：

- 不做 WikiTQ/OOD、跨模型迁移和三随机种子平均。
- 不复现 Human-Written/Deepening 主线；Anthropic xlsx skill 只作为思想参考。
- 不重复跑 No Skill baseline；已有结果作为对照。

必须做：

- 创建 `skill0`：由 `qwen3.5-35b-a3b` 基于 spreadsheet 操作常识生成，不能看 evolve/test 轨迹。
- 用 `skill0` 在 evolve set 上生成轨迹，然后从失败/成功轨迹中产生 patch。
- 分层合并 patch，得到 `skill*`。
- 在 held-out test set 上比较 `No Skill`、`skill0`、`skill*`。

## 2. 已有 No Skill 结果

已有 no-skill artifacts：

- Evaluation: `outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b.json`
- Output files: `data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b/`
- Trajectories: `inference/outputs/conv_multi_row_react_exec_qwen3.5-35b-a3b.jsonl`

快速检查结果：

- eval 文件有 400 条唯一样本，hard pass 为 104/400，即 26.0%。
- 如果按当前 `dataset.json` 顺序前 200/后 200 切分，前 200 hard pass 为 55/200，后 200 hard pass 为 49/200。
- conv jsonl 有 436 行、400 个唯一 id，说明它是追加式日志；有 35 个重复 id，4 条 `status=failed`，错误均为 API 524。
- 轨迹字段为 `id`、`instruction_type`、`test_cases`、`conversation`、`solution`、`status`。`conversation` 是列表，通常从完整 prompt 开始，后续交替保存模型回复和代码执行结果。

这些 no-skill 轨迹可用于理解数据形态、调试 analyst prompt、做低成本 sanity check。但严格复现 Parametric + Creation 时，Stage 1 轨迹应该来自注入 `skill0` 后的 evolve set 推理，而不是 no-skill 轨迹。

## 3. 数据切分

数据源固定为：

```text
data/spreadsheetbench_verified_400/dataset.json
```

建议生成显式 split 文件：

```text
data/splits/verified_evolve_200.json
data/splits/verified_test_200.json
```

默认方案：按当前 `dataset.json` 顺序前 200 条作为 evolve set，后 200 条作为 test set。这样与现有 no-skill eval 可直接对齐。如果后续有论文官方 split 或你指定的 seed split，应以外部 split 文件为准，并记录在 run config 中。

## 4. 实验矩阵

本阶段只跑单模型 `qwen3.5-35b-a3b`：

| 条件 | evolve 阶段 | test 阶段 | 用途 |
| --- | --- | --- | --- |
| No Skill | 已完成 | 已完成 | baseline |
| Parametric `skill0` | 不使用轨迹，只由 LLM 生成 | 注入 `skill0` 跑 test | Creation baseline |
| Creation +Error | 用 `skill0` 跑 evolve，分析失败轨迹 | 注入 `skill*` 跑 test | 优先复现 |
| Creation +Combined | 用 `skill0` 跑 evolve，分析失败和成功轨迹 | 注入 `skill*` 跑 test | 第二优先级 |

论文里 +Error 更稳，+Success 方差较大。因此第一轮建议先实现 Creation +Error，确认闭环有效后再加入 success analyst。

## 5. Skill0 生成

`skill0` 应模拟论文的 Parametric baseline：只依赖模型参数知识，不使用任何 SpreadsheetBench 轨迹、golden、eval 结果或论文总结出的高频 SOP。建议保存为：

```text
skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md
```

生成 prompt 应要求：

- 面向 spreadsheet manipulation agent。
- 输出一个简洁 `SKILL.md`，包含任务理解、读表、写表、公式、格式保留、验证等常识。
- 不引用具体 benchmark、task id、文件路径、answer_position 示例。
- 不写过度具体的经验规则，例如“openpyxl 写公式后必须 LibreOffice 重算”，除非模型自己从常识中提出。

这样才能把 `skill*` 的提升归因到轨迹证据，而不是人工把论文结论提前写入 `skill0`。

## 6. Stage 1: 用 Skill0 生成 Evolve 轨迹

需要在 inference prompt 顶部注入 `skill0`。论文做法是把 `SKILL.md` 预加载到上下文；本仓库可先用最简单方式实现：在 `PROMPT_*` 模板前 prepend skill text。

正式轨迹生成只跑 evolve set：

```bash
cd inference
python3 inference_multiple.py \
  --setting row_react_exec \
  --model qwen3.5-35b-a3b \
  --api_key API_KEY \
  --base_url BASE_URL \
  --dataset spreadsheetbench_verified_400 \
  --code_exec_url http://localhost:8081/execute \
  --max_turn_num 100 \
  --skip_existing
```

实现时需要增加 split/filter 参数或生成临时 dataset，使脚本只跑 evolve 200。输出目录建议不要覆盖 no-skill：

```text
data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_parametric/
inference/outputs/conv_multi_row_react_exec_qwen3.5-35b-a3b_parametric.jsonl
```

轨迹生成后运行 evaluation，并把 eval 结果回填到 trajectory records：

```bash
cd evaluation
python3 open_spreadsheet.py \
  --dir_path ../data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_parametric \
  --backend libreoffice

python3 evaluation.py \
  --setting multi_row_react_exec \
  --model qwen3.5-35b-a3b_parametric \
  --dataset spreadsheetbench_verified_400
```

注意：当前 `evaluation.py` 默认评估整个 dataset。正式复现需要让它支持 split，或在运行前构造只含 evolve/test 的 dataset view。

## 7. Trajectory 清洗与标注

由于现有 conv 文件会追加重复记录，后续所有 stage 都必须先标准化轨迹：

1. 读取 `conv_*.jsonl`。
2. 按 `id` 去重，优先选择最后一条 `status=ok` 且 output 文件存在的记录。
3. 与 eval json 按 `id` join。
4. 添加 `hard_restriction`、`soft_restriction`、`test_case_results`。
5. 拆成 `T-` 和 `T+`：`hard_restriction == 0` 为失败，`== 1` 为成功。

每条 analyst 输入应包含：

- `skill0` 的 `SKILL.md`。
- dataset metadata：instruction、instruction_type、answer_position、spreadsheet_path。
- test case：input/output/golden 文件名。
- conversation：prompt、模型回复、代码执行结果。
- solution：最终代码。
- eval：pass/fail 和失败范围。

## 8. Stage 2: Patch Proposal

第一轮建议先实现 error analyst。每条失败轨迹独立产生 patch，输出结构化 JSON：

```json
{
  "trajectory_id": "17-35",
  "analyst_type": "error",
  "failure_surface": "...",
  "root_cause": "...",
  "evidence": ["conversation step ...", "output/golden diff ..."],
  "memory_items": [
    {"title": "...", "lesson": "...", "generalization": "..."}
  ],
  "edits": [
    {"file": "SKILL.md", "op": "insert_after", "target": "...", "content": "..."}
  ]
}
```

降级版 LLM-only analyst 可以先只看轨迹、solution 和 eval 失败信号。更接近论文的 agentic analyst 应能：

- 读取 input/output/golden xlsx。
- 定位具体单元格差异。
- 检查 agent 代码为什么产生差异。
- 尝试最小修复并重新调用 evaluation 验证。
- 如果无法验证因果原因，丢弃该 patch。

Success analyst 放到第二阶段，输出 successful behavior patterns。合并时需要更严格：只有多个成功轨迹独立支持的策略才进入主 `SKILL.md`。

## 9. Stage 3: Hierarchical Merge

论文 merge batch size 为 32；本复现也采用 32。流程：

1. 固定 seed 打乱 patch 列表。
2. 每 32 个 patch 合并为 1 个 consolidated patch。
3. 多层重复，直到只剩一个最终 patch。
4. 应用到 `skill0`，生成 `skill*`。

合并 prompt 必须强调：

- 高频错误模式优先。
- 单例、过拟合、只对某个 task id 有效的经验丢弃或放入 `references/`。
- 主 `SKILL.md` 保持短、可执行、通用。
- 不允许写入具体答案、具体 golden 值、具体 benchmark 样本 id。

程序化检查：

- patch 只能修改 `SKILL.md` 或创建 `references/*.md`。
- `references/*.md` 的创建和链接必须成对出现。
- 不允许多个 edit 修改同一 target 段落。
- JSON patch 必须能被 parser 读取；Markdown 至少通过基本格式检查。

## 10. Test 阶段

最终需要在 held-out test 200 上分别评估：

- No Skill：使用已有 baseline 中对应 test split 的结果。
- `skill0`：注入 parametric skill 后跑 test split。
- `skill*`：注入 evolved skill 后跑 test split。

输出目录建议：

```text
trace2skill_runs/<run_id>/
  config.json
  split/
  skill0/SKILL.md
  evolve/
    conv_parametric.jsonl
    eval_parametric.json
    labeled_trajectories.jsonl
  patches/error/*.json
  patches/success/*.json
  merges/level_*/batch_*.json
  skill_star/SKILL.md
  test/
    eval_no_skill.json
    eval_skill0.json
    eval_skill_star.json
  report.md
```

报告中至少给出：

- hard pass rate、soft average。
- 相对 No Skill 和 `skill0` 的 delta。
- evolve set 中失败/成功轨迹数量、生成 patch 数量、保留 patch 数量。
- `skill*` 的主要 SOP 分类和每类支持 patch 数。
- 与论文差异：是否 agentic error analyst、是否 +Combined、是否完整 200 evolve。

## 11. Sanity Check

论文中 SpreadsheetBench 常见高频 SOP 可用于检查 evolved skill 是否合理，但不能提前写进 `skill0`：

- 写公式后重算并用 `data_only=True` 回读。
- 写回 xlsx 优先用 `openpyxl`，避免 `pandas.to_excel()` 破坏 workbook 结构。
- 修改后重新打开 output，验证 `answer_position`。
- 删除行列时倒序操作，并严格限制范围。
- 写入前确认 sheet、range、header、answer_position。
- 日期和数值保持原生类型，避免字符串化。

如果 `skill*` 完全没有这些类别，或大量出现 task-specific 规则，说明 patch proposal/merge 没有复现 Trace2Skill 的核心归纳效果。

## 12. 推荐实施顺序

1. 生成并冻结 split 文件。
2. 生成 `skill0` 并保存。
3. 加入 skill 注入和 split 运行能力。
4. 用 `skill0` 跑 evolve 200，生成正式 Creation 轨迹。
5. 清洗 conv/eval，产出 labeled trajectories。
6. 实现 error analyst，先抽样 10 条人工检查。
7. 实现 hierarchical merge，生成 `skill*`。
8. 用 `skill0` 和 `skill*` 分别跑 test 200。
9. 汇总与已有 no-skill baseline 的 delta。

第一阶段成功标准：`skill*` 在 held-out test 200 上相对 `skill0` 有稳定提升，并且提升来自通用 spreadsheet SOP，而不是泄漏 test 信息或记忆 evolve 样本。
