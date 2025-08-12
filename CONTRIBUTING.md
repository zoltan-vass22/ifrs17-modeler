# Contributing Guidelines

## Branching model
- `main`: release-ready only.
- `dev`: integration branch for all features.
- `feature/*`: one feature per branch (short-lived).
- `hotfix/*`: urgent fixes based off `main`.

### One-time setup
```bash
git switch main
git pull --ff-only
git switch -c dev
git push -u origin dev
```
> (Optional) Protect `main` and `dev` in GitHub → Settings → Branches.

---

## Start a feature
```bash
git fetch --all --prune
git switch dev
git pull --ff-only
git switch -c feature/<short-descriptive-name>
```

### Commit style (Conventional Commits)
```
<type>(scope): short imperative summary

[body – why, not what]
[footer – breaking changes, issue refs]
```
Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`, `build`, `ci`.  
Scopes: `engine`, `contracts`, `assumptions`, `results`, `reporting`, `runs`, `common`, `config`.

**Examples**
- `feat(engine): add CSM release by coverage units`
- `feat(results): add RollforwardLine model (migrations)`
- `test(engine): reproduce IFRS IE4 numbers`
- `docs(readme): add architecture diagram`

### Django models & migrations
- When models change:
  ```bash
  python manage.py makemigrations
  git add .
  git commit -m "feat(results): add PLLine model (migrations)"
  ```
- Keep models + migrations in the **same commit**.

---

## Open a Pull Request (PR → `dev`)
```bash
git push -u origin feature/<short-descriptive-name>
```
On GitHub:
- Base: `dev`, Compare: your feature branch.
- Link issue(s): `Closes #123`.
- Fill the PR template (test plan, screenshots if UI).

### Keep branch fresh
```bash
git fetch origin
git rebase origin/dev
# resolve conflicts
git add <files>
git rebase --continue
git push --force-with-lease
```
> Only rebase your own feature branches. Never rebase `main`/`dev`.

---

## Merge & cleanup
- Prefer **Squash & merge** for one commit on `dev` (or **Rebase & merge** to keep history).
- Delete the branch after merge.
- Local cleanup:
  ```bash
  git switch dev
  git pull --ff-only
  git branch -d feature/<short-descriptive-name>
  git fetch --prune
  ```

---

## Release flow (`dev` → `main`)
```bash
git switch dev && git pull --ff-only
git switch main
git merge --ff-only dev
git push
git tag -a v0.1.0 -m "MVP scaffold"
git push --tags
```

## Hotfix flow
```bash
git switch main && git pull --ff-only
git switch -c hotfix/<fix-name>
# implement, test, commit
git push -u origin hotfix/<fix-name>
# PR → main, merge
git switch dev && git pull --ff-only
git merge --ff-only main
git push
```

---

## Testing, style & tooling (recommended)
- Tests live under the app (e.g., `engine/tests/`).
- Add minimal smoke tests for engine math and reporting queries.
- Consider pre-commit hooks:
  - `black`, `isort`, `flake8` (or `ruff`) before each commit.
- Keep `.env`, `.venv`, SQLite DB out of Git (see `.gitignore`).

---

## PR checklist
- [ ] Feature is scoped and documented.
- [ ] Models + migrations included (if applicable).
- [ ] Tests added/updated and pass locally.
- [ ] README/docs updated if behavior/UI changed.
- [ ] Screenshots for reporting changes (when UI lands).

---

## Security & secrets
- Never commit secrets or production DBs.
- Use a local `.env` (ignored by Git).

---

## Versioning
- Semantic tags: `vMAJOR.MINOR.PATCH`.
- Tag meaningful milestones (e.g., reproducing IFRS 17 IE table in tests).

---

### Contact
Open a GitHub issue for questions or to propose larger changes.

---

## Optional: `.gitattributes`
Add this to normalize line endings:
```
* text=auto
```

---

## Optional: CI (later)
Add GitHub Actions to run tests and linters on PRs to `dev`.

---

## Optional: PR Template

Create `.github/pull_request_template.md`:

```markdown
## Summary
<!-- What does this change do? Why? -->

## Type
- [ ] feat
- [ ] fix
- [ ] refactor
- [ ] docs
- [ ] test
- [ ] chore

## Scope
- [ ] engine
- [ ] contracts
- [ ] assumptions
- [ ] results
- [ ] reporting
- [ ] runs
- [ ] common
- [ ] config

## Changes
- Bullet list of key changes

## Tests
- How did you test? Include commands, data, and results.

## Screenshots (if UI)
<!-- attach before/after -->

## Risks / Rollback
- Risks, fallback plan.

## Links
Closes #<issue-id>
```
