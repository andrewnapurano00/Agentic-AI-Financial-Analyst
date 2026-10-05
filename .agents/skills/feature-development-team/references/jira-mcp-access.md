# Jira through the working local MCP bridge

Read this when checking Jira access or publishing feature-team tickets. Prefer native Atlassian MCP tools when exposed; otherwise call the same MCP server through the local stdio helper. This is MCP access, not a browser or a separate Jira REST integration.

## Local connection

Default site: `https://bigmeatpete717.atlassian.net`; project: `AAFA`. Honor the user's selected alternative.

On this Windows workstation, resolve the bridge directory as `Path.home() / '.codex/mcp/atlassian'`:

- `bridge.mjs`: pinned `mcp-remote` bridge to `https://mcp.atlassian.com/v2/mcp`.
- `check.py`: MCP initialize, tools/list, tool schema inspection and single tool invocation.
- `README.md`: local setup, dependency reinstall and troubleshooting notes.

The Codex `mcp_servers.atlassian` entry runs Node with `--use-system-ca` and `bridge.mjs`. The bridge enables Undici `allowH2: true`. Norton Web/Mail Shield intercepts HTTPS on this workstation: Windows certificate trust resolves Node's certificate error, while HTTP/2 avoids the observed malformed HTTP/1.1 chunk framing. Certificate verification remains enabled. Do not disable TLS verification, change Norton settings, inspect token stores or rebuild authentication simply because Codex reports `auth_status: unsupported` for stdio.

If these local files are absent on another workstation, use that environment's native tools or report the missing bridge. Do not install dependencies or change global configuration as an implicit part of a feature run.

## Check access and schemas

These are read-only checks; they do not consume the creation-attempt budget:

```powershell
python "$env:USERPROFILE/.codex/mcp/atlassian/check.py"
python "$env:USERPROFILE/.codex/mcp/atlassian/check.py" --describe discover
python "$env:USERPROFILE/.codex/mcp/atlassian/check.py" --describe executeRead
python "$env:USERPROFILE/.codex/mcp/atlassian/check.py" --describe createJiraIssue
```

Do not print the entire tool catalog when one schema suffices. A connection returning tools is not proof of project permissions. Use `discover` to obtain operation names and input requirements, then `executeRead` for project metadata and permissions. The verified operation `listJiraProjects` accepts `action: create` to filter projects by creation permission; `listJiraProjectIssueTypesMetadata` accepts `projectIdOrKey`. Recheck their current contracts before relying on them. Pass the selected site URL as `cloudId` where supported; resolve resources if the current schema requires an actual cloud UUID. Do not silently use another site.

Use live schemas for `createJiraIssue`, issue fields and duplicate searches. For v2 operations not in tools/list, discover the exact operation and use its advertised executeRead/executeWrite/executeDestructive routing. Never guess operation names or use a write to test access.

## Pass payloads without shell quoting failures

PowerShell may strip quotes from inline JSON passed to native programs. Serialize the arguments in Python and pass a subprocess argument list. For example, this discovers project-listing metadata only:

```powershell
@'
import json, subprocess, sys
from pathlib import Path
helper = Path.home() / '.codex/mcp/atlassian/check.py'
arguments = {'query': 'list jira projects'}
subprocess.run(
    [sys.executable, '-u', str(helper), '--tool', 'discover',
     '--arguments', json.dumps(arguments)], check=True,
)
'@ | python -
```

For publication, load the coordinator's saved, verified UTF-8 JSON payload with `json.loads(Path(payload_path).read_text(encoding='utf-8'))` and use the same subprocess pattern with `--tool createJiraIssue`. The payload has `cloudId`, `projectKey`, `summary`, `issueType` and the verified description/fields. Do not rewrite the payload during execution. The helper can invoke writes despite its diagnostic name: only issue an authorized create after duplicate checks and the coordinator's durable pending-ledger acknowledgment. Editing this skill does not authorize a create.

Check both the process exit code and MCP result: the helper can exit zero when a tool returns `isError: true`. Its tool-call output contains MCP `content` blocks; text blocks often contain a second JSON object, with the created key at `data.key`. Parse the result, require `isError` to be absent/false and a confirmed issue key, then form the link from the verified site plus `/browse/<key>`. A handshake, zero exit code or successful tools/list alone never establishes creation.

Invoke sequentially. Failed, interrupted or timed-out create calls consume an attempt. Reconcile uncertain outcomes by searching run/item identifiers and matching evidence; never rerun a create merely because output was missing or parsing failed. Preserve the original five-attempt cap, snapshot checks and report ledger regardless of native tools versus direct stdio.

## Evidence and limits

On October 4, 2026, the local bridge completed initialize and tools/list (21 tools), listed all three Jira projects, read AAFA issue types, and created [AAFA-4](https://bigmeatpete717.atlassian.net/browse/AAFA-4) on the user's explicit request. This is historical connection/write evidence, not permission to create another test ticket or proof that a future session is authenticated. If access fails, report the actual failure and retain drafts; do not prescribe repeated client restarts when direct stdio can be tested.
