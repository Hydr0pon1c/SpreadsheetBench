import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def load_json(path):
    with open(path, "r") as fp:
        return json.load(fp)


def dump_json(data, path):
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)


def load_jsonl(path):
    records = []
    with open(path, "r") as fp:
        for line in fp:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(records, path):
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def task_id(value):
    return str(value)


def load_split_ids(split_file):
    if not split_file:
        return None
    split_data = load_json(split_file)
    if isinstance(split_data, dict):
        if "ids" in split_data:
            return {task_id(item) for item in split_data["ids"]}
        for key in ("items", "records", "samples"):
            if key in split_data:
                return {task_id(item["id"] if isinstance(item, dict) else item) for item in split_data[key]}
    if isinstance(split_data, list):
        return {task_id(item["id"] if isinstance(item, dict) else item) for item in split_data}
    raise ValueError(f"Unsupported split file format: {split_file}")


def filter_dataset(dataset, split_file):
    split_ids = load_split_ids(split_file)
    if split_ids is None:
        return dataset
    filtered = [item for item in dataset if task_id(item["id"]) in split_ids]
    missing = split_ids - {task_id(item["id"]) for item in filtered}
    if missing:
        raise ValueError(f"{len(missing)} split ids were not found: {sorted(missing)[:5]}")
    return filtered


def dataset_by_id(dataset):
    return {task_id(item["id"]): item for item in dataset}


def default_run_dir(run_id, output_root="trace2skill_runs"):
    return REPO_ROOT / output_root / run_id

