---
name: seed-fault
description: Seed one deliberate fault into the pipeline, record the red test output and hook stderr in docs/SEEDED_FAULTS.md, then restore it. Use when asked to break the pipeline on purpose, seed a fault, or test whether the suite catches something.
allowed-tools: Read, Edit, Bash(make test*), Bash(python -m pytest*), Bash(git diff*), Bash(git status*)
---

# Current state

!`git status --short`

# Seeding fault: $ARGUMENTS

The point is evidence that a check goes red, not a fix. Work in this order.

1. **Start clean.** If `git status` above lists modified files under `src/`,
   stop and say so. A fault seeded on top of other changes proves nothing.

2. **Make exactly one change** with the Edit tool, so the PostToolUse hook
   fires. Show the change with `git diff`.

3. **Capture the hook.** Quote the hook's stderr word for word. If the hook
   did not fire (an edit outside `src/`, or a fault the leakage tests
   cannot see), say so plainly. That is a finding, not a failure.

4. **Run `make test`** and quote the summary lines and the failing test
   names exactly. Do not paraphrase the output.

5. **Record** a new section in `docs/SEEDED_FAULTS.md`:
   `## Fault N: <description>`, then the diff, the hook stderr, the
   `make test` output (each in a code block), and one sentence on which
   test caught it and why.

6. **Restore.** Undo the change with the Edit tool, run `make test`, and
   confirm it passes. Report how many turns the restore took.

If no test went red, do not edit a test to make it fail. Report that the
suite missed the fault and name the check that would catch it.
