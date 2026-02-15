from __future__ import annotations

import argparse
import sys

from docs_splitter.adapters.io_json import load_request, save_result
from docs_splitter.domain import DomainError
from docs_splitter.pipeline.service import run_split


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split PDF document data into chunks.")
    parser.add_argument("--input", required=True, help="Input JSON path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        request = load_request(args.input)
        result = run_split(request)
        save_result(args.output, result)
    except DomainError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

