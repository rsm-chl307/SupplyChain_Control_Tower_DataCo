# Windows Host API Runner

The deployed legacy CLI and background Worker support **Input Token Count** only. The one-request count CLI requires manual `EXECUTE`; the opt-in count Worker uses a Windows-local policy. The new, separate Generation handoff below has not been deployed or enabled on Windows. Arbitrary HTTP destinations remain unsupported.

In this source revision, `REAL_TOKEN_COUNT_DISPATCH_LOCKED = True` blocks the
real count transport before credential access. The manual and Worker flows
below describe the future separately authorized operation; Fake transports
remain available for offline qualification.

## Versioned P5 Generation handoff (WP3, local implementation)

Generation is a separate **manual** operation in `generation_host.py`. It does not
change the count-only Runner, Worker, package schemas, or Auto-Run policy. The
Generation CLI is not installed or activated on Windows by this code change.
The real Host transport is additionally blocked by
`REAL_GENERATION_DISPATCH_LOCKED = True`; the handoff below describes the
future authorized flow and cannot be used for a paid call in this revision.
The pinned `cryptography` dependency in `requirements-generation.txt` and native
Windows behavior require separate deployment verification.

The Host Owner verifier and Host Ed25519 signing seed are separate Generic
Credentials in the interactive Windows account. The OpenAI credential remains
in its original Credential Manager target. Initial setup, performed only after
separate deployment approval, uses hidden input for the Owner verifier:

```powershell
py -3 -m tools.windows_api_runner.generation_owner
py -3 -m tools.windows_api_runner.generation_key_setup
```

`generation_key_setup` refuses to overwrite an existing Host signing key and
exports only its public key to
`%LOCALAPPDATA%\SupplyChainCopilot\generation_owner_public.bin`.
The Container pins that public key outside the repository at the path used by
`HOST_OWNER_PUBLIC_KEY_PATH`. The P5 issuer private key is a **different** key,
stored outside the repository; `generation_issuer_setup` exports only its public
key to a chosen location. The Host pins that P5 issuer public key at
`%LOCALAPPDATA%\SupplyChainCopilot\p5_issuer_public.bin`. Never copy either
private key across the Container/Host boundary or into the exchange.

The approved handoff has two machine stages and one Owner password entry:

1. The Container retains the live trusted Run/Brief/ProviderRequest, verifies
   exact count evidence, paid authorization and budget, appends Archive Intent,
   and writes a signed `generation/proposals/<UUID>.json`.
2. Copy that proposal to the matching Windows namespace exchange. On the Host,
   `py -3 -m tools.windows_api_runner.generation_host authorize <proposal-path>
   --exchange <namespace-host-exchange>` verifies the pinned issuer signature,
   displays the exact request and accepts one hidden Owner password. It writes
   `generation/authorizations/<UUID>.json` containing only a short-lived signed
   authorization. Copy this proof back to the Container.
3. The Container verifies the Host signature and live P5 state, atomically burns
   the one-use Ledger claim, and writes a P5-signed
   `generation/requests/<UUID>.json` permit package. Copy it to Windows.
4. On the Host, `py -3 -m tools.windows_api_runner.generation_host dispatch
   <request-path> --exchange <namespace-host-exchange>` verifies the Proposal,
   Owner authorization and final Permit against pinned keys, then durably claims
   the one-use Host state before one fixed `/v1/responses` request. It does not
   ask for `EXECUTE` or a second confirmation. Copy the signed response package
   back to the Container for P1, evidence and Archive collection.

The Host trusts the P5 issuer signature only after the Container's claim
transaction completes. A missing or uncertain Host response, interrupted
dispatch or Archive failure must be reconciled under its original UUID. No
automatic retry or replacement UUID is allowed. Usage is response metadata;
actual charge remains null until separate authoritative billing evidence is
reconciled. The Real Provider lock and count Auto-Run policy stay unchanged.
WP4 sequential coordination, Windows deployment and real API execution require
separate authorization.

## Host requirements

- Windows 10/11 and Python 3.10+ on the Windows host.
- Count-only Runner: standard library only. The separately deployed Generation
  CLI requires the pinned `cryptography` version in `requirements-generation.txt`.
- An OpenAI credential stored as a Generic Credential in the current Windows user's Credential Manager with target name `SupplyChainCopilot/OpenAI`.
- A fresh, rotated credential if any prior credential was exposed. Do not reuse the previously exposed key.

After revoking any exposed credential, provision the rotated value with a hidden interactive prompt (no secret command-line arguments):

```powershell
py -3 -m tools.windows_api_runner.store_credential
```

The tool writes the UTF-8 credential blob to the current Windows user's Credential Manager Generic Credential target `SupplyChainCopilot/OpenAI`; it prints only the target name. Never put the secret in a shell command, environment variable, repository file, Docker mount, or request package. The manual CLI reads this credential only after confirmation. The background Worker reads it only after the Windows-local Auto-Run Policy accepts a request.

Boolean availability check (prints only `PRESENT` or `MISSING`):

```powershell
py -3 -m tools.windows_api_runner.verify_credential
```

## Background Worker (Local Testing MVP)

The Worker runs on Windows and uses the Docker CLI to copy only request and response packages between the existing Container and the Windows-local exchange. It does not use a bind mount, recreate the Container, or send credentials through Docker. Fixed defaults are Container `codex-sandbox-lab-005`, Container exchange `/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange`, and Windows exchange `C:\SupplyChainCopilot\api_exchange`. Runner state, policy, and logs remain under `%LOCALAPPDATA%\SupplyChainCopilot`, outside the exchange.

The repository deployment entry point is `deploy_runner.ps1`. It validates the running Container, repository/exchange paths, current limited Task Scheduler action, Worker state, and disabled Auto-Run policy before staging. It copies exactly the files listed in `source-manifest.json`, verifies SHA-256 before and after installation, backs up the prior Runner package and Task XML, and uses the SQLite online backup API for an existing Runner state database (including committed WAL data). An incompatible state schema stops deployment without migration. It does not copy Credential Manager content or exchange requests/responses. The deployment script does not require the optional parent `tools\__init__.py` namespace-package marker.

For WP3.5-A **Generation Native Fake Acceptance**, use `tmp/WP3_WINDOWS_NATIVE_FAKE_ACCEPTANCE.ps1`. When Generation files are missing, it calls `deploy_generation.ps1`, which stages and verifies only Generation components, preserves existing Count Worker files and SQLite, and does not start or stop the Count Worker Task. The Task may be `Ready`; its definition, limited interactive principal, and disabled Auto-Run policy are still checked. The older `deploy_runner.ps1` remains the complete Count Worker deployment path and still manages that Worker's lifecycle.

From a Windows PowerShell session with Docker Desktop CLI access, retrieve and run the formal script:

```powershell
$DeployScript = Join-Path $env:TEMP 'P5_WINDOWS_RUNNER_DEPLOY.ps1'
docker cp 'codex-sandbox-lab-005:/workspace/SupplyChain_Control_Tower_DataCo/tools/windows_api_runner/deploy_runner.ps1' $DeployScript
if ($LASTEXITCODE -ne 0) { throw 'Could not retrieve the deployment script.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DeployScript
```

The deployer captures the existing Task XML, then stops a verified running Worker only after staging and backups pass, and starts it after deployment. If installation fails after the directory switch, it restores the prior package and restarts a Worker that was running before deployment. The prior package remains under `%LOCALAPPDATA%\SupplyChainCopilot\backups\<deployment-id>\active_old_package`; inspect before using a manual rollback. The backup also contains the original package and, when present, Task XML, policy file and WAL-aware SQLite snapshot.

After verified file deployment, bootstrap registers the limited interactive Task only when none exists, or starts the already-verified Task. Missing Auto-Run policy remains absent (the Runner treats absence as disabled); an existing policy must already have `enabled: false` and is never rewritten. Status must report `Auto-run enabled: False`.

The checked-in manifest covers all deployable Runner files except itself and the complete Count Worker deployer, `deploy_runner.ps1`; it records that deployer's SHA-256 separately. `__pycache__` and runtime state are excluded. The staging copy and installed package are checked against that manifest. The script is PowerShell 5.1-compatible by construction; this has not been natively parsed or run in a Windows shell in the current environment.

For deployments where the Container is unavailable, copying/updating files manually is not supported; do not run the older temporary bootstrap script. Use the exact deployer above so the preflight, backup and complete-manifest checks run together.

The background Task bootstrap itself is:

```powershell
Set-Location C:\SupplyChainCopilot\runner
.\tools\windows_api_runner\bootstrap_worker.ps1
```

Bootstrap registers and starts a limited-privilege Task Scheduler task at user logon. It creates host-local exchange, state, and log directories. The installed policy is disabled by default, so the task does not poll Docker or access Credential Manager until a policy is explicitly enabled. The Worker can also be run interactively for local diagnostics with `py -3 -m tools.windows_api_runner.worker --once`; it still respects local policy.

The Task runs `worker_task.ps1`, which launches the existing Python Worker and appends stdout, stderr and timestamped start/exit code records under `%LOCALAPPDATA%\SupplyChainCopilot\logs` (`worker.stdout.log`, `worker.stderr.log`, `worker.lifecycle.log`). These logs survive package rollback. If the Task exits during deployment, the deployer reports `LastTaskResult` and the log paths. Do not place credentials or request payloads in Task arguments or logs.

The policy file is `%LOCALAPPDATA%\SupplyChainCopilot\auto_run_policy.json`. The checked-in template is disabled. To opt in, explicitly choose allowed Case IDs and a maximum request count per UTC day:

```powershell
.\tools\windows_api_runner\enable_auto_run.ps1 -AllowedCaseIds EV-01 -MaxRequestsPerUtcDay 1
```

This requires typing `ENABLE LOCAL INPUT TOKEN COUNT AUTO-RUN`. It is a local operator action; Docker cannot perform it. Disable the policy with `disable_auto_run.ps1`. Check task and policy status with `status_worker.ps1`; stop/start the task with `stop_worker.ps1` / `start_worker.ps1`.

Policy validation is host-side and strict: only `input_token_count`, `gpt-6-luna`, known P5 Case IDs, bounded request/payload bytes, and a bounded daily dispatch count are accepted. The Request Package cannot set or expand policy. This is a request-count and byte-size limit, not a dollar-spend guarantee or token estimate. The daily count includes dispatch claims left IN_PROGRESS or UNKNOWN. The Worker never retries a recorded UUID: after restart it only returns an existing response or marks an uncertain dispatch UNKNOWN.

The Worker uses the fixed API destination and existing response redaction. The API Key is read from Credential Manager only on Windows, held in Worker process memory for the API call, and never placed in Docker, logs, SQLite metadata, or Request/Response packages. Auto-Run is disabled unless the local policy is explicitly enabled.

### Automatic local workflow

In the Container, start the P5 local workflow once:

```bash
python -m src.ai_copilot.local_token_count_e2e --case EV-01
```

P5 prepares and displays the request UUID, model, digest, and Windows exchange path, then waits for the matching response. With the Worker task running and a matching enabled policy, the Worker polls the fixed Container request directory, validates the package and policy, executes at most once, and copies the response back. P5 then collects and validates it in the same process. There is no per-request `EXECUTE` prompt or manual `docker cp` in this opt-in mode. No real API execution occurs until the Windows owner has separately enabled a policy and the P5 workflow has been intentionally started.

If the process times out, is interrupted, a transport is uncertain, or response persistence fails, the original UUID remains UNKNOWN and is never retried. Inspect/reconcile that same identity; do not start a replacement workflow to bypass the lock. The Worker does not close P5 failures or UNKNOWN workflows. Confirmed HTTP 400 close-out remains an explicit operator action using preserved Request/Response evidence; this task does not reconcile historical EV-01.

## Exchange directories (legacy manual file-transfer mode)

The implementation uses the host path `C:\SupplyChainCopilot\api_exchange` as a suggested location. Create `requests` and `responses` directories there. No Docker or Compose configuration exists in this repository, so container paths and bind mounts must be connected by the deployment owner. Mount only the request directory read/write for the container and the response directory read-only for the container. Keep host execution state at `%LOCALAPPDATA%\SupplyChainCopilot\runner_state.sqlite3`; do not mount it into Docker.

Example PowerShell directory setup:

```powershell
New-Item -ItemType Directory -Force C:\SupplyChainCopilot\api_exchange\requests
New-Item -ItemType Directory -Force C:\SupplyChainCopilot\api_exchange\responses
```

The container should write each finished package as `requests/<request_id>.json` (write a temporary file and rename it when complete). It reads `responses/<request_id>.json` after the host runner creates it. Do not share the Credential Manager or runner-state database with the container.

### P5 exchange path without a bind mount

The P5 bridge's default Container-side exchange root is:

```text
/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange
```

The default is derived from the checked-out bridge module location. The P5 application can override it with the non-secret environment variable `P5_WINDOWS_RUNNER_EXCHANGE_PATH`, which must be an absolute Container path. The P5 integration entrypoints `prepare_configured_count_request()` and `collect_configured_count_response()` use this same configured path. Preparation creates both `requests` and `responses` directories. This local exchange path is inside the existing Container writable layer; it is not a bind mount and is not visible to Windows until files are copied.

With Docker Desktop CLI available in Windows PowerShell, these commands show the default-path transfer. Replace `<request-id>` with the UUID returned by P5 preparation. If `P5_WINDOWS_RUNNER_EXCHANGE_PATH` is set, replace `$ContainerExchange` with the exact Container path in the generated P5 handoff; do not use the default below. Keep the response under that same Container exchange root so collection can validate it against the original Run, Brief and payload.

```powershell
$ContainerName = 'codex-sandbox-lab-005'
$ContainerExchange = '/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange'
$RequestId = '<request-id>'
$HostExchange = 'C:\SupplyChainCopilot\api_exchange'

docker cp "${ContainerName}:$ContainerExchange/requests/$RequestId.json" "$HostExchange\requests\$RequestId.json"
py -3 -m tools.windows_api_runner.api_runner "$HostExchange\requests\$RequestId.json" --exchange $HostExchange
docker cp "$HostExchange\responses\$RequestId.json" "${ContainerName}:$ContainerExchange/responses/"
```

`docker cp` does not add a mount or recreate the Container. The Container name, Docker CLI access, and host folder permissions must be verified on the Windows host. Never copy the Runner state database or credentials into the Container.

## Request package

The package has a strict top-level schema in `request-package.schema.json`. The payload is the complete JSON body intended for the fixed Input Token Count endpoint. Its digest is SHA-256 over UTF-8 canonical JSON matching P5: sorted object keys, compact separators, JSON's default ASCII escaping, and non-finite numbers rejected. The payload model must equal the package model. Credential-like payload fields and key-shaped strings are rejected. P5 packages additionally carry all four `brief_digest`, `provider_request_digest`, `count_projection_digest`, and `run_manifest_sha256` values; they are copied unchanged into the response for cross-boundary identity checks.

Synthetic example (digest is valid for this exact payload):

```json
{
  "request_id": "00000000-0000-4000-8000-000000000001",
  "case_id": "EV-01",
  "run_id": "synthetic-run-001",
  "operation": "input_token_count",
  "model": "gpt-6-luna",
  "payload": {
    "input": "Synthetic EV-01 token-count fixture",
    "model": "gpt-6-luna",
    "store": false
  },
  "payload_digest": "09674b31bc0b6cd538385f50156e05ae6db2579f1b2c8aed41a7239d57c97909",
  "created_at": "2026-11-23T00:00:00Z"
}
```

## Run manually

From the repository root on Windows:

```powershell
py -3 -m tools.windows_api_runner.api_runner `
  C:\SupplyChainCopilot\api_exchange\requests\<request_id>.json `
  --exchange C:\SupplyChainCopilot\api_exchange
```

The runner prints the case, request ID, operation, model, digest, and fixed endpoint, then waits for the operator to type `EXECUTE`. Any other input is a pre-dispatch refusal. A fresh request package and new request ID require a fresh manual confirmation.

## State and recovery

State is stored on the Windows host, outside the Docker exchange. Request ID is unique; additionally, a case/run/operation/payload digest tuple can be executed at most once by this state store. `IN_PROGRESS`, `UNKNOWN`, and completed requests are never automatically retried. Any transport exception or response persistence failure is `UNKNOWN`; stop and reconcile using the host state, saved response if present, and OpenAI request ID if available. The implementation does not claim exactly-once external execution. A known HTTP error is recorded as `FAILED_AFTER_DISPATCH`, with its response package, and must not be automatically retried.

The Response Package schema is `response-package.schema.json`. It contains sanitized response content, HTTP status, request ID and model metadata when returned, usage when returned, timestamp, and runner status. Charge is not fabricated or inferred by this token-count runner.

## Security boundary

- Fixed destination: `https://api.openai.com/v1/responses/input_tokens`; redirects and environment proxies are disabled.
- The only operation is `input_token_count`; the only accepted model is `gpt-6-luna`.
- No arbitrary URL, command execution, service endpoint, or background process exists.
- The credential is retrieved from Windows Credential Manager after confirmation and is held only in process memory for the request. It is never added to Docker environment or package files.
- The state database is host-local and should remain outside all container mounts.
- A bind-mounted request/response directory is an exchange boundary, not a trusted store. The operator reviews the digest before execution.

## P5 Input Token Count handoff

`P5TokenCountOrchestrator` in `src/ai_copilot/p5_token_count_orchestrator.py` is the Docker-side caller for the count-only workflow. The surrounding P5 application must supply an already validated `ValidatedBrief` and its exact `ProviderRequest`; the orchestrator does not create Runs or business context.

The low-level caller API remains available for tests and explicit integrations. It uses this manual sequence:

1. Call `prepare(case_id, validated_brief, provider_request)` once. It writes one package through `prepare_configured_count_request()`, stores the exact UUID and Run/Brief/payload identities in a separate SQLite workflow file, and returns the existing `PreparedCountRequest`.
2. Call `create_windows_handoff(request_id)`. It validates the prepared package and returns a non-secret handoff record with the exact Container paths, Windows paths, `docker cp` commands, and manual Runner invocation. Present those commands to the operator. The method never launches Docker or the Windows Runner.
3. On Windows, review the displayed Case, UUID, model, and payload digest, then run the documented Runner command and confirm only by typing `EXECUTE` at its prompt.
4. Copy only the matching response package back to the recorded Container response path. A file appearing there is only a candidate response.
5. Call `mark_response_pending(request_id)`, then `collect_response(request_id, case_id, validated_brief, provider_request)`. Collection calls `collect_configured_count_response()` with the same context, then the existing `require_exact_token_count()` gate. Only successful validation transitions the workflow to `COLLECTED` and returns `ExactTokenCount` evidence.

The exchange root comes from `P5_WINDOWS_RUNNER_EXCHANGE_PATH` when configured; otherwise it is `/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange` in the current checkout. `create_windows_handoff()` derives the Docker copy commands from that configured root rather than assuming the default.

### Recovery and stop conditions

- The workflow state is stored at `<exchange-root>/.p5_token_count_workflow.sqlite3`, separate from the paid Ledger. It preserves the Request UUID and blocks preparation of another Case until the current Case is `COLLECTED`.
- If the process restarts, reopen the orchestrator with the same exchange and state paths. Reacquire the exact original validated Brief and ProviderRequest before collection; the bridge reloads the existing request package and recomputes its Run and payload identity. If that context cannot be recovered, stop without creating a replacement UUID.
- If no response file has arrived, leave the request pending and wait for operator reconciliation. Do not prepare another count request.
- A host timeout, transport uncertainty, or response persistence failure is `UNKNOWN` in the host Runner state. The Docker operator must record the same request as `UNKNOWN` with `mark_unknown(request_id)` after reconciling the host state. Never redispatch it.
- A malformed or mismatched copied response fails the P5 workflow closed. Do not replace the UUID to bypass the failed or uncertain request.
- A successful count produces token evidence only. It does not reserve the paid Ledger, consume Owner Approval, or authorize Generation.

### Single-command local P5 token-count workflow

From the repository root in the Docker Container, run:

```bash
python -m src.ai_copilot.local_token_count_e2e --case EV-01
```

The operator command defaults to the pinned EV-01 synthetic case (Baseline, two Brief records, no comparison). It checks persisted workflow/orphan state before issuing a new Run, then creates the trusted SyntheticHarness Context, validated Brief, exact `gpt-6-luna` P5 ProviderRequest, one P5 request package and UUID. It displays non-secret identity and digest metadata, then waits for the matching response file. When the Windows background Worker is installed and its local policy explicitly allows this Case, it automatically transfers, executes and returns the package without a per-request PowerShell command, file copy, or `EXECUTE` prompt. The same live trusted Brief and ProviderRequest are used for collection and the existing exact token evidence gate.

Do not stop the waiting process during a real host operation. Ctrl-C/EOF marks the original request UNKNOWN; a subsequent invocation refuses to create a new Run or UUID while that workflow is unresolved. `python -m src.ai_copilot.local_token_count_e2e --status` displays recorded case, state, UUID and Run without creating a Run. UNKNOWN and FAILED workflows require reconciliation and are never retried automatically. If the process is lost, the original validated Brief cannot be restored from SQLite digests; stop rather than attempting to collect with reconstructed context or preparing a replacement.

The Container command never retrieves credentials or dispatches an API request. Only the separately installed Windows Worker can dispatch; it checks the Windows-local policy before Credential Manager access. Fake E2E tests are offline evidence and do not constitute a real count.

Task Scheduler, Docker CLI transfer and P5 response collection are automated after one-time Windows bootstrap and explicit local policy enablement. This does not automate or consume production approval. No real Windows-host or API acceptance is implied by the offline Fake Transport tests.
