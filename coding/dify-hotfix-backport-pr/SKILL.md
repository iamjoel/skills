---
name: dify-hotfix-backport-pr
description: Create Dify upstream hotfix branches and same-repository backport PRs. Use when the user gives a target hotfix branch such as `hotfix/1.15.0-fix.4` and a source commit to cherry-pick, asks to backport a main commit into a Dify hotfix release branch, or asks to repair an existing upstream hotfix cherry-pick PR.
---

# Dify Hotfix Backport PR

## Scope

Use this in `/Users/hejl/projects/dify` for hotfix backports from `myori/main` into
`langgenius/dify:hotfix/<version>-fix.N`. Push the PR branch directly to
`langgenius/dify` through `myori`; never push it to the `hjlarry/dify` fork.

Local assumptions for this checkout:

- `myori` is upstream `langgenius/dify`.
- Hotfix PRs use `myori/<target-hotfix-branch>` as the base and an upstream branch with the same name as the local PR branch as the head.
- `.github/scripts/check-hotfix-cherry-picks.sh` requires both the `(cherry picked from commit <sha>)` line and a source SHA reachable from `myori/main`.

## Required Inputs

Require these before acting:

- Target branch, for example `hotfix/1.15.0-fix.4`.
- Source commit SHA from `myori/main`.

If the source SHA is not reachable from `myori/main`, stop and ask for the final main commit SHA. Do not open a hotfix PR from a fork-only or PR-branch-only source commit, because the hotfix provenance check will fail.

## Workflow

1. Read repo instructions before touching files:

```bash
sed -n '1,220p' AGENTS.md
```

If the cherry-pick touches `api/`, read `api/AGENTS.md`; if it touches `web/`, read `web/AGENTS.md`.

2. Confirm worktree and remotes:

```bash
git status --short --branch
git remote -v
gh --version
gh auth status
```

If the worktree has unrelated changes, do not reset or stage them. Ask before proceeding.

3. Fetch the refs needed for branch creation and provenance:

```bash
git fetch myori '+refs/heads/main:refs/remotes/myori/main' '+refs/heads/hotfix/*:refs/remotes/myori/hotfix/*'
```

4. Derive the previous hotfix branch from the target:

```bash
python3 /Users/hejl/.codex/skills/dify-hotfix-backport-pr/scripts/derive_previous_hotfix_branch.py hotfix/1.15.0-fix.4
```

For `hotfix/1.15.0-fix.4`, this returns `hotfix/1.15.0-fix.3`. If the target is `fix.0`, stop and ask for the correct base tag or branch.

5. Ensure the upstream target branch exists.

If `myori/<target>` already exists, use it as the PR base. If it does not exist, create it from the exact tip of `myori/<previous>`:

```bash
base_sha="$(git rev-parse myori/hotfix/1.15.0-fix.3)"
git push myori "${base_sha}:refs/heads/hotfix/1.15.0-fix.4"
git fetch myori 'hotfix/1.15.0-fix.4:refs/remotes/myori/hotfix/1.15.0-fix.4'
git rev-parse myori/hotfix/1.15.0-fix.4
```

Never create the upstream hotfix branch from the current feature branch or from the source commit.

6. Verify the source commit is valid for hotfix provenance:

```bash
git cat-file -t <source-sha>
git show --no-patch --format='%H%n%P%n%s%n%b' <source-sha>
git merge-base --is-ancestor <source-sha> myori/main
```

Only continue if `merge-base --is-ancestor` exits 0.

7. Create or repair the PR branch.

For a new PR branch, use a short descriptive name under `agent/`, for example:

```bash
git switch -c agent/hotfix-1.15.0-fix.4-rbac-editor-member myori/hotfix/1.15.0-fix.4
git cherry-pick -x <source-sha>
```

For an existing PR branch repair, switch to the existing branch, reset to the hotfix base, then re-cherry-pick the main-reachable source commit:

```bash
git switch <existing-pr-branch>
git reset --hard myori/hotfix/1.15.0-fix.4
git cherry-pick -x <source-sha>
```

If there are conflicts, preserve the incoming source commit's intent while adapting to the older hotfix code shape. Stage resolved files before `git cherry-pick --continue`.

8. Validate before pushing.

Always run the hotfix provenance check:

```bash
BASE_SHA=myori/hotfix/1.15.0-fix.4 HEAD_SHA=HEAD MAIN_REF=myori/main \
  bash .github/scripts/check-hotfix-cherry-picks.sh
```

Run focused tests for touched areas. Examples:

```bash
DEBUG=false uv run --project api pytest api/tests/unit_tests/services/enterprise/test_rbac_service.py
pnpm -C web type-check
pnpm -C web test <focused-test-file>
```

Prefer targeted tests over broad suites unless the change's blast radius requires more.

9. Push the PR branch directly to upstream.

Never push the PR branch to `origin` or `hjlarry/dify`.

For a new PR branch:

```bash
branch="$(git branch --show-current)"
git push -u myori "HEAD:refs/heads/${branch}"
```

For an existing branch rewrite, fetch its current upstream SHA and use an explicit lease:

```bash
branch="$(git branch --show-current)"
git fetch myori "refs/heads/${branch}:refs/remotes/myori/${branch}"
remote_sha="$(git rev-parse "refs/remotes/myori/${branch}")"
git push --force-with-lease="refs/heads/${branch}:${remote_sha}" myori "HEAD:refs/heads/${branch}"
```

10. Create or update the PR.

Create a draft PR against the upstream hotfix branch. Because the head branch is in the same repository, pass the branch name without a fork owner:

```bash
gh pr create \
  --repo langgenius/dify \
  --draft \
  --base hotfix/1.15.0-fix.4 \
  --head "$(git branch --show-current)" \
  --title "<commit subject>" \
  --body-file /tmp/dify-hotfix-pr-body.md
```

For an existing PR, update the body with the actual source SHA, checks run, and results:

```bash
gh pr edit <number> --repo langgenius/dify --body-file /tmp/dify-hotfix-pr-body.md
```

After edits, verify and preserve draft state if the PR was intended to stay draft:

```bash
gh pr view <number> --repo langgenius/dify --json isDraft,mergeable,commits,url
gh pr ready <number> --repo langgenius/dify --undo
```

Only run `gh pr ready --undo` when the PR should be draft and GitHub reports `isDraft: false`.

## PR Body Shape

Use concise Markdown:

```markdown
## Summary

Cherry-picks `<source-sha>` onto `<target-branch>`.

<One sentence explaining the behavior being backported.>

## Validation

- `<hotfix provenance command>` -> verified 1 PR commit includes cherry-pick provenance from main
- `<focused test command>` -> <result>
```

## Final Response

Report:

- Upstream target branch and base SHA.
- Source SHA and generated hotfix commit SHA.
- Upstream PR branch and PR URL.
- Whether the PR is draft and mergeable.
- Confirmation that the fork was not used.
- Exact validation commands and results.
- Any blockers, especially source commits not reachable from `myori/main`.
