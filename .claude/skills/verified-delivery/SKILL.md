---
name: verified-delivery
description: Use before reporting work as complete, fixed, or passing, or before recording a completed task; verify each claim against fresh evidence.
---

# Verified delivery

Do not infer completion from a diff, an earlier test run, or a successful test
suite alone. Match each claim to evidence from the current work.

1. Re-read the requested outcome, acceptance conditions, and applicable project
   requirements. Keep each requirement separate.
2. For every requirement, record one status: confirmed, nonconforming, or
   unverified. Name the command or artifact that supports the status. A test
   proves only the behavior it exercises.
3. Run the full relevant verification after the final change, read its output
   and exit code, then inspect the resulting artifact and complete diff.
4. Report implementation checks separately from product or hypothesis
   completion. Preserve known gaps and unresolved observations even when all
   runnable checks pass.
5. Keep requested evidence with its command, exit code, target revision, and
   check results. Clean temporary work only after durable evidence is saved.

If a check fails or a requirement lacks evidence, report that state and follow
the repository's existing stop and escalation rules. This skill does not grant
authority to change requirements or lower acceptance conditions.

For executable behavior, exercise the user-facing path and inspect the full
input-to-output artifact chain. This adapts direct-artifact guidance from
pstack principle-prove-it-works and completion-evidence guidance from
Superpowers verification-before-completion. Source revisions and licenses are
recorded in UPSTREAM-NOTICES.md.
