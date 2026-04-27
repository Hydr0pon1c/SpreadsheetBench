import argparse
import json
import os
import random
from pathlib import Path

from openai import OpenAI

from common import default_run_dir, ensure_dir, load_json, utc_now


MERGE_PROMPT = """You are a skill edit coordinator. You receive multiple independently proposed patches
that each suggest changes to a spreadsheet manipulation skill. Your job is to merge them into one
coherent, non-redundant consolidated JSON patch.

Guidelines:
1. Deduplicate: when multiple patches propose the same or very similar lessons, keep the best version
   with the clearest wording and strongest evidence.
2. Resolve conflicts: if patches propose contradictory guidance, choose the one with stronger
   justification or synthesize both into a more precise principle.
3. Preserve unique insights: different patches may address different failure patterns; include unique,
   non-redundant edits.
4. Maintain conciseness: the merged patch should be shorter than the sum of unique input edits.
5. Keep edits independent: consolidated edits should be conceptually separable and should not repeat
   the same passage in different wording.
6. Apply prevalent pattern bias: when multiple patches independently propose similar lessons, treat
   that recurrence as evidence of a systematic property and preserve it with higher priority.

Filtering rules:
- Keep only general spreadsheet manipulation lessons supported by the supplied patches.
- Drop benchmark-specific ids, concrete answers, local paths, one-off constants, and duplicated lessons.
- Drop concrete cell ranges, sheet names, filenames, and benchmark values, even if they appear as examples.
- Use generic wording such as "the target range", "the relevant worksheet", or "the relevant columns".

Return strict JSON with:
{
  "reasoning": "...",
  "analyst_type": "merge",
  "source_patch_count": 0,
  "memory_items": [{"title": "...", "lesson": "...", "generalization": "..."}],
  "edits": [{"file": "SKILL.md", "op": "append_section", "target": "Trace-Derived Lessons", "content": "..."}],
  "changelog_entries": ["..."]
}
"""


def load_patch_files(input_dir):
    return [
        path for path in sorted(Path(input_dir).glob("*.json"))
        if path.is_file() and path.parent.name != "rejected"
    ]


def parse_args():
    parser = argparse.ArgumentParser("Hierarchically merge Trace2Skill JSON patches.")
    parser.add_argument("--run_id", default="manual")
    parser.add_argument("--input_dir", default="")
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--model", default="qwen3.5-35b-a3b")
    parser.add_argument("--api_key", default=os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--base_url", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def merge_batch(client, model, patches):
    prompt = MERGE_PROMPT + "\n\nPatch proposals:\n" + json.dumps(patches, ensure_ascii=False, indent=2)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    ).choices[0].message.content
    start = response.find("{")
    end = response.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in merge response")
    merged = json.loads(response[start:end])
    merged["created_at"] = utc_now()
    merged["source_patch_count"] = len(patches)
    return merged


def main():
    args = parse_args()
    if not args.api_key:
        raise ValueError("Provide --api_key or set DASHSCOPE_API_KEY/OPENAI_API_KEY.")
    run_dir = default_run_dir(args.run_id)
    input_dir = Path(args.input_dir) if args.input_dir else run_dir / "patches" / "error"
    output_dir = Path(args.output_dir) if args.output_dir else run_dir / "merges"
    ensure_dir(output_dir)

    patch_files = load_patch_files(input_dir)
    random.Random(args.seed).shuffle(patch_files)
    current = [load_json(path) for path in patch_files]
    if not current:
        raise ValueError(f"No patch json files found in {input_dir}")

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    level = 0
    while len(current) > 1:
        level_dir = output_dir / f"level_{level}"
        ensure_dir(level_dir)
        next_level = []
        for batch_idx in range(0, len(current), args.batch_size):
            batch = current[batch_idx:batch_idx + args.batch_size]
            merged = merge_batch(client, args.model, batch)
            out_path = level_dir / f"batch_{batch_idx // args.batch_size}.json"
            out_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
            next_level.append(merged)
            print(f"Wrote {out_path}")
        current = next_level
        level += 1

    final_path = output_dir / "final_patch.json"
    final_path.write_text(json.dumps(current[0], indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {final_path}")


if __name__ == "__main__":
    main()
