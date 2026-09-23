---
name: verify-docs-splitter
description: Run the docs-splitter CLI against its committed synthetic PDF and inspect durable evidence before reporting implementation status.
---

# Verify docs-splitter

Use this skill to check the current CLI behavior against the checked-in synthetic
input. It verifies the command-line path, not all PRD requirements and not a
real user's PDF.

## Run

From the repository root, choose an evidence directory that does not already
exist, then run:

    .venv/bin/python scripts/verify_project.py --output-dir /tmp/docs-splitter-evidence-20260923-run-01

Use a different unused suffix for every run. The script locates the repository
from its own file path and can be invoked by absolute path from any working directory. It loads tests/data/input_ok.json and
tests/data/sample_magazine.pdf. It does not ask for a hand-created temporary
JSON file.

## Checks and evidence

A zero exit code means the listed synthetic-fixture checks passed. Inspect
report.md and manifest.json in the evidence directory. They retain the exact
invocation, each CLI command and exit code, target revision, fixture hashes,
check results, and requirement-level PRD statuses. CLI output logs, the
generated split plan, and split PDFs are also preserved. A failed check returns
a nonzero exit code and remains marked failed in the evidence.

The runner checks definition-only output, expected unit and unclassified page
ranges, continuous page assignment, boundary checks, refusal to split without
the review flag, synthetic confirmed output, every output page's extracted
text against its corresponding source page in order, source PDF SHA-256, and
rejection of a rerun that would overwrite existing split PDFs.

The script uses the confirmation flag only for the committed synthetic
fixture. It does not approve a real PDF. Text extraction equality is not proof
of exact visual fidelity. The PRD status table keeps known gaps visible,
including direct PDF outline reading, ambiguous-match candidates, thumbnails,
multi-level review coverage, human review, and real-PDF timing.

## Cleanup

The script removes only its temporary work directory. Keep the evidence
directory for review. Never use the synthetic confirmation flag as evidence
that a real PDF was reviewed.
