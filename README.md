# ReplayBench Results

ReplayBench Results is the public archive and Run Explorer for selected [ReplayBench](https://github.com/Yang-Zhaowei/ReplayBench) benchmark releases. The Explorer serves HTML, CSS, JavaScript, and JSON from `public/`.

## Local preview

```powershell
uv run --no-project python -m http.server 8000 --bind 127.0.0.1 --directory public
```

Open <http://127.0.0.1:8000/> in Edge or another browser. The site works offline through the local server once Python is available.

## Prepare and review a data release

Start with an accepted ReplayBench Registry v1 JSON export saved outside the served directory. The publisher uses Python 3.10 or later and the standard library. If a release already exists, copy `public/` into the local review directory first so the candidate includes the existing catalog and snapshots.

```powershell
New-Item -ItemType Directory -Force .review | Out-Null
Copy-Item -LiteralPath public -Destination .review -Recurse -Force
uv run --no-project python tools/publish_release.py --input 'C:\path\to\registry.json' --out .review/public
uv run --no-project python -m http.server 8000 --bind 127.0.0.1 --directory .review/public
```

Review `.review/privacy-audit.json`, the Markdown summary, the new snapshot and its manifest. The audit records included and omitted field paths, counts, detected violations, and the SHA-256 of the exact public JSON bytes. The publisher aborts on privacy violations and preserves the source file. The field and format checks catch common leaks. Review the remaining identifiers and labels for organization-specific private values before any public push, including to PR branches.

After approval, copy only the reviewed data artifacts from `.review/public/data/` to `public/data/`. Inspect the Git diff, verify that the new snapshot and `latest.json` share the manifest hash, and open a data-only pull request. The local audit and the source export stay outside `public/` and Git. Website updates use the same `public/` directory and can ship independently of data.

```powershell
Get-FileHash public/data/latest.json -Algorithm SHA256
uv run --no-project python -m unittest discover -s tests -v
```

To include the frozen acceptance test, set `REPLAYBENCH_ACCEPTANCE_EXPORT` to the path of the accepted 61-record JSON before running the suite. The test reads that export and creates its release in a temporary directory.

## Public schema v1

`data/latest.json` and every snapshot's `benchmark.json` have two top-level fields, `public_schema_version` and `records`. Optional measurements and metadata can be null. The [publisher's field allowlist](tools/publish_release.py) defines the public types and the permitted source leaves.

| Record group | Public content |
| --- | --- |
| Identity | Run ID, track, Subject ID, exact Task ID/version and manifest/source/input hashes, candidate flag, verifier name/revision and identity hash |
| Model and environment | Declared, requested and reported model, revision, quantization, GPU model, VRAM and RAM, backend name and version, agent name and version |
| Execution and evaluation | Start time, execution status, score, strict pass, critical check identifiers, dimensions and approved summaries |
| Configuration | Declared context and reasoning, allowlisted settings, effective context and reasoning budget, and whether reasoning content was observed |
| Measurements | Client and verifier durations, token and cache counters, server prompt and generation rates, draft counters and acceptance rate, and agent counters |
| Metadata flags | A flagged discrepancy can coexist with the original Subject and declared model values |

`direct_model` and `pi_agent` are separate tracks. The publisher selects both regardless of execution status. Candidate versions retain their original Task identity and carry an explicit flag based on the source version's `-candidate` suffix. Score sorting and comparison require recorded scores and a matching track, exact Task and input, and complete matching verifier identity and revision. The verifier hash covers the source entry point, name, and revision. Configuration values and runtime observations are shown alongside the scores. Null scores remain unavailable. The Registry v1 export does not include dimension scores, so the Explorer shows failure dimensions when available.

The publisher writes an immutable `data/snapshots/<snapshot-id>/` containing `benchmark.json` and `manifest.json`. The ID uses the UTC release date and 12 characters of the data SHA-256. The manifest records the full data and source export digests, counts, and coverage. Republishing identical data reuses its existing ID and manifest. The catalog points to the latest snapshot and lists earlier releases. The Explorer fetches those earlier datasets on demand.

To roll back just the data, restore `latest.json` and `benchmark.md` from the desired release commit and set `latest_snapshot_id` in `catalog.json` to that snapshot. Retain the other catalog entries and immutable snapshot directories so the Explorer can still browse them.

## Cloudflare Pages

In the Cloudflare dashboard, open **Workers & Pages**, create a **Pages** project with Git integration, and authorize the GitHub app for `Yang-Zhaowei/ReplayBench-Results`.

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Framework preset | None |
| Build command | Leave blank |
| Build output directory | `public` |
| Root directory | Repository root (default) |

Select **Save and Deploy**. Keep automatic production deployments enabled. Under branch control, allow preview deployments for branches used by pull requests. The Cloudflare GitHub app posts deployment status checks on commits and preview links on pull requests from the connected repository. Use a code-only PR to verify the integration before the first data release. [Cloudflare Pages setup](https://developers.cloudflare.com/pages/get-started/git-integration/) · [GitHub integration and checks](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)

For an immediate site rollback, open the project's **Deployments** tab, find a previous successful production deployment, then choose **Rollback to this deployment** from its menu. Revert the corresponding Git changes on `main` if subsequent deployments should retain that older version. [Cloudflare Pages rollbacks](https://developers.cloudflare.com/pages/configuration/rollbacks/)
