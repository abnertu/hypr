# AGENTS Instructions

Preserve bindings and their actions. Keep deployed configuration read-only and runtime state outside its source tree.

## Git

- Write commits in [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) format.
- Start the type, the scope and the description in lowercase. Keep the case of code identifiers and proper nouns.
- For a non-trivial change, write a commit body that explains why.
- Mark a breaking change with `!` and a `BREAKING CHANGE:` footer.
- Author commits as the user alone. Add no agent trailers or links, such as `Co-Authored-By` or a session URL.
- Commit as the plan progresses.
- Before you push, squash related commits into one commit to keep the history clean.
- Push only after the user approves that push.
- Keep plans, diagnostic logs and throwaway test output outside the repo.
- Resolve the complete deployment symlink chain before you update a checkout. A Nix store link can point back to a live checkout.
- Complete refactors in an isolated worktree before you update the live tree.
- Suspend automatic reload during a multi-file live update.
- Reload the complete tree after the update.
- Update the live tree only after the pushed commit passes CI.

## Releases

- Version releases with [Semantic Versioning 2.0.0](https://semver.org/).
- Name each release tag with the bare version, such as `1.2.3`. If the repo already uses a tag prefix, such as `v`, keep it.
- When you create a changelog, use [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format. Keep the format of an existing changelog.
- Release in this order:
  1. Update the version files and the changelog in one commit, such as `chore(release): prepare 1.2.3`.
  2. Push the commit to the default branch.
  3. Wait until the branch pipeline of that commit passes.
  4. Tag that commit with an annotated tag: `git tag -a 1.2.3 -m "Release 1.2.3" <commit>`. Tag a release candidate as `1.2.3-rc.1`.
  5. Push the tag alone: `git push origin 1.2.3`. The tag pipeline publishes the package and creates the release.
- Push the commit and the tag in separate pushes. Do not use `git push --follow-tags`. One push starts two overlapping pipelines, and a single runner queues the tag pipeline.

## Runtime contracts

- Give each application one startup owner. Session managers or user services own session applications.
- Keep autostart declarations for compositor-owned work. Remove duplicate startup declarations when ownership moves.
- Keep shared shell and terminal settings in the user environment configuration.
- Keep Noctalia theme changes in its templates.
- Write runtime files under `ctx.state_dir`, never under `ctx.config_dir`.
- Keep helper declarations in TOML and validate them through `hyprconf.config`.
- Keep TOML declarations within the subset that the reader supports: single-line strings, numbers, booleans, arrays, tables and array tables.
- Preserve JSON null positions and reject malformed native replies.
- Keep command execution outside compositor configuration loading.
- Use the checked process adapter for synchronous native helper operations.
- Quote arguments with `shell.quote` when a trusted command needs a shell.
- Keep each mutating operation under the shared lock.
- Preserve saved state when runtime application fails.
- Report failed recovery separately from the original failure.
- Treat notifications and screenshot sounds as optional feedback.
- Keep successful screenshot publication when clipboard copying fails.
- Store profile names rather than copied profile files.
- Keep the first-line profile label for menus.
- Keep the ignored `monitors.conf` and `workspaces.conf` files outside configuration loading.

## Lua contracts

- Keep compositor and helper contexts separate. Helpers reach Hyprland through `runtime.hyprctl`.
- Import each owner directly. Add an abstraction only to remove real duplication.
- Use the installed Hyprland stubs for annotations.
- Use `HL.*` types for values passed into Hyprland.
- Annotate parsed TOML and JSON structures at their consumers.
- Keep `mouse = true` bind fields, although `HL.BindOptions` does not declare them.
- Change those fields only with an intentional binding change.

## Tests

- Add a test to the repo only when it guards behavior that no existing test covers.
- The test must fail when that behavior breaks. Weigh this before you add each test.
- Run throwaway tests freely to check your work.
- Keep throwaway tests out of the repo unless they meet the bar above.
- Keep keymap compatibility in the frozen snapshot and callback probes.
- Use the synthetic Noctalia fixture instead of personal theme state.
- Test helpers through their CLI with temporary roots and fake native commands.
- Parse shipped profiles with native Hyprland in isolated roots.
- Reject process execution while loading the real configuration entry point.
- Test behavior rather than copied option inventories or source text.
- Run `just all` before you finish.
- Add each new check as a `just` recipe that `check` runs.
- Verify real menus, portals and hardware only in an authorized desktop session.
- Report unavailable checks and uncovered contracts.

## CI

- Keep a CI check only when it catches a concrete failure that no existing check covers.
- Identify that failure before you add or keep the check.
- Apply the test rules to CI checks too.
- Run the repo's entry points against real inputs or isolated fixtures.
- Reject duplicate checks, source-text assertions, copied inventories and checks that only prove that a command or file exists.
- Name each workflow, job and step by its target and its action.
- Name CI files in kebab-case by purpose, such as `deploy-production.yml`.
- Keep reserved host filenames, including `.gitlab-ci.yml`.
- Name workflows in Title Case, such as `Deploy Production`.
- Keep the repository name out of workflow names.
- Name the workflow that validates the whole repository by its action alone, such as `Validate`.
- Name job IDs in snake_case, such as `build_image`.
- Start each GitHub step name with a verb, such as `Install Dependencies` or `Run Tests`.
- Preserve proper nouns and code identifiers when you apply case.
- Prefer a specific purpose, such as `deploy-production.yml`, over a vague name, such as `production.yml`.
- Omit redundant host or artifact words, as in `github-action-build.yml` and `build-workflow.yml`.
- Keep job display names unique within the repository.
- When you rename a CI artifact, update its dispatch references, dependencies, release gates, required check contexts and badges together.
- Propagate command failures.
- Count a missing prerequisite or skipped required coverage as a failure.
- Run the checks in branch and pull request pipelines, never in tag pipelines. A tag pipeline builds, smoke-tests and publishes the package, and then creates the release.
- Start each release job with a check that the tagged commit is on the default branch.
- Match release jobs to the tag format of the version, such as `/^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$/`.
- Protect the release tags. Only protected refs can read the release credentials.
- A tag pipeline uses the CI config of the tagged commit. Merge a CI change to the default branch before you tag.
- Run the checks in a workflow on `pull_request` and on `push` to branches.
- Run the release in a separate workflow on `push` of tags that match the version format. GitHub tag filters are globs, such as `[0-9]+.[0-9]+.[0-9]+` and `[0-9]+.[0-9]+.[0-9]+-*`.
- Check out release jobs with `fetch-depth: 0`, so that the ancestry check sees the default branch.
- Keep release secrets in an environment that allows only the release tags. Protect the tags with a tag ruleset.
- After you change these rules, audit the repo against them.
- Validate changes locally. Then verify the required CI on the pushed commit.
- Report each uncovered contract and each unavailable check.

## Docs

- Keep each doc concise and plain. Each sentence must carry information.
- Write only standing rules in `AGENTS.md`. A standing rule changes how an agent does later, unrelated tasks.
- Record a fact about one place or one failure at its source: a code comment, a test, a commit body, an ADR or an issue.
- Keep operator procedures in the README and contributor constraints here.
- Write English docs in US English, to the [ASD-STE100](https://www.asd-ste100.org/) writing rules:
  - Give one instruction in each sentence.
  - Write instructions in the imperative and in the active voice.
  - Use one word for one meaning, and one meaning for one word.
  - An instruction has 20 words or fewer. A description has 25 words or fewer.
- Review each sentence over these limits. Split it if it holds more than one instruction or fact.
- Use a numbered list for three or more instructions in a fixed order, also across sentences.
- Write a set of full-sentence items, or of more than five items, as a bullet list. Otherwise, the set can stay in one sentence, even when the sentence is over the limits.
- Write a non-English doc in two passes:
  1. Write an English draft to these rules.
  2. Translate the draft:
     1. Keep its sentence boundaries and one term for each concept.
     2. Keep commands, paths and code unchanged.
     3. Use the natural word order of the target language.
