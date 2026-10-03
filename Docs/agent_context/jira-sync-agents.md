# `jira-sync` Agent Context

Use `jira-sync` to synchronize Jira Cloud issues from local Markdown files. Markdown is the desired source of truth; the tool does not pull Jira edits back into files.

## Safe Operating Workflow

Run commands in this order:

```bash
jira-sync validate <ticket-path> --json
jira-sync plan <ticket-path> --json
jira-sync push <ticket-path> --yes --json
```

If the repository contains `.ai-tools.toml` with `jira.ticket_directory`, `<ticket-path>` may be omitted.

1. Run `validate --json`. This is local and does not contact Jira. Stop if the exit code is nonzero or `valid` is `false`.
2. Run online `plan --json`. Planning reads Jira but changes neither Jira nor local files. Inspect `summary` and every item’s `action`, `reason`, and `changed_fields`.
3. Report the numbers of `CREATE`, `UPDATE`, and `NOOP` actions. Call out unexpected creations, parent changes, or large update sets.
4. Obtain explicit user authorization before executing `push`. A user request that clearly says to push or apply the reviewed plan is sufficient authorization.
5. Run `push --yes --json`. The `--yes` flag is mandatory with JSON output because interactive prompts would corrupt stdout.
6. Report created/updated Jira keys and any errors. Never retry a partially failed push without planning again.

Use offline planning only when Jira access is unavailable:

```bash
jira-sync plan <ticket-path> --offline --json
```

Offline mode cannot compare Jira state. It conservatively reports every ticket containing `jira_key` as `UPDATE`; do not treat this as evidence that Jira differs.

## Actions and Idempotency

- `CREATE`: no `jira_key` exists. A successful push creates the issue and normally writes its assigned key into the Markdown front matter.
- `UPDATE`: managed local fields differ from Jira. Online JSON plans list exact `changed_fields`, and push sends only those fields.
- `NOOP`: all managed fields match. Push skips the issue.

Do not remove a written-back `jira_key`; doing so can create a duplicate issue. Parent/child creation order is resolved through stable local `id` values.

## Ticket Format

Each ticket is Markdown with optional YAML front matter and an H1 summary. Recommended metadata:

```yaml
---
id: stable-local-id
project: ENG
type: Task
parent: parent-local-id
priority: High
labels: [example]
---
```

Supported keys include `id`, `jira_key`, `project`, `type`/`issue_type`, `summary`/`title`, `labels`, `priority`, `parent`, `assignee_account_id`, and `fields`. Put Jira custom fields under `fields` using their field IDs. Other top-level front-matter keys are treated as Jira fields, so do not invent metadata keys casually.

## Configuration and Credentials

Project defaults belong in `.ai-tools.toml`:

```toml
[jira]
project = "ENG"
ticket_directory = "Docs/Tickets/Jira"
```

Credentials use `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN`. They may come from the process environment or an ignored `.env` loaded through `python-dotenv`. Never display, log, edit, or commit credentials. Real process variables take precedence over `.env` values.

## Limits and Error Handling

Trust the process exit code before parsing output. Validation failures exit `1`; configuration, Jira, and synchronization failures are also nonzero. A push is not transactional: earlier issues may have succeeded before a later failure.

The tool does not currently synchronize workflow status, delete Jira issues, pull Jira changes, create dependency links from prose such as `Depends on`, or manage attachments and comments. Estimates and milestones require explicit Jira custom-field mappings.

For complete human-oriented reference material, see [`../jira-sync.md`](../jira-sync.md).
