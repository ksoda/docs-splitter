---
name: systematic-debugging
description: Use for bugs, failed checks, or unexpected behavior before changing code to identify and test the likely cause.
---

# Systematic debugging

Use this when behavior differs from the request, a check fails, or a tool
produces an unexpected result.

1. Read the complete error and reproduce the behavior with the same inputs.
   Check recent changes, configuration, and environment.
2. Trace the affected data and component boundaries. Compare the failing path
   with a working example and list relevant differences.
3. State one evidence-based cause to investigate. Test it with the smallest
   useful change or diagnostic. If evidence contradicts it, form a new
   hypothesis instead of stacking fixes.
4. Fix the cause, add a focused regression check when appropriate, then run
   the relevant verification and inspect its output.

Do not guess from symptoms or bundle unrelated cleanup into a repair. If the
cause, required decision, or safe next step is unclear, investigate further or
escalate under the repository's existing rules. Do not replace local stop
conditions with a fixed attempt count, and do not require TDD for unrelated
work.

This skill adapts the investigation and single-hypothesis workflow from
Superpowers systematic-debugging; source revision and license are recorded in
UPSTREAM-NOTICES.md.
