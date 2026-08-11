# Project Instructions

- Read `SPEC.md` before planning or implementing changes.
- Treat its acceptance criteria as the definition of completion.
- Implement changes on a dedicated Git branch.
- Add or update tests appropriate to the changed behavior, and run functional end-to-end tests against affected acceptance criteria. For documentation-only changes, run formatting and consistency validation instead.
- Run all relevant validation before opening a pull request.
- Do not open a pull request if validation fails.
- After validation passes, commit the changes, push the dedicated branch, and open or update the application pull request without waiting for routine conversational approval.
- Treat the pull request as the sole human approval gate: include the validation results, and never merge it automatically.

## Global Harness Improvements

- Treat this application as a workload for identifying reusable improvements to the global Codex harness, including its `AGENTS.md`, skills, tools, permissions, validation, tracing, and instructions.
- Propose a global change only when application work provides concrete evidence of a reusable improvement; do not promote one-off preferences or speculative ideas into the global harness.
- When an improvement belongs in the global harness rather than this application, immediately use the global `harness-improvement` skill. Do not implement the global change in this repository or ask for routine conversational approval.
- Follow that skill through proposal creation and launch of the dedicated harness-builder agent as a separate workstream. Continue the current application task unless the harness limitation blocks safe completion or creates material risk.
- The builder must validate the change and open or reuse the global harness pull request as the sole human approval gate.
- Never merge, activate, or install the global change. Report the builder's branch, commit, pull request, validation, risks, and diff to Pascal.
