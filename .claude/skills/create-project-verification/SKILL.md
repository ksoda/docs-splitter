---
name: create-project-verification
description: Use when a repository needs a repeatable, evidence-producing check of a user-facing CLI, service, or application path.
---

# Create project verification

Build a runnable verification path from repository evidence, not imagined
inputs or assumptions. First inspect the project's instructions, primary user
surface, existing fixtures, run commands, and current checks. Ask the user only
for facts the repository cannot establish.

Create a concise project-specific skill and executable helper only where they
make the behavior repeatable. Ground their commands and expected outcomes in
the actual code and committed fixtures. The instructions must explain input
preparation, invocation, observable checks, evidence location, and cleanup.

Use a newly created evidence directory and stop without modifying it if it
already exists. Record the command, exit code, target revision, and each check
result. Preserve useful outputs and logs before deleting temporary work. Run
the generated instructions end to end once, inspect the evidence after
cleanup, and fix any proven harness defect before handing it over.

State what each check proves and which product requirements remain confirmed,
nonconforming, or unverified. A synthetic fixture is not approval of a real
user document, and extracted text equality does not establish visual fidelity.
Follow existing project permissions and stop conditions; creating a
verification helper does not grant new authority.

This skill adapts repository-interview, evidence, and end-to-end trial guidance
from pstack create-verification-skill; source revision and license are
recorded in UPSTREAM-NOTICES.md.
