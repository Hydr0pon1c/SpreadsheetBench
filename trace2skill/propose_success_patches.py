import argparse
import json
import os
import re
from pathlib import Path

from openai import OpenAI

from common import default_run_dir, ensure_dir, load_jsonl, utc_now


SUCCESS_PROMPT = """You are an expert in success pattern analysis for spreadsheet manipulation agents.

Mission:
Given a successful agent trajectory, the current SKILL.md, and the evaluation result, identify the
generalizable behavior patterns that contributed to the correct answer. Your goal is to propose a
targeted skill patch that helps future agents repeat these effective behaviors.

Requirements:
1. Broad coverage: capture every clearly effective behavior in the trajectory that plausibly contributed
   to success.
2. Frequency awareness: if multiple successful behaviors are present, list broader and more reusable
   patterns first; absorb rare details into the nearest broader pattern.
3. Generalization: each pattern must describe a mechanism, not a single task-specific detail.
4. Skill encoding: convert the strongest patterns into compact success memory items and a concise
   SKILL.md patch.

Constraints:
- Infer only lessons supported by the supplied successful trajectory and evaluation result.
- Do not write task-specific answers, benchmark ids, local paths, golden values, or one-off constants into the skill.
- Do not include concrete cell ranges, sheet names, filenames, or benchmark values from the trajectory, even as examples.
- Use generic terms such as "the target range", "the relevant worksheet", or "the relevant columns".
- Prefer reusable patterns about task interpretation, range/scope control, validation, library/tool choice,
  formula handling, formatting preservation, and robust execution.

Return strict JSON with this schema:
{
  "trajectory_id": "...",
  "analyst_type": "success",
  "success_surface": "...",
  "effective_behaviors": ["..."],
  "evidence": ["..."],
  "memory_items": [
    {"title": "...", "lesson": "...", "generalization": "..."}
  ],
  "edits": [
    {"file": "SKILL.md", "op": "append_section", "target": "Trace-Derived Lessons", "content": "..."}
  ]
}
"""


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in response")
    return json.loads(match.group(0))


def compact_trajectory(item, max_chars):
    trajectory = item["trajectory"]
    conversation = trajectory.get("conversation", [])
    if isinstance(conversation, list):
        compact_conv = conversation[-8:]
    else:
        compact_conv = str(conversation)[-max_chars:]
    payload = {
        "id": item["id"],
        "metadata": {
            "instruction": item["metadata"].get("instruction"),
            "instruction_type": item["metadata"].get("instruction_type"),
            "answer_position": item["metadata"].get("answer_position"),
        },
        "eval": item["eval"],
        "solution": trajectory.get("solution", ""),
        "conversation_tail": compact_conv,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(text) > max_chars:
        return text[-max_chars:]
    return text


def parse_args():
    parser = argparse.ArgumentParser("Propose Trace2Skill JSON patches from successful trajectories.")
    parser.add_argument("--run_id", default="manual")
    parser.add_argument("--labeled_jsonl", default="")
    parser.add_argument("--skill_path", required=True)
    parser.add_argument("--model", default="qwen3.5-35b-a3b")
    parser.add_argument("--api_key", default=os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--base_url", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max_chars", type=int, default=16000)
    parser.add_argument("--output_dir", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.api_key:
        raise ValueError("Provide --api_key or set DASHSCOPE_API_KEY/OPENAI_API_KEY.")
    run_dir = default_run_dir(args.run_id)
    labeled_jsonl = Path(args.labeled_jsonl) if args.labeled_jsonl else run_dir / "evolve" / "labeled_trajectories.jsonl"
    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "patches" / "success"
    rejected_dir = output_dir / "rejected"
    ensure_dir(output_dir)
    ensure_dir(rejected_dir)

    skill_text = Path(args.skill_path).read_text()
    records = [item for item in load_jsonl(labeled_jsonl) if item["label"] == "T+"]
    if args.limit:
        records = records[:args.limit]

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    for item in records:
        prompt = (
            f"{SUCCESS_PROMPT}\n\n"
            f"Current SKILL.md:\n{skill_text}\n\n"
            f"Successful trajectory:\n{compact_trajectory(item, args.max_chars)}"
        )
        response = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
        try:
            patch = extract_json(response)
            patch.setdefault("trajectory_id", str(item["id"]))
            patch.setdefault("analyst_type", "success")
            patch["created_at"] = utc_now()
            path = output_dir / f"{item['id']}.json"
        except Exception as exc:
            patch = {"id": item["id"], "error": str(exc), "raw_response": response}
            path = rejected_dir / f"{item['id']}.json"
        path.write_text(json.dumps(patch, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
