# Agent Configuration

This file configures how agent skills interact with this repository.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for this repo (`gongyijie85/ai-food-scanner`). Use the `gh` CLI to create, list, and update issues. External PRs are not treated as a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: domain language lives in `CONTEXT.md` at the repo root, and architectural decisions live in `docs/adr/`. See `docs/agents/domain.md`.
