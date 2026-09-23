from __future__ import annotations

import argparse
import sys

from docs_splitter.adapters.io_json import load_request, save_plan
from docs_splitter.domain import DomainError
from docs_splitter.pipeline.service import build_plan, execute_split


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split a PDF into hierarchy-based units defined by its table of contents."
    )
    parser.add_argument("--input", required=True, help="Input request JSON path")
    parser.add_argument("--output", required=True, help="Output split-plan JSON path")
    parser.add_argument(
        "--split-output-dir",
        help="If set, also write split PDFs into this directory (requires --confirm-reviewed "
        "unless the plan has no boundary review items).",
    )
    parser.add_argument(
        "--confirm-reviewed",
        action="store_true",
        help="Acknowledge that a human has reviewed plan.review_items before writing split PDFs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        request = load_request(args.input)
        plan = build_plan(request)
        save_plan(args.output, plan)
        if args.split_output_dir:
            execute_split(
                request=request,
                plan=plan,
                output_dir=args.split_output_dir,
                confirmed=args.confirm_reviewed,
            )
    except DomainError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
