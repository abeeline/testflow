const el = {
  spec: document.getElementById("spec"),
  profile: document.getElementById("profile"),
  manifest: document.getElementById("manifest"),
  extension: document.getElementById("extension"),
  efsm: document.getElementById("efsm"),
  configReq: document.getElementById("configReq"),
  useLlmCfg: document.getElementById("useLlmCfg"),
  configOut: document.getElementById("configOut"),
  report: document.getElementById("report"),
  activeEfsm: document.getElementById("activeEfsm"),
  mbtOut: document.getElementById("mbtOut"),
  status: document.getElementById("status"),
  graph: document.getElementById("graph"),
  mode: document.getElementById("mode"),
  deviceId: document.getElementById("deviceId"),
  atPort: document.getElementById("atPort"),
  baud: document.getElementById("baud"),
  maxSteps: document.getElementById("maxSteps"),
};

function setStatus(s) { el.status.textContent = s; }
function j(v) { return JSON.stringify(v, null, 2); }
function parseJSON(name, text) {
  try { return JSON.parse(text || "{}"); }
  catch (e) { throw new Error(`${name} JSON解析失败: ${e.message}`); }
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function postJSON(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const t = await r.text();
  if (!r.ok) throw new Error(t || `HTTP ${r.status}`);
  return t ? JSON.parse(t) : {};
}

async function loadAll() {
  setStatus("加载中...");
  const [spec, profile, manifest, extension, efsm, build] = await Promise.all([
    getJSON("/api/at-agent/spec"),
    getJSON("/api/at-agent/profile"),
    getJSON("/api/at-agent/manifest"),
    getJSON("/api/at-agent/extension"),
    getJSON("/api/at-agent/efsm"),
    getJSON("/api/at-agent/build"),
  ]);
  el.spec.value = j(spec);
  el.profile.value = j(profile);
  el.manifest.value = j(manifest);
  el.extension.value = j(extension);
  el.efsm.value = j(efsm);
  el.report.textContent = j(build.report || {});
  el.activeEfsm.textContent = j(build.active_efsm || {});
  renderGraph(build.active_efsm || efsm || {});
  setStatus("加载完成");
}

async function saveAll() {
  setStatus("保存中...");
  const spec = parseJSON("ATSpec", el.spec.value);
  const profile = parseJSON("Profile", el.profile.value);
  const manifest = parseJSON("Manifest", el.manifest.value);
  const extension = parseJSON("Extension", el.extension.value);
  const efsm = parseJSON("EFSM", el.efsm.value);
  await postJSON("/api/at-agent/spec", { data: spec, locked_baseline: true });
  await postJSON("/api/at-agent/profile", { data: profile });
  await postJSON("/api/at-agent/manifest", { data: manifest });
  await postJSON("/api/at-agent/extension", { data: extension });
  await postJSON("/api/at-agent/efsm", { data: efsm });
  setStatus("保存完成");
}

async function compile() {
  setStatus("编译中...");
  const out = await postJSON("/api/at-agent/compile", { use_llm: true });
  el.report.textContent = j(out.report || {});
  el.activeEfsm.textContent = j(out.active_efsm || {});
  renderGraph(out.active_efsm || {});
  setStatus("编译完成");
}

async function configCompile() {
  const request_text = (el.configReq.value || "").trim();
  if (!request_text) throw new Error("请填写配置需求");
  setStatus("配置编译中...");
  const out = await postJSON("/api/at-agent/config-compile", {
    request_text,
    use_llm: !!el.useLlmCfg.checked,
    apply_changes: true,
    compile_after_apply: true,
  });
  el.configOut.textContent = j(out);
  if (out.manifest) el.manifest.value = j(out.manifest);
  if (out.extension) el.extension.value = j(out.extension);
  if (out.compile_result?.report) el.report.textContent = j(out.compile_result.report);
  if (out.compile_result?.active_efsm) {
    el.activeEfsm.textContent = j(out.compile_result.active_efsm);
    renderGraph(out.compile_result.active_efsm);
  }
  setStatus("配置编译完成");
}

async function resetBaseline() {
  setStatus("重置中...");
  await postJSON("/api/at-agent/reset-baseline", {});
  await loadAll();
  setStatus("基线重置完成");
}

async function runMbt() {
  setStatus("MBT执行中...");
  const out = await postJSON("/api/at-agent/mbt/run", {
    mode: el.mode.value,
    device_id: (el.deviceId.value || "").trim(),
    at_port: (el.atPort.value || "").trim(),
    baudrate: Number(el.baud.value || 115200),
    max_steps: Number(el.maxSteps.value || 20),
  });
  el.mbtOut.textContent = j(out);
  setStatus(`MBT执行完成：覆盖 ${out.coverage?.covered || 0}/${out.coverage?.total || 0}`);
}

function renderGraph(efsm) {
  el.graph.innerHTML = "";
  const states = Array.isArray(efsm?.states) ? efsm.states : [];
  const transitions = Array.isArray(efsm?.transitions) ? efsm.transitions : [];
  if (!states.length) {
    el.graph.innerHTML = "<pre>暂无可渲染状态</pre>";
    return;
  }

  const width = el.graph.clientWidth || 1000;
  const height = el.graph.clientHeight || 460;
  const svg = d3.select(el.graph).append("svg").attr("width", width).attr("height", height);

  const nodeMap = new Map();
  const nodes = states
    .filter((s) => s && s.id)
    .map((s) => ({ id: String(s.id), type: String(s.type || "stable"), label: String(s.id) }));
  nodes.forEach((n) => nodeMap.set(n.id, n));

  const links = [];
  transitions.forEach((t) => {
    if (!t || !t.to) return;
    const from = String(t.from || "").trim();
    const to = String(t.to || "").trim();
    if (from === "*" || !from) return;
    if (!nodeMap.has(from) || !nodeMap.has(to)) return;
    links.push({ source: from, target: to, label: String(t.id || "") });
  });

  svg.append("defs").append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 22)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#93c5fd");

  const link = svg.append("g").selectAll("line").data(links).enter().append("line")
    .attr("stroke", "#60a5fa").attr("stroke-width", 1.4).attr("marker-end", "url(#arrow)");

  const label = svg.append("g").selectAll("text").data(links).enter().append("text")
    .text((d) => d.label).attr("font-size", 10).attr("fill", "#cbd5e1");

  const node = svg.append("g").selectAll("g").data(nodes).enter().append("g")
    .call(d3.drag()
      .on("start", (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on("end", (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

  node.append("circle")
    .attr("r", 16)
    .attr("fill", (d) => (d.type === "initial" ? "#16a34a" : "#0ea5b7"))
    .attr("stroke", "#e5e7eb")
    .attr("stroke-width", 1.2);

  node.append("text")
    .text((d) => d.label)
    .attr("text-anchor", "middle")
    .attr("dy", 30)
    .attr("font-size", 11)
    .attr("fill", "#cbd5e1");

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance(110))
    .force("charge", d3.forceManyBody().strength(-320))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(25));

  sim.on("tick", () => {
    nodes.forEach((d) => {
      d.x = Math.max(20, Math.min(width - 20, d.x || 20));
      d.y = Math.max(20, Math.min(height - 20, d.y || 20));
    });
    link.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y).attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
    label.attr("x", (d) => (d.source.x + d.target.x) / 2).attr("y", (d) => (d.source.y + d.target.y) / 2 - 4);
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
}

document.getElementById("loadBtn").addEventListener("click", () => loadAll().catch((e) => setStatus(e.message || String(e))));
document.getElementById("saveBtn").addEventListener("click", () => saveAll().catch((e) => setStatus(e.message || String(e))));
document.getElementById("compileBtn").addEventListener("click", () => compile().catch((e) => setStatus(e.message || String(e))));
document.getElementById("resetBtn").addEventListener("click", () => resetBaseline().catch((e) => setStatus(e.message || String(e))));
document.getElementById("runMbtBtn").addEventListener("click", () => runMbt().catch((e) => setStatus(e.message || String(e))));
document.getElementById("configCompileBtn").addEventListener("click", () => configCompile().catch((e) => setStatus(e.message || String(e))));

loadAll().catch((e) => setStatus(`初始化失败: ${e.message || e}`));
