"use strict";

const get = id => document.getElementById(id);
const selected = new Set();
const trackNames = {direct_model: "Direct Model", pi_agent: "Pi Agent"};
const snapshots = new Map();
const trackViews = new Map();
let records = [];
const formatNumber = new Intl.NumberFormat("en", {maximumFractionDigits: 6});
const formatPercent = new Intl.NumberFormat("en", {style: "percent", maximumFractionDigits: 2});
const formatSummaryNumber = new Intl.NumberFormat("en", {maximumFractionDigits: 3});

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function value(item, unit = "") {
  if (item === null || item === undefined || item === "") return "Unknown";
  if (typeof item === "number") return formatNumber.format(item) + unit;
  if (typeof item === "boolean") return item ? "Yes" : "No";
  return String(item) + unit;
}

const model = run => run.model.declared ?? run.model.observed;
const modelName = run => model(run) ?? "Unknown model";
const hardwareName = run => run.hardware.gpu;
const taskName = run => `${run.task.id} · ${run.task.version}`;
const verifierName = run => run.verifier.name
  ? `${run.verifier.name} · ${value(run.verifier.revision)}`
  : `Verifier ${run.verifier.identity_sha256.slice(0, 8)} · revision unknown`;
const trackName = run => trackNames[run.track] ?? run.track;
const statusLabel = status => status.replaceAll("_", " ");
const failures = run => run.result.critical_failures;
const failureDetails = run => run.result.critical_failure_details ?? [];
const score = run => run.result.score === null ? "Unavailable" : value(run.result.score);
const failureList = run => failures(run) === null ? "Unknown" : failures(run).join(", ") || "None";

const filters = {
  track: [run => run.track, track => trackNames[track] ?? track],
  model: [modelName],
  task: [taskName],
  verifier: [verifierName],
  backend: [run => value(run.backend.name)],
  gpu: [run => value(hardwareName(run))],
  quantization: [run => value(run.model.quantization)],
  "execution-status": [run => run.execution.status, statusLabel]
};

function populateFilters() {
  for (const [id, [field, label = item => item]] of Object.entries(filters)) {
    const input = get(id);
    const options = [...new Set(records.map(field))].sort((a, b) => label(a).localeCompare(label(b)));
    input.replaceChildren(new Option("All", ""), ...options.map(option => new Option(label(option), option)));
  }
}

function metrics(run, includeScores = true) {
  const agent = run.agent ?? {};
  const rate = run.server.draft_acceptance_rate;
  const scores = includeScores ? [
    ["Score", score(run)],
    ["Strict pass", value(run.result.strict_pass)],
    ["Critical failures", failureList(run)]
  ] : [];
  return [
    ...scores,
    ["Adapter time", value(run.execution.adapter_seconds, " s")],
    ["Client wall time", value(run.execution.client_wall_seconds, " s")],
    ["Verification time", value(run.execution.verification_seconds, " s")],
    ["Prompt tokens", value(run.tokens.prompt)],
    ["Completion tokens", value(run.tokens.completion)],
    ["Cache-read tokens", value(run.tokens.cache_read)],
    ["Cache-write tokens", value(run.tokens.cache_write)],
    ["Server cached tokens", value(run.server.cached_tokens)],
    ["Server prompt rate", value(run.server.prompt_tokens_per_second, " tok/s")],
    ["Server generation rate", value(run.server.generation_tokens_per_second, " tok/s")],
    ["Draft tokens", value(run.server.draft_tokens)],
    ["Accepted draft tokens", value(run.server.accepted_draft_tokens)],
    ["Draft acceptance rate", rate == null ? "Unknown" : formatPercent.format(rate)],
    ["Model invocations", value(agent.model_invocation_count)],
    ["Tool calls", value(agent.tool_call_count ?? run.tokens.tool_calls)],
    ["Tool errors", value(agent.tool_error_count)],
    ["Retries", value(agent.retry_count)]
  ];
}

function showDialog(title, content) {
  get("detail-title").textContent = title;
  get("detail-content").replaceChildren(...content);
  get("detail").showModal();
}

function detailGroup(title, entries) {
  const list = node("dl");
  for (const [label, content] of entries) list.append(node("dt", label), node("dd", content));
  return [node("h3", title), list];
}

function settings(values) {
  return Object.entries(values ?? {}).sort(([a], [b]) => a.localeCompare(b))
    .map(([key, reading]) => {
      const formatted = reading && typeof reading === "object" ? `{${settings(reading)}}` : value(reading);
      return `${key} = ${formatted}`;
    }).join(", ") || "Unknown";
}

function runtimeConfiguration(run) {
  const runtime = run.runtime ?? {};
  return [
    ["Model context window (declared)", value(run.model.context_window, " tokens")],
    ["Model reasoning (declared)", settings(run.model.reasoning)],
    ["Effective context window (observed)", value(runtime.effective_context_window, " tokens")],
    ["Effective reasoning budget (observed)", value(runtime.effective_reasoning_budget, " tokens")],
    ["Reasoning content present (observed)", value(runtime.observed_reasoning_present)],
    ["Backend context and KV settings (declared)", settings(runtime.declared_context)],
    ["Subject runtime settings (declared)", settings(runtime.subject_declared_settings)],
    ["Operator settings (declared)", settings(runtime.operator_declared_settings)],
    ["Request parameters", settings(runtime.requested_parameters)]
  ];
}

function criticalFailureSection(run) {
  const detailsById = new Map(failureDetails(run).map(detail => [detail.id, detail]));
  const ids = failures(run) ?? [];
  const title = node("h3", "Critical failure details");
  if (!ids.length) return [title, node("p", failureList(run))];
  const list = node("ul");
  for (const id of ids) {
    const item = node("li");
    const detail = detailsById.get(id);
    item.append(node("strong", id),
      node("span", detail?.dimension ? `Dimension · ${detail.dimension}` : "Dimension unavailable", "sub"),
      node("span", detail?.summary || "Reason summary unavailable", "sub"));
    list.append(item);
  }
  return [title, list];
}

function showRun(run) {
  showDialog(modelName(run), [
    node("p", run.run_id, "mono"),
    ...metadataNotes(run),
    ...detailGroup("Benchmark", [
      ["Track", trackName(run)], ["Task", taskName(run)], ["Task manifest SHA-256", value(run.task.manifest_sha256)],
      ["Task source SHA-256", value(run.task.source_sha256)], ["Input SHA-256", value(run.task.input_sha256)],
      ["Verifier", verifierName(run)], ["Verifier identity SHA-256", value(run.verifier.identity_sha256)],
      ["Execution status", value(run.execution.status)],
      ["Started at", value(run.execution.started_at)]
    ]),
    ...detailGroup("Model and hardware", [
      ["Declared model", value(run.model.declared)], ["Requested model", value(run.model.requested)],
      ["Reported model", value(run.model.observed)],
      ["Model revision", value(run.model.revision)], ["Declared quantization", value(run.model.quantization)],
      ["Subject", value(run.subject.id)], ["Declared backend", value(run.backend.name)],
      ["Backend version", value(run.backend.version)], ["Declared GPU", value(hardwareName(run))],
      ["VRAM", value(run.hardware.vram_gb, " GB")], ["RAM", value(run.hardware.ram_gb, " GB")],
      ["Agent", value(run.agent.name)], ["Agent version", value(run.agent.version)]
    ]),
    ...detailGroup("Runtime configuration", runtimeConfiguration(run)),
    ...detailGroup("Recorded measurements", metrics(run)),
    ...criticalFailureSection(run)
  ]);
}

function metadataNotes(run) {
  return run.metadata_flags?.includes("subject_model_version_mismatch")
    ? [node("p", `Review needed. Subject ${run.subject.id} and declared model ${run.model.declared} carry different Qwen versions.`, "notice")]
    : [];
}

function buttonForRun(run) {
  const button = node("button", modelName(run), "run-link");
  button.type = "button";
  button.addEventListener("click", () => showRun(run));
  return button;
}

function runTable(rows) {
  const table = node("table", undefined, "run-table");
  table.setAttribute("role", "table");
  const headings = node("tr");
  headings.setAttribute("role", "row");
  const labels = ["Select", "Model / Run", "Task / Verifier", "Backend / hardware", "Status", "Score", "Server gen.", "Client wall"];
  for (const title of labels) {
    const heading = node("th", title);
    heading.scope = "col";
    heading.setAttribute("role", "columnheader");
    headings.append(heading);
  }
  table.append(node("thead"));
  table.tHead.setAttribute("role", "rowgroup");
  table.tHead.append(headings);
  const body = node("tbody");
  body.setAttribute("role", "rowgroup");
  const entries = new Map();
  for (const run of rows) {
    const row = node("tr");
    row.setAttribute("role", "row");
    const toggle = node("input");
    toggle.type = "checkbox";
    toggle.checked = selected.has(run);
    toggle.setAttribute("aria-label", `Select ${run.run_id} for comparison`);
    toggle.addEventListener("change", () => {
      if (toggle.checked) selected.add(run);
      else selected.delete(run);
      updateSelection();
    });
    const select = node("label", undefined, "select-run");
    select.append(toggle, node("span", "Compare", "mobile-select"));
    row.insertCell().append(select);
    const identity = row.insertCell();
    identity.append(buttonForRun(run), node("span", run.run_id, "sub mono"), node("span", value(run.model.quantization), "sub"));
    if (run.metadata_flags?.length) identity.append(node("span", "Metadata review", "sub notice"));
    row.insertCell().append(node("span", taskName(run)), node("span", verifierName(run), "sub"));
    row.insertCell().append(node("span", value(run.backend.name)), node("span", value(hardwareName(run)), "sub"));
    row.insertCell().append(node("span", statusLabel(run.execution.status), "status"));
    const result = row.insertCell();
    result.append(node("strong", score(run)));
    if (run.result.strict_pass !== null) {
      const pass = run.result.strict_pass;
      result.append(node("span", pass ? "Pass" : "Fail", `sub ${pass ? "pass" : "fail"}`));
    }
    for (const [reading, unit] of [[run.server.generation_tokens_per_second, " tok/s"],
      [run.execution.client_wall_seconds, " s"]]) {
      row.insertCell().textContent = reading == null ? "Unknown" : formatSummaryNumber.format(reading) + unit;
    }
    for (const [index, cell] of [...row.cells].entries()) {
      cell.setAttribute("role", "cell");
      if (index > 1) {
        const label = node("span", labels[index], "mobile-label");
        label.setAttribute("aria-hidden", "true");
        cell.prepend(label);
      }
    }
    const search = [run.run_id, run.subject.id, modelName(run), run.model.observed, taskName(run), verifierName(run),
      run.backend.name, hardwareName(run), run.model.quantization, run.execution.status,
      statusLabel(run.execution.status), ...(failures(run) ?? []),
      ...failureDetails(run).map(detail => detail.dimension)].join(" ").toLowerCase();
    entries.set(run, {row, toggle, search});
    body.append(row);
  }
  table.append(body);
  const container = node("div", undefined, "table-wrap run-list");
  container.tabIndex = 0;
  container.setAttribute("role", "region");
  container.setAttribute("aria-label", trackName(rows[0]) + " Runs");
  container.append(table);
  return {container, body, entries, order: rows};
}

function newest(a, b) {
  const time = run => Date.parse(run.execution.started_at) || 0;
  return time(b) - time(a) || a.run_id.localeCompare(b.run_id);
}

function sameBenchmark(rows) {
  return rows.length > 0 && rows.every(run => run.result.score != null && run.verifier.name && run.verifier.revision
    && sameEvaluation(run, rows[0]));
}

function sameTask(a, b) {
  return a.track === b.track && ["id", "version", "manifest_sha256", "input_sha256", "source_sha256"]
    .every(field => a.task[field] === b.task[field]);
}

function sameEvaluation(a, b) {
  return sameTask(a, b) && a.verifier.identity_sha256 === b.verifier.identity_sha256;
}

function updateSelection() {
  get("selection").textContent = `${selected.size} of 2 selected`;
  get("compare").disabled = selected.size !== 2;
  get("clear-selection").hidden = !selected.size;
  for (const view of trackViews.values()) {
    for (const [run, {toggle}] of view.entries) {
      toggle.checked = selected.has(run);
      toggle.disabled = selected.size === 2 && !toggle.checked;
    }
  }
}

function render() {
  const query = get("search").value.toLowerCase().trim();
  const active = Object.entries(filters).map(([id, [field]]) => [get(id).value, field]).filter(([wanted]) => wanted);
  const sorting = get("sort").value;
  const unavailable = [];
  let count = 0;
  for (const [track, view] of trackViews) {
    const visible = [];
    for (const [run, {row, search}] of view.entries) {
      row.hidden = !(search.includes(query) && active.every(([wanted, field]) => field(run) === wanted));
      if (!row.hidden) visible.push(run);
    }
    view.section.hidden = !visible.length;
    count += visible.length;
    let order = newest;
    if (sorting === "model") order = (a, b) => modelName(a).localeCompare(modelName(b)) || newest(a, b);
    if (sorting === "score" && visible.length) {
      if (sameBenchmark(visible)) order = (a, b) => b.result.score - a.result.score || newest(a, b);
      else unavailable.push(trackNames[track]);
    }
    visible.sort(order);
    const current = view.order.filter(item => !view.entries.get(item).row.hidden);
    if (!visible.every((run, index) => run === current[index])) {
      for (const run of visible) view.body.append(view.entries.get(run).row);
      view.order = [...view.order.filter(item => view.entries.get(item).row.hidden), ...visible];
    }
  }
  get("empty").hidden = count > 0;
  get("count").textContent = `${count} of ${records.length} Runs`;
  get("sort-note").textContent = unavailable.length
    ? `Newest first in ${unavailable.join(", ")}. Score sorting requires one benchmark per track.` : "";
}

function showComparison() {
  const rows = [...selected];
  const [first, second] = rows;
  if (!sameTask(first, second)) {
    showDialog("Compare Runs", [node("p", "Choose two Runs from the same track with the exact same Task and input.")]);
    return;
  }
  const includeScores = sameBenchmark(rows);
  const table = node("table");
  const head = table.createTHead().insertRow();
  head.append(node("th", "Field"));
  for (const run of rows) {
    const cell = node("th", modelName(run));
    cell.append(node("span", run.run_id, "sub mono"),
      node("span", [run.model.quantization, run.backend.name, hardwareName(run)].filter(Boolean).join(" · "), "sub"));
    head.append(cell);
  }
  const body = table.createTBody();
  const configuration = run => [
    ["Backend", value(run.backend.name)],
    ["Backend version", value(run.backend.version)],
    ["Hardware", value(hardwareName(run))],
    ["Quantization", value(run.model.quantization)],
    ["Verifier", verifierName(run)],
    ["Execution status", value(run.execution.status)],
    ...runtimeConfiguration(run)
  ];
  const [leftConfig, rightConfig] = rows.map(configuration);
  const [leftMetrics, rightMetrics] = rows.map(run => metrics(run, includeScores));
  let differences = false;
  function addRow(name, left, right, highlight = false) {
    const row = body.insertRow();
    const heading = node("th", name);
    heading.scope = "row";
    if (highlight) {
      row.classList.add("configuration-difference");
      heading.append(node("span", "Differs", "sub"));
      differences = true;
    }
    row.append(heading, node("td", left), node("td", right));
  }
  for (const [index, [name, reading]] of leftConfig.entries()) {
    const other = rightConfig[index][1];
    addRow(name, reading, other, reading !== other);
  }
  for (const [index, [name, reading]] of leftMetrics.entries()) addRow(name, reading, rightMetrics[index][1]);
  const container = node("div", undefined, "table-wrap");
  container.tabIndex = 0;
  container.setAttribute("role", "region");
  container.setAttribute("aria-label", "Run comparison");
  container.append(table);
  const notes = [];
  if (differences) notes.push(node("p", "Highlighted rows show differences in recorded configuration.", "sub"));
  if (!includeScores) notes.push(node("p", "Score comparison requires two recorded scores and matching Verifier identity and revision.", "sub"));
  showDialog("Compare Runs", [node("p", `${trackName(first)} · ${taskName(first)}`), ...notes, container]);
}

function renderCards(models) {
  for (const name of models) {
    const runs = records.filter(run => modelName(run) === name);
    const distinct = field => [...new Set(runs.map(field).filter(Boolean))].sort().join(", ") || "Unknown";
    const card = node("article");
    const open = node("button", "Filter Runs", "run-link");
    open.type = "button";
    open.setAttribute("aria-label", `Filter Runs for ${name}`);
    open.addEventListener("click", () => {
      for (const id of Object.keys(filters)) get(id).value = "";
      get("search").value = "";
      get("model").value = name;
      render();
      get("filter-toggle").setAttribute("aria-expanded", "true");
      get("model").focus();
    });
    card.append(node("h3", name), node("p", `${runs.length} Runs · ${distinct(trackName)}`, "sub"),
      node("p", `Tasks: ${distinct(taskName)}`, "sub"), node("p", `Backends: ${distinct(run => run.backend.name)}`, "sub"),
      node("p", `Hardware: ${distinct(hardwareName)}`, "sub"),
      node("p", `Quantization: ${distinct(run => run.model.quantization)}`, "sub"),
      node("p", `Revisions: ${distinct(run => run.model.revision)}`, "sub"));
    const flagged = runs.filter(run => run.metadata_flags?.length);
    if (flagged.length) card.append(...metadataNotes(flagged[0]));
    card.append(open);
    get("cards").append(card);
  }
  if (!models.length) get("cards").append(node("p", "No model identities were recorded.", "sub"));
}

function showDataset(data) {
  records = data.records;
  selected.clear();
  trackViews.clear();
  get("runs").replaceChildren();
  get("cards").replaceChildren();
  get("search").value = "";
  get("sort").value = "newest";
  populateFilters();
  for (const [track, title] of Object.entries(trackNames)) {
    const rows = records.filter(run => run.track === track).sort(newest);
    if (!rows.length) continue;
    const view = runTable(rows);
    view.section = node("section");
    view.section.append(node("h3", title, "track-heading"), view.container);
    get("runs").append(view.section);
    trackViews.set(track, view);
  }
  const models = [...new Set(records.map(modelName))].sort((a, b) => a.localeCompare(b));
  const known = new Set(records.map(model).filter(Boolean)).size;
  get("overview").textContent = records.length
    ? `${records.length} archived Runs · ${known} recorded models`
    : "No public benchmark snapshots have been released.";
  get("empty").textContent = records.length ? "No Runs match these filters." : "Published Runs will appear here.";
  renderCards(models);
  render();
  updateSelection();
}

async function loadJSON(path, expectedArray) {
  const response = await fetch(path);
  if (!response.ok) throw new Error("Could not load data");
  const data = await response.json();
  if (data.public_schema_version !== 1 || !Array.isArray(data[expectedArray])) {
    throw new Error("Unsupported public data format");
  }
  return data;
}

async function loadLatest() {
  const catalog = loadJSON("data/catalog.json", "snapshots").catch(() => null);
  try {
    const latest = await loadJSON("data/latest.json", "records");
    snapshots.set("", latest);
    showDataset(latest);
    const index = await catalog;
    if (!index) {
      get("release-status").textContent = "Snapshot history is temporarily unavailable.";
      return;
    }
    const picker = get("snapshot");
    if (index.latest_snapshot_id) {
      picker.options[0].textContent = `Latest release · ${index.latest_snapshot_id}`;
    }
    for (const snapshot of index.snapshots) {
      if (snapshot.snapshot_id !== index.latest_snapshot_id && /^\d{4}-\d{2}-\d{2}-[a-f0-9]{12}$/.test(snapshot.snapshot_id)) {
        picker.add(new Option(`${snapshot.snapshot_id} · ${snapshot.record_count} Runs`, snapshot.snapshot_id));
      }
    }
    picker.disabled = picker.options.length < 2;
  } catch {
    get("overview").textContent = "Benchmark data could not be loaded.";
    get("release-status").textContent = "Reload the page to retry. For local use, open the Explorer through the preview server.";
  }
}

let activeSnapshot = "";
get("snapshot").addEventListener("change", async event => {
  const picker = event.target;
  const id = picker.value;
  picker.disabled = true;
  get("release-status").textContent = "Loading snapshot…";
  try {
    if (!snapshots.has(id)) snapshots.set(id, await loadJSON(`data/snapshots/${id}/benchmark.json`, "records"));
    showDataset(snapshots.get(id));
    activeSnapshot = id;
    get("release-status").textContent = "";
  } catch {
    picker.value = activeSnapshot;
    get("release-status").textContent = "This snapshot could not be loaded. Try again.";
  } finally {
    picker.disabled = false;
  }
});

get("filters").addEventListener("submit", event => event.preventDefault());
get("filter-toggle").addEventListener("click", event => {
  const button = event.currentTarget;
  button.setAttribute("aria-expanded", button.getAttribute("aria-expanded") !== "true");
});
for (const id of Object.keys(filters)) get(id).addEventListener("change", render);
get("search").addEventListener("input", render);
get("sort").addEventListener("change", render);
get("compare").addEventListener("click", showComparison);
get("clear-selection").addEventListener("click", () => {
  selected.clear();
  updateSelection();
  get("search").focus();
});
loadLatest();
