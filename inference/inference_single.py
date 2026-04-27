import os
import json
import argparse
import pandas as pd
from tqdm import tqdm

from llm_api import get_llm_response
from prompt_format import PROMPT_FORMAT_SINGLE
from code_exec import get_exec_client, extract_code, exec_code


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


def gen_solution(opt):
    dataset_path = os.path.abspath(f'../data/{opt.dataset}')
    with open(f'{dataset_path}/dataset.json', 'r') as fp:
        dataset = json.load(fp)

    dataset_output_dir = f'{dataset_path}/outputs'
    model_output_dir = f'{dataset_output_dir}/single_{opt.model}'
    local_output_dir = 'outputs'
    local_log_dir = 'log'
    ensure_dir(dataset_output_dir)
    ensure_dir(model_output_dir)
    ensure_dir(local_output_dir)
    ensure_dir(local_log_dir)

    # create code execution client
    client = get_exec_client(opt.code_exec_url, opt.conv_id)
        
    for data in tqdm(dataset):
        try:
            test_cases = discover_test_cases(dataset_path, data)
            first_case = test_cases[0]
            file_name = first_case["input_file"]

            input_path = f"/mnt/data/{data['spreadsheet_path']}/{file_name}"
            output_file_name = first_case["output_file"]
            output_path = f"/mnt/data/outputs/single_{opt.model}/{output_file_name}"
            
            find_input_path = f"{dataset_path}/{data['spreadsheet_path']}/{file_name}"
            file_content = gen_file_content(find_input_path, opt.row)
            prompt = ""
            prompt = PROMPT_FORMAT_SINGLE.format_map({
                'instruction': data['instruction'],
                'spreadsheet_path': input_path,
                'spreadsheet_content' : file_content,
                'instruction_type': data['instruction_type'],
                'answer_position': data['answer_position'],
                'output_path': output_path
            })
            messages = [prompt]
            response = get_llm_response(messages, opt)
            messages.append(response)
            try:
                exec_result = exec_code(client, extract_code(response))
            except Exception as e:
                exec_result = 'Error occur when running code.'
            messages.append(exec_result)
            conv_result = {
                'id': data['id'],
                'instruction_type': data['instruction_type'],
                'test_cases': test_cases,
                'conversation': messages,
                'solution': extract_code(response),
                'status': 'ok'
            }
        except Exception as e:
            print(str(e))
            conv_result = {
                'id': data['id'],
                'instruction_type': data['instruction_type'],
                'test_cases': [],
                'conversation': "",
                'solution': "",
                'status': 'failed',
                'error': str(e)
            }
            with open(f'log/single_{opt.model}.jsonl', 'a+') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        with open(f'outputs/conv_single_{opt.model}.jsonl', 'a+') as fp:
            fp.write(json.dumps(conv_result, ensure_ascii=False) + '\n')


def run_solution(opt):
    client = get_exec_client(opt.code_exec_url, opt.conv_id)
    with open(f'outputs/conv_single_{opt.model}.jsonl', 'r') as fp:
        conv_records = [json.loads(line) for line in fp.readlines()]
    for conv in tqdm(conv_records):
        try:
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
        except Exception as e:
            print(e)


def parse_option():
    parser = argparse.ArgumentParser("command line arguments for generation.")
    
    parser.add_argument('--model', type=str, help='model name')
    parser.add_argument('--api_key', type=str, default="", help='the api key of model')
    parser.add_argument('--base_url', type=str, default="", help='the base url of model')
    parser.add_argument('--dataset', type=str, default="sample_data_200", help='dataset name')
    parser.add_argument('--code_exec_url', type=str, default="http://localhost:8081/execute", help='code execution docker url')
    parser.add_argument('--conv_id', type=str, default="EVAL", help='code execution conversation id')
    parser.add_argument('--row', type=int, default=5, help='the number of rows provided in the prompt')
    parser.add_argument('--llm_max_retries', type=int, default=8, help='max retries for transient LLM API failures')
    parser.add_argument('--llm_retry_base_seconds', type=float, default=5.0, help='base delay in seconds for LLM API retry backoff')
    opt = parser.parse_args()

    return opt


if __name__ == '__main__':
    opt = parse_option()
    print(opt)

    gen_solution(opt)
    run_solution(opt)
