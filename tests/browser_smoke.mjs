import assert from "node:assert/strict";
import {mkdtemp, readFile, rm} from "node:fs/promises";
import {createServer} from "node:http";
import {spawn} from "node:child_process";
import {once} from "node:events";
import {tmpdir} from "node:os";
import {dirname, join, resolve} from "node:path";

const browser = process.argv[2];
if (!browser) throw new Error("Usage: node tests/browser_smoke.mjs <path-to-Chrome-or-Edge>");

function record(run_id, score, started_at, backend = "local") {
  return {
    run_id,
    track: "direct_model",
    task: {id: "smoke-task", version: "1.0", candidate: false, manifest_sha256: "a".repeat(64),
      source_sha256: "b".repeat(64), input_sha256: "c".repeat(64)},
    verifier: {name: "smoke-verifier", revision: "1.0", identity_sha256: "d".repeat(64)},
    subject: {id: "smoke-subject"},
    model: {declared: "Smoke Model", observed: null, requested: "smoke-model",
      quantization: "Q4", revision: null, context_window: null, reasoning: {}},
    backend: {name: backend, version: "1.0"},
    hardware: {gpu: null, vram_gb: null, ram_gb: null},
    agent: {name: null, version: null},
    execution: {status: "completed", started_at, adapter_seconds: 1, client_wall_seconds: 2,
      verification_seconds: 0},
    result: {score, strict_pass: score > 0.7, critical_failures: [], critical_failure_details: []},
    tokens: {prompt: 10, completion: 20, cache_read: 0, cache_write: 0, tool_calls: 0},
    server: {prompt_tokens_per_second: 10, generation_tokens_per_second: 5,
      draft_acceptance_rate: null, cached_tokens: null, draft_tokens: null, accepted_draft_tokens: null},
    runtime: {effective_context_window: null, effective_reasoning_budget: null,
      observed_reasoning_present: null, declared_context: {}, subject_declared_settings: {},
      operator_declared_settings: {}, requested_parameters: {}},
    metadata_flags: []
  };
}

const latest = {public_schema_version: 1, records: [
  record("first-run", 0.8, "2026-01-02T00:00:00Z"),
  record("second-run", 0.6, "2026-01-01T00:00:00Z", "alternate")
]};
latest.records[0].hardware = {gpu: "RTX 4070", vram_gb: 12, ram_gb: 32, cpu: "Intel Core i7-13700KF",
  memory_type: "DDR5", source: "declared", operator_confirmed_fields: ["cpu", "memory_type", "ram_gb"]};
const older = {public_schema_version: 1, records: [record("historical-run", 0.9, "2025-12-01T00:00:00Z")]};
const snapshot = "2026-01-01-0123456789ab";
const root = new URL("../", import.meta.url);
const assets = {
  "/browser-smoke": ["tests/browser_smoke.html", "text/html"],
  "/": ["public/index.html", "text/html"],
  "/assets/explorer.js": ["public/assets/explorer.js", "text/javascript"],
  "/assets/explorer.css": ["public/assets/explorer.css", "text/css"]
};
const server = createServer(async (request, response) => {
  const path = new URL(request.url, "http://localhost").pathname;
  if (path === "/data/latest.json") return json(response, latest);
  if (path === "/data/catalog.json") return json(response, {
    public_schema_version: 1, latest_snapshot_id: "2026-01-02-abcdef123456",
    snapshots: [{snapshot_id: snapshot, record_count: 1}]
  });
  if (path === `/data/snapshots/${snapshot}/benchmark.json`) return json(response, older);
  if (!Object.hasOwn(assets, path)) return response.writeHead(404).end();
  const [file, contentType] = assets[path];
  try {
    const bytes = await readFile(new URL(file, root));
    response.writeHead(200, {"Content-Type": contentType + "; charset=utf-8"}).end(bytes);
  } catch {
    response.writeHead(404).end();
  }
});
function json(response, data) {
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(data));
}

const tempRoot = resolve(tmpdir());
const profile = await mkdtemp(join(tempRoot, "replaybench-browser-"));
try {
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const {port} = server.address();
  const processHandle = spawn(browser, [
    "--headless=new", "--disable-gpu", "--no-first-run", `--user-data-dir=${profile}`,
    "--disable-background-networking", "--disable-sync", "--hide-scrollbars",
    "--window-size=600,1200", "--virtual-time-budget=10000", "--dump-dom",
    `http://127.0.0.1:${port}/browser-smoke`
  ], {stdio: ["ignore", "pipe", "pipe"], timeout: 20000, windowsHide: true});
  let stdout = "";
  let stderr = "";
  processHandle.stdout.setEncoding("utf8").on("data", chunk => stdout += chunk);
  processHandle.stderr.setEncoding("utf8").on("data", chunk => stderr += chunk);
  const [code] = await once(processHandle, "close");
  assert.equal(code, 0, `Browser exited with code ${code}: ${stderr}`);
  const result = stdout.match(/<pre id="result">([^<]*)<\/pre>/)?.[1];
  assert.equal(result, "PASS", result ?? "Browser did not return the smoke test result");
  console.log("Browser smoke passed at 320px.");
} finally {
  server.close();
  server.closeAllConnections();
  if (dirname(profile) === tempRoot) {
    await rm(profile, {recursive: true, force: true, maxRetries: 3});
  }
}
