# Repository Guidelines

## Project Structure & Module Organization

- `inference/`: LLM prompting, API calls, code execution clients, and single/multi-turn inference entry points.
- `inference/scripts/`: shell wrappers for common inference modes.
- `evaluation/`: workbook comparison, scoring, spreadsheet recalculation helpers, and evaluation scripts.
- `code_exec_docker/`: Docker/API/Jupyter execution environment used by inference.
- `data/`: archived benchmark datasets and extracted local datasets.
- `outputs/`: generated conversations, predictions, and evaluation artifacts.
- `images/`: static repository assets.

## Build, Test, and Development Commands

- `cd code_exec_docker && docker build -t xingyaoww/codeact-execute-api -f Dockerfile.api .`: build the execution API image.
- `cd code_exec_docker && docker build -t xingyaoww/codeact-executor -f Dockerfile.executor .`: build the executor image.
- `cd code_exec_docker && bash start_jupyter_server.sh 8081`: start the local execution API expected by inference.
- `cd inference && python3 inference_single.py --model MODEL --api_key KEY --base_url URL --dataset sample_data_200`: run single-turn inference.
- `cd inference && python3 inference_multiple.py --setting react_exec --model MODEL --dataset sample_data_200 --skip_existing`: run multi-turn inference.
- `cd evaluation && python3 evaluation.py --setting single --model MODEL --dataset sample_data_200`: score generated outputs.
- `cd evaluation && python3 open_spreadsheet.py --dir_path ../data/sample_data_200/outputs --backend libreoffice`: recalculate spreadsheets when formulas need cached values.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation. Keep functions small and named in `snake_case`; constants use `UPPER_CASE`. Order imports as standard library, third-party, then local modules. Prefer the existing `os.path` style unless a touched module already uses `pathlib`. Do not commit generated `outputs/`, logs, PID files, or extracted temporary datasets.

## Testing Guidelines

There is no configured unit-test framework. Validate changes with the narrowest executable path: run the relevant inference script on a small dataset, then run `evaluation.py`. For workbook-comparison changes, use `evaluation/parity_test.py` or a recalculated sample and check both soft and hard scores. Name new diagnostics after the behavior covered, for example `test_output_name_generation.py`.

## Commit & Pull Request Guidelines

Recent history uses short imperative or descriptive messages, such as `update spreadsheetbench verified` and `Add cross-platform evaluation support via LibreOffice`. Keep commits focused and mention the affected area when useful, for example `evaluation: handle verified golden filenames`.

Pull requests should include a concise summary, dataset/model/settings used for validation, score or failure changes for evaluation logic, and any Docker or LibreOffice setup notes.

## Security & Configuration Tips

Do not hard-code API keys in scripts or examples. Pass credentials through CLI arguments or uncommitted wrappers. Keep `code_exec_docker/config.json` paths absolute and local to the machine running Docker.
