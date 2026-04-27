import argparse
from pathlib import Path

from common import default_run_dir, load_json, load_split_ids, task_id


def load_eval(path, split_ids):
    if not path:
        return []
    records = load_json(path)
    if split_ids is not None:
        records = [item for item in records if task_id(item["id"]) in split_ids]
    return records


def metrics(records):
    if not records:
        return {"count": 0, "hard": 0, "hard_rate": 0.0, "soft_avg": 0.0}
    hard = sum(float(item.get("hard_restriction", 0)) for item in records)
    soft = sum(float(item.get("soft_restriction", 0)) for item in records)
    return {
        "count": len(records),
        "hard": hard,
        "hard_rate": hard / len(records),
        "soft_avg": soft / len(records),
    }


def row(name, stats, baseline=None):
    delta = ""
    if baseline and stats["count"]:
        delta = f"{(stats['hard_rate'] - baseline['hard_rate']) * 100:+.2f} pp"
    return (
        f"| {name} | {stats['count']} | {stats['hard']:.0f} | "
        f"{stats['hard_rate'] * 100:.2f}% | {stats['soft_avg'] * 100:.2f}% | {delta} |"
    )


def parse_args():
    parser = argparse.ArgumentParser("Summarize Trace2Skill eval json files into a report.")
    parser.add_argument("--run_id", default="manual")
    parser.add_argument("--split_file", default="")
    parser.add_argument("--eval_no_skill", default="")
    parser.add_argument("--eval_skill0", default="")
    parser.add_argument("--eval_skill_star", default="")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    split_ids = load_split_ids(args.split_file) if args.split_file else None
    no_skill = metrics(load_eval(args.eval_no_skill, split_ids))
    skill0 = metrics(load_eval(args.eval_skill0, split_ids))
    skill_star = metrics(load_eval(args.eval_skill_star, split_ids))

    lines = [
        "# Trace2Skill SpreadsheetBench Report",
        "",
        f"- Split file: `{args.split_file or 'none'}`",
        "",
        "| Condition | Count | Hard Pass | Hard Rate | Soft Avg | Delta vs No Skill |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        row("No Skill", no_skill),
        row("skill0", skill0, no_skill),
        row("skill*", skill_star, no_skill),
        "",
    ]
    output = Path(args.output) if args.output else default_run_dir(args.run_id) / "report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
