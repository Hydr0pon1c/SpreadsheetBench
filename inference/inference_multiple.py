import os
import json
import argparse
import copy
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from tqdm import tqdm

from llm_api import get_llm_response
from code_exec import get_exec_client, extract_code, exec_code
from prompt_format import PROMPT_FORMAT_SINGLE, PROMPT_DF_RCT_FORMAT , PROMPT_NO_DF_RCT_FORMAT


_worker_state = threading.local()
_worker_id_lock = threading.Lock()
_next_worker_id = 0


def get_worker_index():
    global _next_worker_id
    if not hasattr(_worker_state, "index"):
        with _worker_id_lock:
            _worker_state.index = _next_worker_id
            _next_worker_id += 1
    return _worker_state.index


def load_split_ids(split_file):
    if not split_file:
        return None
    with open(split_file, 'r') as fp:
        split_data = json.load(fp)
    if isinstance(split_data, dict):
        if 'ids' in split_data:
            return {str(item) for item in split_data['ids']}
        for key in ('items', 'records', 'samples'):
            if key in split_data:
                return {str(item['id'] if isinstance(item, dict) else item) for item in split_data[key]}
    if isinstance(split_data, list):
        return {str(item['id'] if isinstance(item, dict) else item) for item in split_data}
    raise ValueError(f"Unsupported split file format: {split_file}")


def filter_dataset_by_split(dataset, split_file):
    split_ids = load_split_ids(split_file)
    if split_ids is None:
        return dataset
    filtered = [data for data in dataset if str(data['id']) in split_ids]
    missing_ids = split_ids - {str(data['id']) for data in filtered}
    if missing_ids:
        raise ValueError(f"{len(missing_ids)} split ids were not found in dataset: {sorted(missing_ids)[:5]}")
    print(f"Loaded split {split_file}: {len(filtered)} tasks")
    return filtered


def load_skill_text(skill_path):
    if not skill_path:
        return ""
    with open(skill_path, 'r') as fp:
        skill_text = fp.read().strip()
    if not skill_text:
        return ""
    return (
        "You have access to the following reusable spreadsheet skill. "
        "Follow it when it is relevant, but prioritize the current task instructions.\n\n"
        "<SKILL.md>\n"
        f"{skill_text}\n"
        "</SKILL.md>\n\n"
    )


def output_name(opt):
    return opt.run_name if opt.run_name else opt.model


def gen_file_content(input_file, row_limit):
    excel_file = pd.ExcelFile(input_file)
    sheet_names = excel_file.sheet_names
    excel_data = {}

    for sheet_name in sheet_names:
        df = excel_file.parse(sheet_name)
        row_count = row_limit if df.shape[0] > row_limit else df.shape[0]
        excel_data[sheet_name] = df.head(row_count).to_string()

    final_str = ""
    for sheet_name, sheet_str in excel_data.items():
        final_str += f"Sheet Name: {sheet_name}\n"
        final_str += sheet_str + "\n"
        final_str += "-" * 50 + "\n"
    
    return final_str


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, 0o777)


def build_output_name(file_name, task_id=None):
    if file_name.endswith("_input.xlsx"):
        return file_name.removesuffix("_input.xlsx") + "_output.xlsx"
    if file_name.endswith("_init.xlsx"):
        return file_name.removesuffix("_init.xlsx") + "_output.xlsx"
    if file_name == "initial.xlsx":
        if task_id is None:
            return "output.xlsx"
        return f"1_{task_id}_output.xlsx"
    return file_name.removesuffix(".xlsx") + "_output.xlsx"


def discover_test_cases(dataset_path, data):
    task_dir = f"{dataset_path}/{data['spreadsheet_path']}"
    task_id = str(data["id"])

    old_style_cases = []
    for idx in range(1, 100):
        input_file = f"{idx}_{task_id}_input.xlsx"
        if not os.path.exists(f"{task_dir}/{input_file}"):
            continue
        old_style_cases.append({
            "input_file": input_file,
            "output_file": build_output_name(input_file, task_id),
        })
    if old_style_cases:
        return old_style_cases

    verified_input = f"1_{task_id}_init.xlsx"
    if os.path.exists(f"{task_dir}/{verified_input}"):
        return [{
            "input_file": verified_input,
            "output_file": build_output_name(verified_input, task_id),
        }]

    if os.path.exists(f"{task_dir}/initial.xlsx"):
        return [{
            "input_file": "initial.xlsx",
            "output_file": build_output_name("initial.xlsx", task_id),
        }]

    raise FileNotFoundError(f"No supported input spreadsheet found in {task_dir}")


def build_prompt(opt, data, input_path, output_path, find_input_path):
    if opt.setting == 'row_exec':
        file_content = gen_file_content(find_input_path, opt.row)
        return PROMPT_FORMAT_SINGLE.format_map({
            'instruction': data['instruction'],
            'spreadsheet_path': input_path,
            'spreadsheet_content' : file_content,
            'instruction_type': data['instruction_type'],
            'answer_position': data['answer_position'],
            'max_turn_num' : opt.max_turn_num,
            'output_path': output_path
        })
    if opt.setting == 'react_exec':
        return PROMPT_NO_DF_RCT_FORMAT.format_map({
            'instruction': data['instruction'],
            'spreadsheet_path': input_path,
            'instruction_type': data['instruction_type'],
            'answer_position': data['answer_position'],
            'max_turn_num' : opt.max_turn_num,
            'output_path': output_path
        })
    if opt.setting == 'row_react_exec':
        file_content = gen_file_content(find_input_path, opt.row)
        return PROMPT_DF_RCT_FORMAT.format_map({
            'instruction': data['instruction'],
            'spreadsheet_path': input_path,
            'spreadsheet_content' : file_content,
            'instruction_type': data['instruction_type'],
            'answer_position': data['answer_position'],
            'max_turn_num' : opt.max_turn_num,
            'output_path': output_path
        })
    raise ValueError('Wrong multi-round setting.')


def process_task(data, opt, dataset_path, run_output_name, skill_prefix):
    messages = []
    test_cases = []
    response = ""
    client = None
    try:
        test_cases = discover_test_cases(dataset_path, data)
        first_case = test_cases[0]
        file_name = first_case["input_file"]
        input_path = f"/mnt/data/{data['spreadsheet_path']}/{file_name}"
        output_file_name = first_case["output_file"]
        output_path = f"/mnt/data/outputs/multi_{opt.setting}_{run_output_name}/{output_file_name}"
        find_input_path = f"{dataset_path}/{data['spreadsheet_path']}/{file_name}"
        local_output_path = output_path.replace('/mnt/data', dataset_path)

        if opt.skip_existing and os.path.exists(local_output_path):
            return None

        task_opt = copy.copy(opt)
        if opt.num_workers > 1:
            task_opt.conv_id = f"{opt.conv_id}-{get_worker_index()}"
        client = get_exec_client(task_opt.code_exec_url, task_opt.conv_id)

        prompt = build_prompt(task_opt, data, input_path, output_path, find_input_path)
        if skill_prefix:
            prompt = skill_prefix + prompt
        messages = [prompt]
        for _ in range(task_opt.max_turn_num):
            response = get_llm_response(messages, task_opt)
            messages.append(response)
            try:
                exec_result = exec_code(client, extract_code(response))
            except Exception:
                exec_result = 'Error occur when running code.'
            messages.append(exec_result)
            if os.path.exists(local_output_path):
                break
        return {
            'id': data['id'],
            'instruction_type': data['instruction_type'],
            'test_cases': test_cases,
            'conversation': messages,
            'solution': extract_code(response),
            'status': 'ok'
        }
    except Exception as e:
        print(f"Task {data['id']} failed after retries; skipping. Error: {e}", flush=True)
        return {
            'id': data['id'],
            'instruction_type': data['instruction_type'],
            'test_cases': test_cases,
            'conversation': messages,
            'solution': extract_code(response) if response else "",
            'status': 'failed',
            'error': str(e)
        }


def gen_solution(opt):
    dataset_path = os.path.abspath(f'../data/{opt.dataset}')
    with open(f'{dataset_path}/dataset.json', 'r') as fp:
        dataset = json.load(fp)
    dataset = filter_dataset_by_split(dataset, opt.split_file)

    dataset_output_dir = f'{dataset_path}/outputs'
    run_output_name = output_name(opt)
    model_output_dir = f'{dataset_output_dir}/multi_{opt.setting}_{run_output_name}'
    local_output_dir = 'outputs'
    ensure_dir(dataset_output_dir)
    ensure_dir(model_output_dir)
    ensure_dir(local_output_dir)
    skill_prefix = load_skill_text(opt.skill_path)
    output_jsonl = f'outputs/conv_multi_{opt.setting}_{run_output_name}.jsonl'

    if opt.num_workers <= 1:
        with open(output_jsonl, 'a+') as fp:
            for data in tqdm(dataset):
                conv_result = process_task(data, opt, dataset_path, run_output_name, skill_prefix)
                if conv_result is None:
                    continue
                fp.write(json.dumps(conv_result, ensure_ascii=False) + '\n')
                fp.flush()
        return

    print(
        f"Running generation with {opt.num_workers} workers. "
        f"Each worker uses its own code execution conv_id prefix: {opt.conv_id}-<worker_index>",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=opt.num_workers) as executor:
        futures = [
            executor.submit(
                process_task,
                data,
                opt,
                dataset_path,
                run_output_name,
                skill_prefix,
            )
            for data in dataset
        ]
        with open(output_jsonl, 'a+') as fp:
            for future in tqdm(as_completed(futures), total=len(futures)):
                conv_result = future.result()
                if conv_result is None:
                    continue
                fp.write(json.dumps(conv_result, ensure_ascii=False) + '\n')
                fp.flush()


def run_solution(opt):
    run_output_name = output_name(opt)
    client = get_exec_client(opt.code_exec_url, opt.conv_id)
    with open(f'outputs/conv_multi_{opt.setting}_{run_output_name}.jsonl', 'r') as fp:
        conv_records = [json.loads(line) for line in fp.readlines()]
    for conv in tqdm(conv_records):
        if conv.get("status") == "failed" or not conv.get("solution"):
            continue
        test_cases = conv.get("test_cases")
        if not test_cases:
            test_cases = [
                {
                    "input_file": f"{idx}_{conv['id']}_input.xlsx",
                    "output_file": f"{idx}_{conv['id']}_output.xlsx",
                }
                for idx in range(1, 4)
            ]
        first_case = test_cases[0]
        for test_case in test_cases[1:]:
            solution = conv['solution'].replace(first_case["input_file"], test_case["input_file"])
            solution = solution.replace(first_case["output_file"], test_case["output_file"])
            exec_result = exec_code(client, solution)


def parse_option():
    parser = argparse.ArgumentParser("command line arguments for generation.")

    parser.add_argument('--model', default="qwen3.5-35b-a3b",type=str, help='model name')
    parser.add_argument('--api_key', type=str, default="sk-658ff2c442984a10bcdc0a9abe3df395", help='the api key of model')
    parser.add_argument('--base_url', type=str, default="https://dashscope.aliyuncs.com/compatible-mode/v1", help='the base url of model')
    parser.add_argument('--setting', type=str, help='three setting: row_exec, react_exec, row_react_exec')
    parser.add_argument('--dataset', type=str, default="spreadsheetbench_verified_400", help='dataset name')
    parser.add_argument('--code_exec_url', type=str, default="http://localhost:8081/execute", help='code execution docker url')
    parser.add_argument('--conv_id', type=str, default="EVAL", help='code execution conversation id')
    parser.add_argument('--max_turn_num', type=int, default=100, help='max turn number of conversation')
    parser.add_argument('--row', type=int, default=5, help='the number of rows provided in the prompt')
    parser.add_argument('--skip_existing', action='store_true', help='skip tasks whose first output file already exists')
    parser.add_argument('--llm_max_retries', type=int, default=8, help='max retries for transient LLM API failures')
    parser.add_argument('--llm_retry_base_seconds', type=float, default=5.0, help='base delay in seconds for LLM API retry backoff')
    parser.add_argument('--split_file', type=str, default="", help='optional split file containing task ids to run')
    parser.add_argument('--skill_path', type=str, default="", help='optional SKILL.md file to prepend to each prompt')
    parser.add_argument('--run_name', type=str, default="", help='optional output name; defaults to model')
    parser.add_argument('--num_workers', type=int, default=8, help='number of parallel task workers for generation')
    
    opt = parser.parse_args()

    return opt


if __name__ == '__main__':
    opt = parse_option()
    print(opt)

    gen_solution(opt)
    run_solution(opt)
