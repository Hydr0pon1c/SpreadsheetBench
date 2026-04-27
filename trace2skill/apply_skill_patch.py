import argparse
from pathlib import Path

from common import default_run_dir, ensure_dir, load_json


def render_patch_section(patch):
    items = patch.get("memory_items") or []
    edits = patch.get("edits") or []
    lines = ["\n## Trace-Derived Lessons\n"]
    for item in items:
        title = item.get("title", "Lesson")
        lesson = item.get("lesson", "")
        generalization = item.get("generalization", "")
        lines.append(f"### {title}\n")
        if lesson:
            lines.append(f"- Lesson: {lesson}\n")
        if generalization:
            lines.append(f"- Generalization: {generalization}\n")
    if not items:
        for edit in edits:
            content = edit.get("content", "").strip()
            if content:
                lines.append(content + "\n")
    return "\n".join(lines).rstrip() + "\n"


def parse_args():
    parser = argparse.ArgumentParser("Apply a consolidated Trace2Skill patch to skill0.")
    parser.add_argument("--run_id", default="manual")
    parser.add_argument("--skill0", required=True)
    parser.add_argument("--patch_json", default="")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    run_dir = default_run_dir(args.run_id)
    patch_json = Path(args.patch_json) if args.patch_json else run_dir / "merges" / "final_patch.json"
    output = Path(args.output) if args.output else run_dir / "skill_star" / "SKILL.md"
    ensure_dir(output.parent)

    base = Path(args.skill0).read_text().rstrip()
    patch = load_json(patch_json)
    output.write_text(base + "\n" + render_patch_section(patch))
    print(f"Wrote evolved skill to {output}")


if __name__ == "__main__":
    main()
