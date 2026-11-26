# Stage 5 — Security review

Date: 2026-11-26 UTC. Scope: the existing Streamlit Cloud AI Fake path. No production Secret or live provider was accessed.

## Controls verified locally

- **Access:** Existing salted scrypt verifier checks the masked password. Five failures lock one browser session for 15 minutes. A successful check creates a 30-minute HMAC grant under a process-only random key. The backend service checks the grant, expiry, lockout and current verifier before invoking any provider callable. A forged session expiry or grant fails. Password widget state is removed after submit. There is no global identity or durable cross-session lockout.
- The grant remains a bearer value in server-side Streamlit session state; the browser is not given it as a widget value. If server-side session state itself is compromised or copied, it is not an independent identity proof. Expiry also removes prior Copilot context and validated advice from that session.
- **Key:** `StreamlitSecretsCredential` is an explicit backend-only Cloud source; missing/invalid values yield sanitized errors. Fake work does not instantiate or call it. The real Cloud provider and P5 real dispatch remain locked. Secrets must never be put in source, browser state, exchange packages, logs or reports. Deployed code could read Cloud Secrets, so Owner release review remains essential.
- **Rate and replay:** Each accepted request reserves a process-local slot under a lock, with per-grant spacing/window/total and per-process UTC-day counts. The same question digest cannot be sent twice under one grant. An ambiguous provider outcome is never automatically retried. A new authenticated session or another process can obtain fresh counters.
- **Input/output:** A bounded question, three prior validated summaries, explicit Brief projection and two reviewed document excerpts comprise context. The full serialized request has a 30,000-byte cap. `max_output_tokens=500`; response bytes are capped at 16,000 and P1 validation rejects malformed/truncated advice. Byte size is a proxy, not exact model token evidence. Historical production data or arbitrary files are not loaded into this Cloud AI flow.
- **Cost:** An optional four-field model-price policy (`AI_PRICE_MODEL_ID`, `AI_PRICE_INPUT_USD_PER_MILLION`, `AI_PRICE_OUTPUT_USD_PER_MILLION`, `AI_SESSION_ESTIMATED_USD_LIMIT`) allows conservative per-session reservation. Partial, malformed or model-mismatched settings fail. No price means cost is **unconfigured**, not free. Usage/charge evidence and a reliable durable budget are still absent.
- **Errors:** Safe reason codes cover invalid access/configuration/context, rate, budget, provider and response errors. The UI shows generic messages; diagnostics log category only, never raw exception text, payload or Secret. Timeout, network ambiguity and unknown results consume capacity and are not retried.
- **Paths:** The Stage 4 packaged JSON/CSV allowlist and published-run restriction were retested. Reviewed business documents are fixed paths and now reject symlinked files/ancestors. No question text is interpreted as a filesystem path.

## Threats and release limits

| Threat | Current result | Remaining limit |
| --- | --- | --- |
| Anonymous paid API abuse | No real dispatch path exists; backend rejects missing signed grant | Before live release, establish durable identity/quotas or restrict AI to a genuinely Owner-controlled mode. A shared password and process counters are not a global public abuse defense. |
| Secret exfiltration via changed app code | No key in Fake flow; credential abstraction sanitizes errors | Streamlit Secrets cannot protect against malicious deployed Python. Owner must review exact release source/dependencies, control deployment rights and scan source. |
| Cost overrun | Local size, output, rate and estimated session reservation | No verified provider hard limit, exact token count, authoritative charge or durable global spend cap. Do not enable paid dispatch based on these estimates alone. |
| Restart / replicas | Grants fail after process restart; ambiguous request is not retried in-process | Process counters are lost; replicas do not share claims. No distributed exactly-once guarantee. |
| Prompt injection / false metrics | Brief/doc text is data; P1 evidence gate validates structured output | Model behavior remains unverified; no live provider test. Human review is still required for unsupported claims. |
| File read | Packaged paths and fixed document set only; traversal/symlink tests pass | Privileged code or concurrent local file mutation is outside the UI path boundary. |

**Security status: PASS WITH LIMITATIONS for offline Fake qualification.** It is not approval to unlock real provider transport, configure production Secrets or deploy.
