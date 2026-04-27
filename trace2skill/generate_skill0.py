import argparse
import os
from pathlib import Path

from openai import OpenAI

from common import REPO_ROOT, dump_json, ensure_dir, utc_now


SKILL0_PROMPT = """You are creating the initial parametric skill for a spreadsheet manipulation agent.

Write a concise SKILL.md that captures general spreadsheet manipulation knowledge only.
The skill will be prepended to prompts for tasks that require editing xlsx files with Python.

Requirements:
- Use Markdown.
- Focus on general practices for understanding the task, reading workbooks, editing cells/ranges, preserving sheets and formats, handling formulas, and validating outputs.
- Keep it actionable and compact.

Return only the SKILL.md content.
"""


def parse_args():
    parser = argparse.ArgumentParser("Generate the parametric skill0 SKILL.md.")
    parser.add_argument("--model", default="qwen3.5-35b-a3b")
    parser.add_argument("--api_key", default="sk-658ff2c442984a10bcdc0a9abe3df395")
    parser.add_argument("--base_url", default=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "skills" / "spreadsheet-parametric-qwen3.5-35b-a3b" / "SKILL.md"),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.api_key:
        raise ValueError("Provide --api_key or set DASHSCOPE_API_KEY/OPENAI_API_KEY.")

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    completion = client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": SKILL0_PROMPT}],
    )
    skill_text = completion.choices[0].message.content.strip()
    if skill_text.startswith("```"):
        skill_text = skill_text.strip("`")
        if skill_text.startswith("markdown"):
            skill_text = skill_text[len("markdown"):].lstrip()

    output_path = Path(args.output)
    ensure_dir(output_path.parent)
    output_path.write_text(skill_text + "\n")
    dump_json(
        {
            "created_at": utc_now(),
            "model": args.model,
            "base_url": args.base_url,
            "output": str(output_path),
            "prompt": SKILL0_PROMPT,
        },
        output_path.parent / "generation_metadata.json",
    )
    print(f"Wrote skill0 to {output_path}")


if __name__ == "__main__":
    main()

