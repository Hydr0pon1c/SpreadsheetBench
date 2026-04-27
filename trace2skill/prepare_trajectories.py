import argparse
from pathlib import Path

from common import (
    REPO_ROOT,
    dataset_by_id,
    default_run_dir,
    dump_json,
    filter_dataset,
    load_json,
    load_jsonl,
    task_id,
    write_jsonl,
)


def output_exists(record, output_dir):
    if not output_dir:
        return True
    for test_case in record.get("test_cases") or []:
        output_file = test_case.get("output_file")
        if output_file and Path(output_dir, output_file).exists():
            return True
    return False


def choose_records(records, output_dir):
    selected = {}
    for idx, record in enumerate(records):
        rid = task_id(record["id"])
        score = (
            1 if record.get("status") == "ok" else 0,
            1 if output_exists(record, output_dir) else 0,
            idx,
        )
        previous = selected.get(rid)
        if previous is None or score >= previous[0]:
            selected[rid] = (score, record)
    return {rid: item[1] for rid, item in selected.items()}


def parse_args():
    parser = argparse.ArgumentParser("Join trajectories with dataset metadata and evaluation results.")
    parser.add_argument("--run_id", default="manual")
    parser.add_argument("--dataset", default="spreadsheetbench_verified_400")
    parser.add_argument("--split_file", default=str(REPO_ROOT / "data" / "splits" / "verified_evolve_200.json"))
    parser.add_argument("--conv_jsonl", required=True)
    parser.add_argument("--eval_json", required=True)
    parser.add_argument("--output_dir", default="", help="optional directory containing generated xlsx outputs")
    parser.add_argument("--output_jsonl", default="")
    parser.add_argument("--summary_json", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    dataset_path = REPO_ROOT / "data" / args.dataset / "dataset.json"
    dataset = filter_dataset(load_json(dataset_path), args.split_file)
    metadata = dataset_by_id(dataset)
    eval_by_id = {task_id(item["id"]): item for item in load_json(args.eval_json)}
    selected = choose_records(load_jsonl(args.conv_jsonl), args.output_dir)

    labeled = []
    for rid, data in metadata.items():
        conv = selected.get(rid)
        eval_result = eval_by_id.get(rid)
        if conv is None or eval_result is None:
            continue
        hard = int(eval_result.get("hard_restriction", 0))
        labeled.append({
            "id": data["id"],
            "label": "T+" if hard == 1 else "T-",
            "metadata": data,
            "trajectory": conv,
            "eval": eval_result,
        })

    run_dir = default_run_dir(args.run_id)
    output_jsonl = Path(args.output_jsonl) if args.output_jsonl else run_dir / "evolve" / "labeled_trajectories.jsonl"
    summary_json = Path(args.summary_json) if args.summary_json else run_dir / "evolve" / "trajectory_summary.json"
    write_jsonl(labeled, output_jsonl)
    dump_json(
        {
            "dataset": args.dataset,
            "split_file": args.split_file,
            "conv_jsonl": args.conv_jsonl,
            "eval_json": args.eval_json,
            "count": len(labeled),
            "positive": sum(1 for item in labeled if item["label"] == "T+"),
            "negative": sum(1 for item in labeled if item["label"] == "T-"),
        },
        summary_json,
    )
    print(f"Wrote {len(labeled)} labeled trajectories to {output_jsonl}")


if __name__ == "__main__":
    main()

