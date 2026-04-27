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

## 4. Inference Results

Generated spreadsheet files are saved inside the dataset:

```text
data/<dataset>/outputs/single_<MODEL>/
data/<dataset>/outputs/multi_<setting>_<MODEL>/
```

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

## 7. Evaluation Results

Evaluation writes JSON files to the repository-level `outputs/` directory:

```text
outputs/eval_<setting>_<MODEL>.json
```

Each record includes the task id, instruction type, per-test-case results, `soft_restriction`, and `hard_restriction`.
