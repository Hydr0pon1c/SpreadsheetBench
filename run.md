# Running Inference and Evaluation

This file lists the commands needed to run SpreadsheetBench inference and evaluation, plus where each result is written.

## 1. Prepare Data

Extract the target dataset archive under `data/` before running. The scripts expect this layout:

```text
data/<dataset>/dataset.json
data/<dataset>/<spreadsheet_path>/...
```

Example dataset names used by the scripts include `sample_data_200`, `spreadsheetbench_912_v0.1`, and `spreadsheetbench_verified_400`.

## 2. Start Code Execution Service

Inference expects a local execution API at `http://localhost:8081/execute`.

```bash
cd code_exec_docker
bash start_jupyter_server.sh 8081
```

If using Docker, first update `code_exec_docker/config.json`; `volumes_path` must be an absolute path to the dataset directory mounted as `/mnt/data`.

## 3. Run Inference

Run commands from `inference/`. Replace `MODEL`, `API_KEY`, `BASE_URL`, and `DATASET` as needed.

### Single-turn inference

```bash
cd inference
python3 inference_single.py \
  --model MODEL \
  --api_key API_KEY \
  --base_url BASE_URL \
  --dataset DATASET \
  --code_exec_url http://localhost:8081/execute
```

### Multi-turn inference

Choose one setting: `row_exec`, `react_exec`, or `row_react_exec`.

```bash
cd inference
python3 inference_multiple.py \
  --setting react_exec \
  --model MODEL \
  --api_key API_KEY \
  --base_url BASE_URL \
  --dataset DATASET \
  --code_exec_url http://localhost:8081/execute \
  --skip_existing
```

For Trace2Skill runs, use `--run_name` to avoid overwriting baseline outputs, `--split_file` to restrict the task ids, and `--skill_path` to prepend a `SKILL.md`:

```bash
cd inference
python3 inference_multiple.py \
  --setting row_react_exec \
  --model qwen3.5-35b-a3b \
  --api_key API_KEY \
  --base_url BASE_URL \
  --dataset spreadsheetbench_verified_400 \
  --split_file ../data/splits/verified_evolve_200.json \
  --skill_path ../skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md \
  --run_name qwen3.5-35b-a3b_parametric_evolve \
  --code_exec_url http://localhost:8081/execute \
  --skip_existing
```

## 4. Inference Results

Generated spreadsheet files are saved inside the dataset:

```text
data/<dataset>/outputs/single_<MODEL>/
data/<dataset>/outputs/multi_<setting>_<MODEL>/
```

When `--run_name RUN` is provided, `RUN` replaces `MODEL` in the output directory and conversation filename.

Conversation logs are saved under `inference/outputs/`:

```text
inference/outputs/conv_single_<MODEL>.jsonl
inference/outputs/conv_multi_<setting>_<MODEL>.jsonl
```

Failed single-turn records may also be logged under `inference/log/`.

## 5. Recalculate Spreadsheets When Needed

If generated workbooks contain formulas, recalculate them before evaluation so cached values are available.

```bash
cd evaluation
python3 open_spreadsheet.py \
  --dir_path ../data/DATASET/outputs \
  --backend libreoffice
```

On Windows with Excel automation available, use `--backend win32com`.

## 6. Run Evaluation

Run from `evaluation/`. The `--setting` value must match the output directory prefix:

- `single` for `data/<dataset>/outputs/single_<MODEL>/`
- `multi_react_exec` for `data/<dataset>/outputs/multi_react_exec_<MODEL>/`
- `multi_row_exec` for `data/<dataset>/outputs/multi_row_exec_<MODEL>/`
- `multi_row_react_exec` for `data/<dataset>/outputs/multi_row_react_exec_<MODEL>/`

```bash
cd evaluation
python3 evaluation.py \
  --setting single \
  --model MODEL \
  --dataset DATASET
```

Example for multi-turn `react_exec`:

```bash
cd evaluation
python3 evaluation.py \
  --setting multi_react_exec \
  --model MODEL \
  --dataset DATASET
```

Trace2Skill evaluation should use the same `--run_name` and split file used for inference:

```bash
cd evaluation
python3 evaluation.py \
  --setting multi_row_react_exec \
  --model qwen3.5-35b-a3b \
  --dataset spreadsheetbench_verified_400 \
  --split_file ../data/splits/verified_evolve_200.json \
  --run_name qwen3.5-35b-a3b_parametric_evolve
```

## 7. Evaluation Results

Evaluation writes JSON files to the repository-level `outputs/` directory:

```text
outputs/eval_<setting>_<MODEL>.json
```

Each record includes the task id, instruction type, per-test-case results, `soft_restriction`, and `hard_restriction`.

## 8. Trace2Skill Reproduction Utilities

Prepare the fixed 200/200 split:

```bash
python3 trace2skill/prepare_splits.py
```

Generate the parametric `skill0`:

```bash
python3 trace2skill/generate_skill0.py \
  --api_key API_KEY \
  --model qwen3.5-35b-a3b
```

After inference and evaluation finish, label trajectories and propose/merge patches:

```bash
python3 trace2skill/prepare_trajectories.py \
  --run_id qwen35_parametric_creation_v1 \
  --split_file data/splits/verified_evolve_200.json \
  --conv_jsonl inference/outputs/conv_multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve.jsonl \
  --eval_json outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve.json \
  --output_dir data/spreadsheetbench_verified_400/outputs/multi_row_react_exec_qwen3.5-35b-a3b_parametric_evolve

python3 trace2skill/propose_patches.py \
  --run_id qwen35_parametric_creation_v1 \
  --skill_path skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md \
  --api_key API_KEY

python3 trace2skill/merge_patches.py \
  --run_id qwen35_parametric_creation_v1 \
  --api_key API_KEY

python3 trace2skill/apply_skill_patch.py \
  --run_id qwen35_parametric_creation_v1 \
  --skill0 skills/spreadsheet-parametric-qwen3.5-35b-a3b/SKILL.md

python3 trace2skill/summarize_results.py \
  --run_id qwen35_parametric_creation_v1 \
  --split_file data/splits/verified_test_200.json \
  --eval_no_skill outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b.json \
  --eval_skill0 outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_parametric_test.json \
  --eval_skill_star outputs/eval_multi_row_react_exec_qwen3.5-35b-a3b_skill_star_test.json
```
