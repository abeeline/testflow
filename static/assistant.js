// TestFlow 助手（右下角对话气泡）
// - 对话：结合当前会话结果 + 当前项目资料/知识库（MCP）+ 公共资料回答；每个项目一份对话，存在本机浏览器里。
// - 运行动态：生成任务的进度、完成、需要处理的事项，和对话分开显示。
// - 系统状态：大模型、项目知识库、正在运行的任务，显示在面板顶部和侧栏“运行状态”里。
// 依赖 app.js 里的全局：stageState、currentProjectId、DEFAULT_PROJECT_ID、projects、projectLabel、currentProject、
// buildChatContext、switchSheetById、openSettings、esc、statusEl。app.js 通过 assistantOn* 钩子通知这里。

const botFab = document.getElementById("botFab");
const botPanel = document.getElementById("botPanel");
const botCloseBtn = document.getElementById("botCloseBtn");
const botRefreshBtn = document.getElementById("botRefreshBtn");
const botInput = document.getElementById("botInput");
const botSendBtn = document.getElementById("botSendBtn");
const botMessages = document.getElementById("botMessages");
const botWelcome = document.getElementById("botWelcome");
const botUnreadBadge = document.getElementById("botUnreadBadge");
const botContextEl = document.getElementById("botContext");
const botRunningEl = document.getElementById("botRunning");
const botActivityEl = document.getElementById("botActivity");
const botActivityCount = document.getElementById("botActivityCount");
const botActivityClear = document.getElementById("botActivityClear");
const botKbToggle = document.getElementById("botKbToggle");
const botKbScope = document.getElementById("botKbScope");
const botKbLabel = document.getElementById("botKbLabel");
const botStateDot = document.getElementById("botStateDot");
const botChatPane = document.getElementById("botChatPane");
const botComposer = document.getElementById("botComposer");
const sidebarStatus = document.getElementById("sidebarStatus");
const statusStateText = document.getElementById("statusStateText");
const statusClock = document.getElementById("statusClock");
const statusActivityBtn = document.getElementById("statusActivityBtn");

const BOT_CHAT_KEY = "testflow_bot_chat_v2:";
const BOT_KB_KEY = "testflow_bot_use_kb";
const BOT_MAX_SAVED = 40;
const BOT_MAX_ACTIVITY = 200;

const bot = {
  projectId: null,       // 当前对话属于哪个项目
  messages: [],          // [{role: "user"|"assistant"|"note", content, refs?, sources?, error?, llmMissing?}]
  pending: false,
  unread: 0,
  activity: [],          // [{ts, text, level}]
  activityUnseen: 0,
  tab: "chat",
  status: null,          // /api/assistant/status
  statusTimer: null,
  task: null,            // {label, detail, startedAt}
  lastAttention: null,   // 最近一条需要处理/失败的动态
  lastStatusAt: null,
  clockTimer: null,
};

// ---------- 小工具 ----------

function botStorageGet(key, fallback = null) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v;
  } catch (_) {
    return fallback;
  }
}

function botStorageSet(key, value) {
  try { localStorage.setItem(key, value); } catch (_) {}
}

function botProjectKey() {
  return currentProjectId && currentProjectId !== DEFAULT_PROJECT_ID ? currentProjectId : "";
}

function botHasProject() {
  return !!botProjectKey();
}

function fmtClock(d = new Date()) {
  return d.toTimeString().slice(0, 8);
}

function fmtElapsed(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function isBotPanelOpen() {
  return !!botPanel && !botPanel.classList.contains("hidden");
}

// 极简 Markdown：代码块、行内代码、粗体、标题、有序/无序列表、[K-n] 引用。先转义再加标签，不会注入 HTML。
function botInline(text, refs) {
  const refMap = new Map((refs || []).map((r) => [r.ref, r]));
  return esc(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[(K-\d+)\]/g, (m, ref) => {
      const r = refMap.get(ref);
      const title = r ? `${r.scope_label || ""} · ${r.filename || ""}` : "资料引用";
      return `<span class="bot-ref" title="${esc(title).replaceAll('"', "&quot;")}">${ref}</span>`;
    });
}

function botMarkdown(src, refs) {
  const parts = String(src || "").split("```");
  return parts.map((part, i) => {
    if (i % 2 === 1) return `<pre class="bot-code"><code>${esc(part.replace(/^[\w-]*\n/, ""))}</code></pre>`;
    const out = [];
    let list = null;
    let para = [];
    const flushPara = () => {
      if (para.length) out.push(`<p>${para.map((l) => botInline(l, refs)).join("<br>")}</p>`);
      para = [];
    };
    const flushList = () => {
      if (list) out.push(`<${list.tag}>${list.items.map((t) => `<li>${botInline(t, refs)}</li>`).join("")}</${list.tag}>`);
      list = null;
    };
    part.split("\n").forEach((line) => {
      const ul = line.match(/^\s*[-*•]\s+(.*)$/);
      const ol = line.match(/^\s*\d+[.、)]\s*(.*)$/);
      const h = line.match(/^\s*#{1,4}\s+(.*)$/);
      if (ul || ol) {
        flushPara();
        const tag = ul ? "ul" : "ol";
        if (!list || list.tag !== tag) { flushList(); list = { tag, items: [] }; }
        list.items.push((ul || ol)[1]);
      } else if (h) {
        flushPara(); flushList();
        out.push(`<div class="bot-h">${botInline(h[1], refs)}</div>`);
      } else if (!line.trim()) {
        flushPara(); flushList();
      } else {
        flushList();
        para.push(line);
      }
    });
    flushPara(); flushList();
    return out.join("");
  }).join("");
}

// ---------- 系统状态 ----------

async function refreshAssistantStatus() {
  try {
    const resp = await fetch(`/api/assistant/status?project_id=${encodeURIComponent(botProjectKey())}`);
    if (!resp.ok) return;
    const first = !bot.status;
    bot.status = await resp.json();
    if (first && (bot.status.running_jobs || []).length && !bot.task) {
      pushSystemBotMessage(`服务端还有 ${bot.status.running_jobs.length} 个任务在后台运行（可能是刷新页面前提交的），完成后可在“测试设计历史”里查看。`);
    }
  } catch (_) {
    return;
  }
  renderAssistantChrome();
}

function scheduleAssistantStatus(delay = 300) {
  clearTimeout(bot.statusTimer);
  bot.statusTimer = setTimeout(() => refreshAssistantStatus(), delay);
}

function sessionCounts() {
  const s = typeof stageState === "object" && stageState ? stageState : {};
  return {
    reqs: (s.requirement_spec?.final_requirements || []).length,
    rows: (s.test_design_spec?.integrated_matrix || []).length,
    cases: (s.test_case_spec?.testcases || []).length,
    exec: !!s.executable_cases,
  };
}

const BOT_STEPS = [
  { key: "reqs", label: "评审", sheet: "sheet2" },
  { key: "rows", label: "设计", sheet: "sheet3" },
  { key: "cases", label: "用例", sheet: "sheet4" },
  { key: "exec", label: "可执行", sheet: "sheet5" },
];

function renderAssistantContext() {
  if (!botContextEl) return;
  const st = bot.status;
  const llmOk = !!st?.llm?.enabled;
  const proj = st?.project;
  const counts = sessionCounts();

  const llmChip = `<button class="bot-chip ${st ? (llmOk ? "is-ok" : "is-warn") : ""}" type="button" data-bot-action="llm" title="${llmOk ? "大模型已配置，点击修改" : "大模型未配置，点击配置"}">
      <span class="bot-chip-dot"></span><span class="bot-chip-text">${esc(st ? (llmOk ? st.llm.model || "大模型" : "大模型未配置") : "检查中…")}</span></button>`;

  let projText = "未选项目 · 只查公共资料";
  let projCls = "";
  let projTitle = "在“需求准备”页选择项目后，助手会检索该项目的知识库和资料";
  if (proj?.selected) {
    const kb = proj.kb_configured ? "知识库 ✓" : "知识库未配置";
    projText = `${proj.name} · ${kb} · 资料 ${proj.doc_count}`;
    projCls = proj.kb_configured || proj.doc_count ? "is-ok" : "is-warn";
    projTitle = proj.kb_configured ? "助手会检索该项目的知识库（MCP）和项目资料，点击管理" : "该项目还没有配置知识库 MCP 地址，点击去配置";
  }
  const projChip = `<button class="bot-chip bot-chip-project ${projCls}" type="button" data-bot-action="project" title="${esc(projTitle)}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h7l2 2h9v10H3z"></path></svg><span class="bot-chip-text">${esc(projText)}</span></button>`;

  const steps = BOT_STEPS.map((s) => {
    const done = s.key === "exec" ? counts.exec : counts[s.key] > 0;
    const n = s.key === "exec" ? "" : counts[s.key] ? ` ${counts[s.key]}` : "";
    return `<button class="bot-step ${done ? "done" : ""}" type="button" data-bot-sheet="${s.sheet}" title="${done ? "已生成，点击查看" : "未生成"}">${esc(s.label)}${n}</button>`;
  }).join('<span class="bot-step-sep"></span>');

  botContextEl.innerHTML = `<div class="bot-context-row">${projChip}${llmChip}</div><div class="bot-steps" aria-label="当前会话进度">${steps}</div>`;
}

function renderKbToggle() {
  if (!botKbScope) return;
  const proj = bot.status?.project;
  const scope = proj?.selected ? "项目 + 公共" : "公共";
  botKbScope.textContent = botKbToggle?.checked ? `（${scope}）` : "（关）";
  if (botKbLabel) {
    botKbLabel.title = botKbToggle?.checked
      ? (proj?.selected
        ? `会检索“${proj.name}”的知识库和项目资料；问题里有协议关键词（流程、消息、定时器、条款号）时再查公共资料。`
        : "未选择项目：问题里有协议关键词时检索公共知识库和公共资料。")
      : "已关闭：只依据当前会话结果和模型自身知识回答，响应更快。";
  }
}

function currentRunState() {
  if (bot.task) return "running";
  if (bot.lastAttention) return "attention";
  return "idle";
}

function renderRunState() {
  const state = currentRunState();
  if (sidebarStatus) sidebarStatus.dataset.state = state;
  if (statusStateText) statusStateText.textContent = state === "running" ? "运行中" : state === "attention" ? "需要处理" : "空闲";
  if (statusClock) {
    statusClock.textContent = bot.task ? fmtElapsed(Date.now() - bot.task.startedAt) : (bot.lastStatusAt ? fmtClock(bot.lastStatusAt).slice(0, 5) : "");
    statusClock.title = bot.task ? "已运行时长" : "最近更新时间";
  }
  botFab?.classList.toggle("is-busy", state === "running");
  if (botStateDot) botStateDot.dataset.state = state;
  if (!botRunningEl) return;
  if (bot.task) {
    botRunningEl.classList.remove("hidden");
    botRunningEl.innerHTML = `<span class="bot-spinner" aria-hidden="true"></span>
      <div class="bot-running-text"><strong>${esc(bot.task.label)}</strong><span>${esc(bot.task.detail || "处理中…")}</span></div>
      <span class="bot-running-time">${fmtElapsed(Date.now() - bot.task.startedAt)}</span>`;
  } else if (bot.lastAttention) {
    botRunningEl.classList.remove("hidden");
    botRunningEl.innerHTML = `<span class="bot-attn-icon" aria-hidden="true">!</span>
      <div class="bot-running-text"><strong>需要处理</strong><span>${esc(bot.lastAttention.text)}</span></div>
      <button class="ui-btn ui-btn-ghost ui-btn-sm" type="button" data-bot-action="dismiss-attention">知道了</button>`;
  } else {
    botRunningEl.classList.add("hidden");
    botRunningEl.innerHTML = "";
  }
}

function renderAssistantChrome() {
  renderAssistantContext();
  renderKbToggle();
  renderRunState();
  if (!bot.messages.length) renderWelcome();
}

// ---------- 欢迎页：能力和边界 ----------

function botSuggestions() {
  const s = stageState || {};
  const out = [];
  const tcs = s.test_case_spec?.testcases || [];
  const reqs = s.requirement_spec?.final_requirements || [];
  const rows = s.test_design_spec?.integrated_matrix || [];
  if (tcs.length) out.push(`${tcs[0].tc_id} 为什么选这个测试环境？`);
  if (reqs.length) out.push(`${reqs[0].req_id} 还缺哪些异常或边界场景？`);
  if (rows.length && !tcs.length) out.push("测试设计里哪些矩阵行覆盖了定时器和异常流程？");
  if (botHasProject()) {
    const topic = reqs[0]?.title ? `“${String(reqs[0].title).slice(0, 24)}”` : "注册失败后的重试策略";
    out.push(`项目资料里关于${topic}有什么约定？`);
  }
  out.push("T3346 定时器到期后 UE 应该怎么处理？");
  out.push(reqs.length ? "下一步应该做什么？" : "怎么开始一次测试设计？");
  return out.slice(0, 4);
}

function capCard(icon, title, desc, statusHtml, cls = "") {
  return `<div class="bot-cap ${cls}"><div class="bot-cap-icon" aria-hidden="true">${icon}</div>
    <div class="bot-cap-body"><strong>${title}</strong><span>${desc}</span>${statusHtml ? `<div class="bot-cap-status">${statusHtml}</div>` : ""}</div></div>`;
}

function statusPill(ok, text, action = "", actionText = "") {
  const btn = action ? ` <button class="bot-link" type="button" data-bot-action="${action}">${esc(actionText)}</button>` : "";
  return `<span class="bot-pill ${ok === true ? "ok" : ok === false ? "warn" : ""}">${esc(text)}</span>${btn}`;
}

function renderWelcome() {
  if (!botWelcome) return;
  if (bot.messages.length) {
    botWelcome.innerHTML = "";
    botWelcome.classList.add("hidden");
    return;
  }
  botWelcome.classList.remove("hidden");
  const st = bot.status;
  const proj = st?.project;
  const counts = sessionCounts();
  const llmOk = st ? !!st.llm?.enabled : true;
  const page = document.querySelector(".sheet-tab.active")?.textContent.replace(/^\s*\S\s*/, "").trim() || "";

  const hasWork = counts.reqs || counts.rows || counts.cases;
  const sessionStatus = hasWork
    ? statusPill(true, `需求 ${counts.reqs} · 矩阵 ${counts.rows} · 用例 ${counts.cases}`)
    : statusPill(null, "还没有生成内容", "go-prepare", "去需求准备");

  let projStatus = statusPill(null, "未选择项目", "go-prepare", "去选择");
  if (proj?.selected) {
    projStatus = proj.kb_configured
      ? statusPill(true, `${proj.name}：知识库已连接 · 资料 ${proj.doc_count} 份`)
      : statusPill(proj.doc_count ? null : false, `${proj.name}：知识库未配置 · 资料 ${proj.doc_count} 份`, "project", "去配置");
  }
  const pubStatus = st?.public?.kb_configured
    ? statusPill(true, "公共知识库已连接")
    : statusPill(null, "公共知识库未配置，按模型自身知识回答", "kb", "去配置");

  const caps = [
    capCard("◎", "解读本次测试设计", "需求、评审问题、矩阵行和用例为什么这样设计，还缺什么场景。", sessionStatus),
    capCard("▣", "查项目知识库", "检索当前项目的知识库（MCP）和项目资料，回答里标注 [K-n] 出处。", projStatus),
    capCard("§", "3GPP 协议问答", "条款、流程、消息、定时器；问题带协议关键词时同时查公共资料。", pubStatus),
    capCard("➜", "操作指引", "告诉你在哪个页面改什么、下一步做什么。", page ? statusPill(null, `当前页面：${page}`) : ""),
  ].join("");

  const limits = [
    "<strong>只读</strong>：不会修改需求、矩阵或用例，也不会替你点击生成；需要调整时我会告诉你去哪里改。",
    "<strong>不执行测试</strong>：不连接仪表、Artemis 或 Amarisoft，看不到执行日志。",
    `<strong>资料范围</strong>：只查${proj?.selected ? `“${esc(proj.name)}”的项目资料` : "公共资料（未选项目）"}${proj?.selected ? "和公共资料" : ""}，看不到其他项目。`,
    "<strong>上下文有上限</strong>：每次带上前 20 条需求、40 行矩阵和 40 条用例，超出的部分请直接点名编号或到页面查看。",
    "<strong>请核对结论</strong>：条款号和数值可能出错，以 3GPP 原文和项目资料为准。",
    "<strong>对话只存本机</strong>：每个项目一份对话，保存在这台电脑的浏览器里，不会写进测试设计。",
  ];

  botWelcome.innerHTML = `
    ${llmOk ? "" : `<div class="bot-banner"><span>大模型未配置，助手暂时无法回答。</span><button class="ui-btn ui-btn-sm" type="button" data-bot-action="llm">去配置</button></div>`}
    <div class="bot-hello">
      <img src="/static/bot.png" alt="" />
      <div><strong>你好，我是 TestFlow 助手</strong>
        <p>我会结合当前会话的结果${proj?.selected ? `和项目“${esc(proj.name)}”的资料` : ""}回答问题。下面是我能做的和做不到的。</p></div>
    </div>
    <div class="bot-section-title">我能帮你</div>
    <div class="bot-caps">${caps}</div>
    <div class="bot-section-title">试试这样问</div>
    <div class="bot-suggestions">${botSuggestions().map((q) => `<button class="bot-suggestion" type="button" data-bot-ask="${esc(q).replaceAll('"', "&quot;")}">${esc(q)}</button>`).join("")}</div>
    <details class="bot-limits" open>
      <summary>能力边界</summary>
      <ul>${limits.map((l) => `<li>${l}</li>`).join("")}</ul>
    </details>`;
}

// ---------- 对话 ----------

function saveBotConversation() {
  if (bot.projectId === null) return;
  const keep = bot.messages.filter((m) => m.role !== "note" || m.keep).slice(-BOT_MAX_SAVED);
  botStorageSet(BOT_CHAT_KEY + (bot.projectId || "default"), JSON.stringify(keep));
}

function loadBotConversation(projectId) {
  let msgs = [];
  try {
    msgs = JSON.parse(botStorageGet(BOT_CHAT_KEY + (projectId || "default"), "[]")) || [];
  } catch (_) {
    msgs = [];
  }
  bot.projectId = projectId;
  bot.messages = Array.isArray(msgs) ? msgs.filter((m) => m && typeof m.content === "string") : [];
  renderBotMessages();
}

function sourcesHtml(sources) {
  if (!Array.isArray(sources) || !sources.length) return "";
  const label = { ok: "命中", empty: "无结果", error: "查询失败", not_configured: "未配置" };
  return `<div class="bot-sources">${sources.map((s) => {
    const n = s.status === "ok" ? ` ${s.hits}` : "";
    const title = s.error ? `${s.label}：${s.error}` : `${s.label}：${label[s.status] || s.status}`;
    return `<span class="bot-source is-${esc(s.status)}" title="${esc(title).replaceAll('"', "&quot;")}">${esc(s.label)} · ${esc(label[s.status] || s.status)}${n}</span>`;
  }).join("")}</div>`;
}

function refsHtml(refs) {
  if (!Array.isArray(refs) || !refs.length) return "";
  return `<details class="bot-refs"><summary>参考资料 ${refs.length} 条</summary><ul>${refs.map((r) =>
    `<li><span class="bot-ref">${esc(r.ref)}</span> ${esc(r.scope_label || "")} · ${esc(r.filename || "")}</li>`).join("")}</ul></details>`;
}

function messageHtml(m, index) {
  if (m.role === "note") return `<div class="bot-note">${esc(m.content)}</div>`;
  if (m.role === "user") return `<div class="bot-msg bot-msg-user">${esc(m.content)}</div>`;
  if (m.role === "pending") {
    return `<div class="bot-msg bot-msg-assistant bot-msg-pending"><span class="bot-typing"><i></i><i></i><i></i></span>${esc(m.content)}</div>`;
  }
  const action = m.llmMissing ? `<div class="bot-msg-actions"><button class="ui-btn ui-btn-sm" type="button" data-bot-action="llm">去配置大模型</button></div>` : "";
  const tools = m.error || m.llmMissing ? "" : `<button class="bot-copy" type="button" data-bot-copy="${index}" title="复制回答">复制</button>`;
  return `<div class="bot-msg bot-msg-assistant ${m.error ? "is-error" : ""}">
      <div class="bot-md">${botMarkdown(m.content, m.refs)}</div>
      ${sourcesHtml(m.sources)}${refsHtml(m.refs)}${action}${tools}
    </div>`;
}

function renderBotMessages() {
  if (!botMessages) return;
  botMessages.innerHTML = bot.messages.map(messageHtml).join("");
  renderWelcome();
  if (botChatPane) botChatPane.scrollTop = botChatPane.scrollHeight;
}

function pushBotMessage(m) {
  bot.messages.push(m);
  if (m.role !== "pending") saveBotConversation();
  renderBotMessages();
  if (m.role === "assistant" && (!isBotPanelOpen() || bot.tab !== "chat")) {
    bot.unread += 1;
    updateBotUnreadUI();
  }
}

function resetBotConversation() {
  bot.messages = [];
  saveBotConversation();
  renderBotMessages();
  if (botInput) botInput.value = "";
  autoGrowInput();
}

function chatHistoryPayload() {
  return bot.messages
    .filter((m) => (m.role === "user" || m.role === "assistant") && !m.error && !m.llmMissing)
    .slice(-8)
    .map((m) => ({ role: m.role, content: m.content }));
}

async function sendBotMessage(text) {
  const q = (text ?? botInput?.value ?? "").trim();
  if (!q || bot.pending) return;
  const history = chatHistoryPayload();
  const useKb = !!botKbToggle?.checked;
  if (botInput && text === undefined) botInput.value = "";
  autoGrowInput();
  pushBotMessage({ role: "user", content: q });
  const pending = { role: "pending", content: useKb ? (botHasProject() ? "正在检索项目资料并思考…" : "正在思考（有协议关键词时会查公共资料）…") : "正在思考…" };
  bot.messages.push(pending);
  renderBotMessages();
  bot.pending = true;
  if (botSendBtn) botSendBtn.disabled = true;
  let reply = null;
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, history, context: buildChatContext(), project_id: botProjectKey(), use_kb: useKb }),
    });
    const raw = await resp.text();
    let data = null;
    try { data = JSON.parse(raw); } catch (_) {}
    if (!resp.ok) {
      reply = { role: "assistant", error: true, content: `请求失败：${data?.detail || raw || resp.status}` };
    } else if (data?.llm_ready === false) {
      reply = { role: "assistant", llmMissing: true, content: data.reply || "大模型未配置。" };
    } else {
      reply = {
        role: "assistant",
        content: (data?.reply || "").trim() || "（没有返回内容）",
        refs: Array.isArray(data?.references) ? data.references : [],
        sources: data?.knowledge?.queried ? data.knowledge.sources : [],
      };
    }
  } catch (e) {
    reply = { role: "assistant", error: true, content: `请求失败：${e.message}（请确认 TestFlow 服务还在运行）` };
  } finally {
    bot.pending = false;
    if (botSendBtn) botSendBtn.disabled = false;
    bot.messages = bot.messages.filter((m) => m !== pending);
  }
  pushBotMessage(reply);
}

function autoGrowInput() {
  if (!botInput) return;
  botInput.style.height = "auto";
  botInput.style.height = `${Math.min(botInput.scrollHeight, 140)}px`;
}

// ---------- 运行动态 ----------

function activityLevel(text, options) {
  if (options?.level) return options.level;
  if (/失败|异常|中断|错误/.test(text)) return "error";
  if (options?.actionNeeded) return "action";
  if (/完成|已生成|已定稿/.test(text)) return "success";
  return "info";
}

// app.js 里所有任务进度都走这个函数（名字沿用旧版）
function pushSystemBotMessage(text, options = {}) {
  const level = activityLevel(String(text || ""), options);
  const item = { ts: new Date(), text: String(text || ""), level };
  bot.activity.push(item);
  if (bot.activity.length > BOT_MAX_ACTIVITY) bot.activity.splice(0, bot.activity.length - BOT_MAX_ACTIVITY);
  if (level === "action" || level === "error") {
    bot.lastAttention = item;
    if (!isBotPanelOpen() || bot.tab !== "activity") {
      bot.activityUnseen += 1;
      bot.unread += 1;
      updateBotUnreadUI();
    }
  } else if (level === "success" && bot.lastAttention && !bot.task) {
    // 新的成功结果说明之前的问题已经处理过了
    bot.lastAttention = null;
  }
  renderActivity();
  renderRunState();
}

function renderActivity() {
  if (botActivityEl) {
    if (!bot.activity.length) {
      botActivityEl.innerHTML = `<li class="bot-activity-empty">还没有运行记录。点击“生成测试需求”或“一键生成”后，进度会显示在这里。</li>`;
    } else {
      botActivityEl.innerHTML = bot.activity.slice().reverse().map((a) =>
        `<li class="bot-activity-item is-${a.level}"><time>${fmtClock(a.ts)}</time><span>${esc(a.text)}</span></li>`).join("");
    }
  }
  if (botActivityCount) {
    botActivityCount.textContent = String(bot.activityUnseen);
    botActivityCount.classList.toggle("hidden", bot.activityUnseen <= 0);
  }
}

function updateBotUnreadUI() {
  if (botUnreadBadge) {
    botUnreadBadge.textContent = bot.unread > 99 ? "99+" : String(bot.unread);
    botUnreadBadge.classList.toggle("hidden", bot.unread <= 0);
  }
  botFab?.classList.toggle("has-unread", bot.unread > 0);
}

function markBotRead() {
  bot.unread = 0;
  if (bot.tab === "activity") bot.activityUnseen = 0;
  updateBotUnreadUI();
  renderActivity();
}

function switchBotTab(tab) {
  bot.tab = tab;
  document.querySelectorAll(".bot-tab").forEach((b) => {
    const on = b.dataset.botTab === tab;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  });
  document.querySelectorAll("[data-bot-pane]").forEach((p) => p.classList.toggle("hidden", p.dataset.botPane !== tab));
  botComposer?.classList.toggle("hidden", tab !== "chat");
  if (tab === "activity") bot.activityUnseen = 0;
  markBotRead();
  if (tab === "chat") setTimeout(() => botInput?.focus(), 0);
}

function openBotPanel(tab) {
  botPanel?.classList.remove("hidden");
  if (tab) switchBotTab(tab);
  else markBotRead();
  scheduleAssistantStatus(0);
  renderAssistantChrome();
  if (bot.tab === "chat") setTimeout(() => botInput?.focus(), 0);
}

// ---------- app.js 钩子 ----------

function assistantOnStatus(text) {
  bot.lastStatusAt = new Date();
  if (bot.task) {
    let line = String(text || "").split("\n")[0];
    if (line.startsWith(`${bot.task.label} · `)) line = line.slice(bot.task.label.length + 3);
    bot.task.detail = line.slice(0, 120);
  }
  renderRunState();
}

function assistantOnTaskBusy(label, busy) {
  if (busy) {
    bot.task = { label: label.replace(/[.…]+$/, ""), detail: "", startedAt: Date.now() };
    bot.lastAttention = null;
    clearInterval(bot.clockTimer);
    bot.clockTimer = setInterval(renderRunState, 1000);
  } else {
    bot.task = null;
    clearInterval(bot.clockTimer);
    bot.clockTimer = null;
    renderAssistantContext();
  }
  renderRunState();
}

function assistantOnProjectChanged() {
  const pid = botProjectKey();
  if (bot.projectId !== null && bot.projectId !== pid) {
    saveBotConversation();
    loadBotConversation(pid);
  } else if (bot.projectId === null) {
    loadBotConversation(pid);
  }
  scheduleAssistantStatus();
}

function assistantOnSessionChanged() {
  renderAssistantContext();
  if (!bot.messages.length) renderWelcome();
}

// ---------- 事件 ----------

botFab?.addEventListener("click", () => {
  if (isBotPanelOpen()) botPanel.classList.add("hidden");
  else openBotPanel(bot.activityUnseen > 0 && bot.tab !== "activity" && !bot.messages.length ? "activity" : undefined);
});
botCloseBtn?.addEventListener("click", () => botPanel?.classList.add("hidden"));
botRefreshBtn?.addEventListener("click", () => {
  if (bot.messages.length && !confirm("清空这个项目的对话记录？")) return;
  resetBotConversation();
  switchBotTab("chat");
});
botSendBtn?.addEventListener("click", () => sendBotMessage());
botInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    sendBotMessage();
  }
});
botInput?.addEventListener("input", autoGrowInput);
botKbToggle?.addEventListener("change", () => {
  botStorageSet(BOT_KB_KEY, botKbToggle.checked ? "1" : "0");
  renderKbToggle();
});
botActivityClear?.addEventListener("click", () => {
  bot.activity = [];
  bot.lastAttention = null;
  bot.activityUnseen = 0;
  renderActivity();
  renderRunState();
});
statusActivityBtn?.addEventListener("click", () => openBotPanel("activity"));
document.querySelectorAll(".bot-tab").forEach((b) => b.addEventListener("click", () => switchBotTab(b.dataset.botTab)));
document.querySelectorAll(".sheet-tab").forEach((b) => b.addEventListener("click", () => {
  if (!bot.messages.length && isBotPanelOpen()) setTimeout(renderWelcome, 0);
}));

botPanel?.addEventListener("click", (e) => {
  const ask = e.target.closest("[data-bot-ask]");
  if (ask) {
    sendBotMessage(ask.dataset.botAsk);
    return;
  }
  const sheet = e.target.closest("[data-bot-sheet]");
  if (sheet) {
    switchSheetById(sheet.dataset.botSheet);
    return;
  }
  const copy = e.target.closest("[data-bot-copy]");
  if (copy) {
    const m = bot.messages[Number(copy.dataset.botCopy)];
    if (m) navigator.clipboard?.writeText(m.content).then(() => {
      copy.textContent = "已复制";
      setTimeout(() => { copy.textContent = "复制"; }, 1200);
    }).catch(() => {});
    return;
  }
  const act = e.target.closest("[data-bot-action]")?.dataset.botAction;
  if (!act) return;
  if (act === "llm") openSettings("llm");
  else if (act === "kb") openSettings("kb");
  else if (act === "project") switchSheetById(botHasProject() ? "sheet9" : "sheet1");
  else if (act === "go-prepare") switchSheetById("sheet1");
  else if (act === "dismiss-attention") {
    bot.lastAttention = null;
    renderRunState();
  }
});

// 设置保存后（大模型、知识库、项目）刷新状态
document.addEventListener("click", (e) => {
  if (e.target.closest("#llmSaveBtn, #kbSaveBtn, #saveProjectBtn, #deleteProjectBtn, #closeSettingsBtn")) scheduleAssistantStatus(800);
});

// ---------- 初始化 ----------

if (botKbToggle) botKbToggle.checked = botStorageGet(BOT_KB_KEY, "1") !== "0";
loadBotConversation(botProjectKey());
renderActivity();
renderAssistantChrome();
refreshAssistantStatus();
