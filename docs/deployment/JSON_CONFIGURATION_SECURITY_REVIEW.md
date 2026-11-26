# Stage 4 — JSON configuration path security review

Date: 2026-11-25 UTC. The previous UI performed `Path(config_text).read_text()` on a user-supplied path. A configuration's `files[*].path` could also direct CSV reads. The published-run path field accepted arbitrary server paths before `load_sequential_outputs()`. These were unsafe in a public app that may later hold a Secret.

## Implemented boundary

`dashboard/cloud_paths.py` now accepts only the exact packaged `examples/planning/synthetic_demo/config.json` path (relative or canonical absolute). It rejects aliases, traversal, other absolute paths, oversized or invalid JSON, wrong data mode, invalid CSV names, symlinked CSV files and CSVs above the size limit. Each referenced CSV must be an adjacent regular file. The separate user CSV upload workflow remains available and unchanged.

The selected published-run path is restricted to this browser session's generated planning runs, historical synthetic `tmp/planning_source_runs`, or the exact existing WP2 test root `tmp/user_data_acceptance_2026-11-17/runs`. The historical roots are absent from a minimal Cloud package; they preserve local read-only WP2 regression coverage. Arbitrary `tmp` paths remain forbidden. Symlink escape from each allowed root is rejected, and a symlinked manifest is rejected. Existing `load_sequential_outputs()` additionally verifies artifact locations and SHA-256 digests. Sensitive files such as Secrets are outside the allowed roots.

Security tests cover valid packaged configuration, traversal, absolute sensitive paths, symlink alias/CSV escape, malformed/oversized JSON, invalid CSV references, published-run escape and manifest symlink. Residual limits: this is a Cloud UI path boundary, not a sandbox against arbitrary Python code or a concurrent local administrator changing packaged files between verification and read. The release source must remain Owner-reviewed. UI error handling does not print rejected file content.

No real Secret was read. The existing P5 deployment-source guard was not changed.
