# ReplayBench Results

ReplayBench Results is the public archive and Run Explorer for selected [ReplayBench](https://github.com/Yang-Zhaowei/ReplayBench) benchmark releases. The Explorer serves HTML, CSS, JavaScript, and JSON from `public/`.

## Local preview

```powershell
uv run --no-project python -m http.server 8000 --bind 127.0.0.1 --directory public
```

Open <http://127.0.0.1:8000/> in Edge or another browser. The site works offline through the local server once Python is available.

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
