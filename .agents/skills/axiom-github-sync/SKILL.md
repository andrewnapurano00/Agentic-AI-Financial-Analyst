---
name: axiom-github-sync
description: "Commit and push authorized Axiom project changes to GitHub, checking change scope, verification, credentials and remote branch state. Use when asked to save or sync work to GitHub."
---

# Axiom GitHub Sync

An explicit request such as `Use $axiom-github-sync` means commit and push the intended current project changes. Proceed without redundant confirmation. Respect narrower instructions such as dry run, review only or commit only. Automatic skill selection alone does not authorize publishing.

## Inspect and verify

- Read AGENTS.md and inspect staged, unstaged and untracked changes. Preserve unrelated work and existing staging intent; stage explicit paths, not everything indiscriminately.
- Expected GitHub repository: `andrewnapurano00/Agentic-AI-Financial-Analyst`, remote `origin` via HTTPS or SSH. Verify the remote without changing it or exposing embedded credentials. Use the current branch and verified upstream; the normal branch is `main`. Ask a focused question if the repository differs or intended changes cannot be distinguished from unrelated work.
- Exclude `.env`, populated secrets, private portfolio data, caches and temporary artifacts. Inspect the intended diff for credentials without printing matched values. Do not force-add ignored files.
- Match validation to AGENTS.md: focused offline tests for behavior, full suite for shared infrastructure/routing, and import/health/browser checks as applicable. For skill/docs-only changes validate manifests, YAML, references and diff hygiene. Reuse previous checks only when their inputs are unchanged; retain their date/scope. Update PLAN for meaningful new deliveries without rewriting historical evidence.
- Report failed checks and their impact; do not publish known failures unless explicitly requested after disclosure. Do not consume paid credits or add unrelated fixes for a sync.

## Commit and push

1. Fetch the verified remote and compare HEAD with the upstream. If behind or diverged, inspect incoming commits. Do not automatically merge/rebase unrelated changes, discard work or force-push. Fast-forward only when working changes are safely preserved; explain conflicts or divergence needing a decision.
2. Stage only intended files, including any pre-existing staged changes only when in scope. Inspect `git diff --cached` and run `git diff --cached --check`. Choose a concise commit message describing the outcome.
3. Commit, then check its exit status before pushing. Do not amend or bypass hooks without explicit instructions. With no changes, skip an empty commit; inspect any authorized unpushed commits before publishing them.
4. Push normally to the verified branch, e.g. `git push origin main` when current branch/upstream is main. Do not publish additional branches/tags. Inspect a rejected push rather than forcing a retry.
5. Verify the remote SHA equals local HEAD and inspect final working-tree status. Report branch, commit link, included work, validation and remaining local changes. Source synchronization does not prove app deployment.

If authentication, hooks, tests or protection rules block completion, preserve work and report the blocker and whether a local commit exists. Use normal Git credential-manager/GitHub sign-in; never request tokens in chat, change repository permissions or disable protection to bypass rejection. Do not switch branches, create PRs or modify remotes unless the user requests that scope.
