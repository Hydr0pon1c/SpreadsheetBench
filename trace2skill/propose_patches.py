import argparse
import json
import os
import re
from pathlib import Path

from openai import OpenAI

from common import REPO_ROOT, default_run_dir, ensure_dir, load_jsonl, utc_now


PATCH_PROMPT = """You are an expert failure-analysis agent for spreadsheet manipulation tasks.

Mission:
Given an agent's execution artifacts, the current SKILL.md, and the evaluation result for one failed
trajectory, diagnose why the agent failed, identify causal failure reasons, and propose a targeted skill
patch that would help future agents avoid similar failures. Your analysis must be systematic,
evidence-driven, and reproducible. Do not guess when the trajectory provides evidence.

Required workflow:
1. Understand the task and failure surface: identify exactly what appears wrong in the output or behavior.
2. Trace the failure to agent behavior: locate the decision, assumption, or code pattern that likely produced the mismatch.
3. Form a minimal-fix hypothesis: describe the smallest behavioral change that would plausibly prevent this class of failure.
4. Generalize: convert that diagnosis into at most 3 failure memory items that are useful beyond this single task.
5. Propose a skill patch: encode only the general lesson, not a task-specific correction.

Constraints:
- Infer only lessons supported by the supplied trajectory and evaluation result.
- Do not write task-specific answers, benchmark ids, local paths, golden values, or one-off constants into the skill.
- Do not include concrete cell ranges, sheet names, filenames, or benchmark values from the trajectory, even as examples.
- Use generic terms such as "the target range", "the relevant worksheet", or "the relevant columns".
- Prefer causal lessons about spreadsheet manipulation, validation, library/tool choice, range boundaries, formulas,
  formatting preservation, and execution hygiene.

Return strict JSON with this schema:
{
  "trajectory_id": "...",
  "analyst_type": "error",
  "failure_surface": "...",
  "root_cause": "...",
  "minimal_fix_hypothesis": "...",
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
    parser = argparse.ArgumentParser("Propose Trace2Skill JSON patches from failed trajectories.")
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
    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "patches" / "error"
    rejected_dir = output_dir / "rejected"
    ensure_dir(output_dir)
    ensure_dir(rejected_dir)

    skill_text = Path(args.skill_path).read_text()
    records = [item for item in load_jsonl(labeled_jsonl) if item["label"] == "T-"]
    if args.limit:
        records = records[:args.limit]

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    for item in records:
        prompt = (
            f"{PATCH_PROMPT}\n\n"
            f"Current SKILL.md:\n{skill_text}\n\n"
            f"Failed trajectory:\n{compact_trajectory(item, args.max_chars)}"
        )
        response = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": prompt}],
        ).choices[0].message.content
        try:
            patch = extract_json(response)
            patch.setdefault("trajectory_id", str(item["id"]))
            patch.setdefault("analyst_type", "error")
            patch["created_at"] = utc_now()
            path = output_dir / f"{item['id']}.json"
        except Exception as exc:
            patch = {"id": item["id"], "error": str(exc), "raw_response": response}
            path = rejected_dir / f"{item['id']}.json"
        path.write_text(json.dumps(patch, indent=2, ensure_ascii=False) + "\n")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
