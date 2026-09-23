import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "loop_guard.py"
SESSION = "test-session"


class LoopGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        (self.project / "tasks").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_hook(self, event: dict[str, Any]) -> dict[str, Any] | None:
        payload = {"session_id": SESSION, "cwd": str(self.project), **event}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)}
        result = subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(payload),
            capture_output=True, text=True, env=env, check=True,
        )
        return json.loads(result.stdout) if result.stdout else None

    def state_file(self) -> Path:
        return self.project / ".claude" / "state" / f"{SESSION}.json"

    def set_start(self, minutes_ago: float) -> None:
        self.run_hook({"hook_event_name": "SessionStart", "source": "startup"})
        state = json.loads(self.state_file().read_text(encoding="utf-8"))
        state["start"] = time.time() - minutes_ago * 60
        self.state_file().write_text(json.dumps(state), encoding="utf-8")

    def fail_command(self, command: str) -> dict[str, Any] | None:
        return self.run_hook({
            "hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
            "tool_input": {"command": command}, "error": "Exit code 1",
        })

    def context(self, output: dict[str, Any] | None) -> str:
        self.assertIsNotNone(output)
        assert output is not None
        return str(output["hookSpecificOutput"]["additionalContext"])

    def test_allows_tools_within_limit(self) -> None:
        self.set_start(10)
        output = self.run_hook({
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        self.assertIsNone(output)

    def test_denies_work_after_limit_but_allows_task_records(self) -> None:
        self.set_start(61)
        denied = self.run_hook({
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        assert denied is not None
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("60分", denied["hookSpecificOutput"]["permissionDecisionReason"])
        allowed = self.run_hook({
            "hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(self.project / "tasks" / "t1.md")},
        })
        self.assertIsNone(allowed)
        outside = self.run_hook({
            "hook_event_name": "PreToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": str(self.project / "src" / "x.py")},
        })
        self.assertIsNotNone(outside)

    def test_session_start_resets_but_compact_keeps_run(self) -> None:
        self.set_start(61)
        self.run_hook({"hook_event_name": "SessionStart", "source": "compact"})
        state = json.loads(self.state_file().read_text(encoding="utf-8"))
        self.assertLess(state["start"], time.time() - 60 * 60)
        self.run_hook({"hook_event_name": "SessionStart", "source": "resume"})
        state = json.loads(self.state_file().read_text(encoding="utf-8"))
        self.assertGreater(state["start"], time.time() - 60)

    def test_same_test_failure_escalates_then_stops(self) -> None:
        command = "PYTHONPATH=src python3 -m unittest tests/test_e2e.py"
        self.assertIsNone(self.fail_command(command))
        self.assertIn("エスカレーション", self.context(self.fail_command(command)))
        self.assertIn("停止", self.context(self.fail_command(command)))

    def test_test_success_resets_failure_count(self) -> None:
        command = "python3 -m unittest"
        self.fail_command(command)
        self.run_hook({
            "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        self.assertIsNone(self.fail_command(command))

    def test_repeated_edits_escalate_once(self) -> None:
        event = {
            "hook_event_name": "PostToolUse", "tool_name": "Edit",
            "tool_input": {"file_path": "src/x.py"},
        }
        outputs = [self.run_hook(event) for _ in range(6)]
        self.assertEqual([o is not None for o in outputs], [False] * 4 + [True, False])
        self.assertIn("エスカレーション", self.context(outputs[4]))

    def test_consecutive_tool_errors_escalate_then_stop(self) -> None:
        outputs = [self.fail_command(f"cmd{i}") for i in range(5)]
        self.assertIsNone(outputs[1])
        self.assertIn("エスカレーション", self.context(outputs[2]))
        self.assertIn("停止", self.context(outputs[4]))


if __name__ == "__main__":
    unittest.main()
