#!/usr/bin/env python3
"""Claude Code hook: time limit and escalation signals for the autonomous loop.

Decisions and provisional thresholds: development-discipline
docs/first-pilot-conditions.md (N-05).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

LIMIT_MINUTES = float(os.environ.get("LOOP_GUARD_LIMIT_MINUTES", "60"))
TEST_FAILURES_TO_ESCALATE = 2
TEST_FAILURES_TO_STOP = 3
EDITS_TO_ESCALATE = 5
ERRORS_TO_ESCALATE = 3
ERRORS_TO_STOP = 5

TEST_COMMAND = re.compile(r"\b(unittest|pytest)\b")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}

ESCALATE = (
    "エスカレーション: {signal}。同じ方針で修正を続けない。"
    "routineサブエージェント（Haiku）の作業なら本体に戻し、"
    "本体の実行中（Sonnet）ならescalationサブエージェント（Opus）に委譲する。"
)
STOP = (
    "停止: {signal}。作業を止め、tasks/ の課題に停止理由、経過時間"
    "（{elapsed:.0f}分）、失敗したコマンドを記録して報告する。"
    "テストが通らない変更はコミットしない。"
)


def state_path(project_dir: Path, session_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)
    return project_dir / ".claude" / "state" / f"{safe_id}.json"


def load_state(path: Path, now: float) -> dict[str, Any]:
    if path.exists():
        with path.open(encoding="utf-8") as f:
            state: dict[str, Any] = json.load(f)
        return state
    return {"start": now, "test_failures": {}, "edits": {}, "errors": 0}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    tmp.replace(path)


def context(event: str, message: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": message},
        "systemMessage": message,
    }


def is_task_file(file_path: str, project_dir: Path) -> bool:
    tasks = (project_dir / "tasks").resolve()
    try:
        Path(file_path).resolve().relative_to(tasks)
    except ValueError:
        return False
    return True


def pre_tool_use(event: dict[str, Any], state: dict[str, Any],
                 project_dir: Path, elapsed: float) -> dict[str, Any] | None:
    if elapsed < LIMIT_MINUTES:
        return None
    tool = event.get("tool_name", "")
    file_path = str(event.get("tool_input", {}).get("file_path", ""))
    if tool in READ_TOOLS or (tool in EDIT_TOOLS and is_task_file(file_path, project_dir)):
        return None
    reason = STOP.format(signal=f"無人実行の上限{LIMIT_MINUTES:.0f}分に到達", elapsed=elapsed)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }


def post_tool_use(event: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    state["errors"] = 0
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    if tool == "Bash":
        command = " ".join(str(tool_input.get("command", "")).split())
        state["test_failures"].pop(command, None)
        return None
    if tool not in EDIT_TOOLS:
        return None
    file_path = str(tool_input.get("file_path") or tool_input.get("notebook_path", ""))
    count = state["edits"].get(file_path, 0) + 1
    state["edits"][file_path] = count
    if count == EDITS_TO_ESCALATE:
        signal = f"{file_path} を{count}回書き直した"
        return context("PostToolUse", ESCALATE.format(signal=signal))
    return None


def post_tool_use_failure(event: dict[str, Any], state: dict[str, Any],
                          elapsed: float) -> dict[str, Any] | None:
    state["errors"] += 1
    command = " ".join(str(event.get("tool_input", {}).get("command", "")).split())
    if event.get("tool_name") == "Bash" and TEST_COMMAND.search(command):
        failures = state["test_failures"].get(command, 0) + 1
        state["test_failures"][command] = failures
        signal = f"同じテストが{failures}回失敗（{command}）"
        if failures >= TEST_FAILURES_TO_STOP:
            return context("PostToolUseFailure", STOP.format(signal=signal, elapsed=elapsed))
        if failures == TEST_FAILURES_TO_ESCALATE:
            return context("PostToolUseFailure", ESCALATE.format(signal=signal))
    errors = state["errors"]
    signal = f"ツールエラーが{errors}回連続"
    if errors >= ERRORS_TO_STOP:
        return context("PostToolUseFailure", STOP.format(signal=signal, elapsed=elapsed))
    if errors == ERRORS_TO_ESCALATE:
        return context("PostToolUseFailure", ESCALATE.format(signal=signal))
    return None


def main() -> int:
    event: dict[str, Any] = json.load(sys.stdin)
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".")
    path = state_path(project_dir, str(event.get("session_id", "unknown")))
    now = time.time()
    name = event.get("hook_event_name")
    # Each start, resume, or /clear begins a new run; compaction continues it.
    if name == "SessionStart" and event.get("source") != "compact" and path.exists():
        path.unlink()
    state = load_state(path, now)
    elapsed = (now - float(state["start"])) / 60

    output: dict[str, Any] | None = None
    if name == "PreToolUse":
        output = pre_tool_use(event, state, project_dir, elapsed)
    elif name == "PostToolUse":
        output = post_tool_use(event, state)
    elif name == "PostToolUseFailure":
        output = post_tool_use_failure(event, state, elapsed)

    save_state(path, state)
    if output is not None:
        json.dump(output, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
