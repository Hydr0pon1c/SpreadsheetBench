import argparse
from pathlib import Path

from common import REPO_ROOT, dump_json, load_json, task_id, utc_now


def build_split(dataset, dataset_name, start, end, split_name):
    records = []
    for idx in range(start, end):
        item = dataset[idx]
        records.append({
            "index": idx,
            "id": item["id"],
            "instruction_type": item.get("instruction_type"),
            "spreadsheet_path": item.get("spreadsheet_path"),
        })
    return {
        "dataset": dataset_name,
        "split": split_name,
        "policy": "dataset_order_first_200_evolve_next_200_test",
        "created_at": utc_now(),
        "count": len(records),
        "ids": [task_id(record["id"]) for record in records],
        "records": records,
    }


def parse_args():
    parser = argparse.ArgumentParser("Prepare fixed SpreadsheetBench verified splits.")
    parser.add_argument("--dataset", default="spreadsheetbench_verified_400")
    parser.add_argument("--data_dir", default=str(REPO_ROOT / "data"))
    parser.add_argument("--output_dir", default=str(REPO_ROOT / "data" / "splits"))
    parser.add_argument("--evolve_size", type=int, default=200)
    parser.add_argument("--test_size", type=int, default=200)
    return parser.parse_args()


def main():
    args = parse_args()
    dataset_path = Path(args.data_dir) / args.dataset / "dataset.json"
    dataset = load_json(dataset_path)
    required = args.evolve_size + args.test_size
    if len(dataset) < required:
        raise ValueError(f"{dataset_path} has {len(dataset)} rows, but {required} are required")

    output_dir = Path(args.output_dir)
    evolve = build_split(dataset, args.dataset, 0, args.evolve_size, "evolve")
    test = build_split(dataset, args.dataset, args.evolve_size, required, "test")
    dump_json(evolve, output_dir / "verified_evolve_200.json")
    dump_json(test, output_dir / "verified_test_200.json")
    print(f"Wrote {evolve['count']} evolve ids and {test['count']} test ids to {output_dir}")


if __name__ == "__main__":
    main()

