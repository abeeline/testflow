const runBtn = document.getElementById("runBtn");
const regenReqBtn = document.getElementById("regenReqBtn");
const genDesignBtn = document.getElementById("genDesignBtn");
const genCasesBtn = document.getElementById("genCasesBtn");
const genExecCasesBtn = document.getElementById("genExecCasesBtn");
const goExecCasesBtn = document.getElementById("goExecCasesBtn");
const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const closeSettingsBtn = document.getElementById("closeSettingsBtn");
const promptSelect = document.getElementById("promptSelect");
const promptEditor = document.getElementById("promptEditor");
const savePromptBtn = document.getElementById("savePromptBtn");
const reloadPromptsBtn = document.getElementById("reloadPromptsBtn");
const refreshFlowVizBtn = document.getElementById("refreshFlowVizBtn");
const flowVizCanvas = document.getElementById("flowVizCanvas");
const flowMermaid = document.getElementById("flowMermaid");
const flowPromptRoles = document.getElementById("flowPromptRoles");
const themeToggle = document.getElementById("themeToggle");

const requirementsEl = document.getElementById("requirements");
const ragEl = document.getElementById("rag");
const capabilityEl = document.getElementById("capability");
const actionVocabEl = document.getElementById("actionVocab");
const testEnvironmentOptionsEl = document.getElementById("testEnvironmentOptions");
const productProfileGroupsEl = document.getElementById("productProfileGroups");
const ragFileEl = document.getElementById("ragFile");
const uploadRagBtn = document.getElementById("uploadRagBtn");
const ragDocsEl = document.getElementById("ragDocs");
const statusEl = document.getElementById("status");
const botFab = document.getElementById("botFab");
const botPanel = document.getElementById("botPanel");
const botCloseBtn = document.getElementById("botCloseBtn");
const botRefreshBtn = document.getElementById("botRefreshBtn");
const botInput = document.getElementById("botInput");
const botSendBtn = document.getElementById("botSendBtn");
const botMessages = document.getElementById("botMessages");
const botUnreadBadge = document.getElementById("botUnreadBadge");

const outReq = document.getElementById("outReq");
const outReview = document.getElementById("outReview");
const outDesign = document.getElementById("outDesign");
const outCases = document.getElementById("outCases");
const execCasesSummary = document.getElementById("execCasesSummary");
const execCasesTrace = document.getElementById("execCasesTrace");
const execCasesBundles = document.getElementById("execCasesBundles");
const bzUrlEl = document.getElementById("bzUrl");
const bzKeyEl = document.getElementById("bzKey");
const bzSaveBtn = document.getElementById("bzSaveBtn");
const bzSettingsHint = document.getElementById("bzSettingsHint");
const llmStatusPill = document.getElementById("llmStatusPill");
const llmStatusText = document.getElementById("llmStatusText");
const llmBanner = document.getElementById("llmBanner");
const llmApiBaseEl = document.getElementById("llmApiBase");
const llmApiKeyEl = document.getElementById("llmApiKey");
const llmKeyHintEl = document.getElementById("llmKeyHint");
const llmModelEl = document.getElementById("llmModel");
const llmTimeoutEl = document.getElementById("llmTimeout");
const llmTestResultEl = document.getElementById("llmTestResult");
const llmSaveBtn = document.getElementById("llmSaveBtn");
const llmTestBtn = document.getElementById("llmTestBtn");
const llmClearKeyBtn = document.getElementById("llmClearKeyBtn");
const bzIdsEl = document.getElementById("bzIds");
const bzExcludedEl = document.getElementById("bzExcluded");
const bzFetchBtn = document.getElementById("bzFetchBtn");
const bzResult = document.getElementById("bzResult");

const viewReq = document.getElementById("viewReq");
const viewReview = document.getElementById("viewReview");
const viewDesign = document.getElementById("viewDesign");
const viewCases = document.getElementById("viewCases");
const openQuestionsPanel = document.getElementById("openQuestionsPanel");
const downloadExcelBtn = document.getElementById("downloadExcelBtn");
const designDocActions = document.getElementById("designDocActions");
const designDocLink = document.getElementById("designDocLink");
const refreshDesignHistoryBtn = document.getElementById("refreshDesignHistoryBtn");
const designHistoryList = document.getElementById("designHistoryList");
const designHistoryDetailTitle = document.getElementById("designHistoryDetailTitle");
const designHistoryMeta = document.getElementById("designHistoryMeta");
const designHistoryVisual = document.getElementById("designHistoryVisual");
const designHistoryJson = document.getElementById("designHistoryJson");
const designHistoryDocLink = document.getElementById("designHistoryDocLink");
const designHistoryLoadBtn = document.getElementById("designHistoryLoadBtn");
const designHistoryCasesBtn = document.getElementById("designHistoryCasesBtn");

const LAST_RESULT_KEY = "pocketflow_last_result_v2";
const THEME_KEY = "pocketflow_theme";
let promptCache = {};
let latestStructured = null;
let botHistory = [];
let botUnread = 0;
let flowVizLoaded = false;
let designHistoryLoaded = false;
let hitlStream = null;
let hitlStreamJobId = "";
let activeStageStream = null;
let activeStageJobId = "";
let latestDesignDocUrl = "";
let designHistoryItems = [];
let selectedDesignHistoryId = "";
let selectedDesignHistoryRecord = null;
let stageState = {
  requirement_spec: null,
  persona_reviews: null,
  requirement_review_history: null,
  test_design_spec: null,
  test_case_spec: null,
  round: 0,
  hitl_job_id: "",
  executable_cases: null,
  bug_ids: [],
  design_history_record_id: "",
  design_history_doc_url: "",
};

const PRODUCT_PROFILE_GROUPS = [
  {
    key: "network_core_protocols",
    label: "1. 网络制式与核心协议 (Network & Core Protocols)",
    options: ["5G NR", "4G LTE", "3G/2G", "NB-IoT / eMTC", "NTN", "IoT-NTN"],
  },
  {
    key: "fiveg_specifics",
    label: "2. 5G 专属组网与射频特性 (5G Specifics)",
    options: ["SA", "NSA", "Sub-6GHz (FR1)", "毫米波 mmWave (FR2)", "RedCap", "网络切片", "载波聚合"],
  },
  {
    key: "sim_standby_modes",
    label: "3. 卡与多待机模式 (SIM & Standby Modes)",
    options: ["单卡", "DSDS", "DSDA", "eSIM"],
  },
  {
    key: "services_data",
    label: "4. 核心业务与数据能力 (Services & Data)",
    options: ["VoNR", "VoLTE", "CSFB", "SMS over NAS / IMS", "IPv4 单栈", "IPv6 单栈", "IPv4/IPv6 双栈 (Dual Stack)"],
  },
  {
    key: "power_mobility",
    label: "5. 功耗与移动性管理 (Power & Mobility)",
    options: ["PSM", "eDRX", "C-DRX", "高铁模式 / 高速移动优化"],
  },
  {
    key: "special_scenarios",
    label: "6. 特殊场景与形态特性 (Special Scenarios & Form Factor)",
    options: ["GNSS / LBS", "C-V2X", "Android架构", "Linux架构", "RTOS架构"],
  },
  {
    key: "form_factor",
    label: "7. 产品定位与形态 (Form Factor)",
    options: ["智能手机", "功能手机", "穿戴产品", "通信模组", "车载模组"],
  },
];

const TEST_ENVIRONMENT_OPTIONS = [
  {
    id: "REAL_NETWORK",
    label: "实网环境",
    priority: 1,
    description: "使用运营商的SIM和网络，进行真实网络下的用户操作层面的测试。",
  },
  {
    id: "AMARISOFT",
    label: "Amarisoft模拟基站",
    priority: 2,
    description: "使用Amarisoft模拟基站，进行部分基础（PHY/协议L3）的仿真测试。",
  },
  {
    id: "PROTOCOL_ANALYZER",
    label: "协议分析仪表",
    priority: 3,
    description: "使用Keysight/Anritsu等协议分析仪表，进行IE配置与协议流程构建等测试。",
  },
];

const stageButtons = [runBtn, regenReqBtn, genDesignBtn, genCasesBtn, genExecCasesBtn, goExecCasesBtn];

function setStatus(text) {
  statusEl.textContent = text;
}

function setButtonsBusy(busy) {
  stageButtons.forEach((btn) => btn && (btn.disabled = !!busy));
}

function setSingleButtonBusy(button, busy, pendingText) {
  if (!button) return;
  if (!button.dataset.defaultText) button.dataset.defaultText = button.textContent || "";
  button.disabled = !!busy;
  button.textContent = busy ? (pendingText || "处理中...") : button.dataset.defaultText;
}

function parseRequirements(text) {
  const one = (text || "").trim();
  return one ? [one] : [];
}

function parseCSVLine(text) {
  if (!text.trim()) return null;
  return text.split(",").map((x) => x.trim()).filter((x) => x.length > 0);
}

function toProfileOptionId(groupKey, option) {
  return `pp_${groupKey}_${String(option).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "")}`;
}

function splitCustomValues(text) {
  return Array.from(new Set(`${text || ""}`.split(/[,，、;；\n]+/).map((x) => x.trim()).filter(Boolean)));
}

function renderProductProfileOptions() {
  if (!productProfileGroupsEl) return;
  productProfileGroupsEl.innerHTML = PRODUCT_PROFILE_GROUPS.map((group) => {
    const items = group.options
      .map((opt) => {
        const id = toProfileOptionId(group.key, opt);
        return `<label class="feature-option"><input type="checkbox" id="${id}" data-profile-group="${group.key}" data-profile-option="${esc(opt)}" /> ${esc(opt)}</label>`;
      })
      .join("");
    const custom = `<div class="feature-custom"><span>其他</span><input class="ui-input" type="text" id="pp_custom_${group.key}" data-profile-custom="${group.key}" placeholder="选项里没有的，在这里补充，多个用逗号分隔" /></div>`;
    return `<div class="feature-profile-group"><h4>${esc(group.label)}</h4><div class="feature-option-grid">${items}</div>${custom}</div>`;
  }).join("");
}

function getSelectedProductProfile() {
  const selected = {};
  const selectedFlat = [];
  PRODUCT_PROFILE_GROUPS.forEach((group) => {
    const values = [];
    group.options.forEach((opt) => {
      const el = document.getElementById(toProfileOptionId(group.key, opt));
      if (el?.checked) values.push(opt);
    });
    splitCustomValues(document.getElementById(`pp_custom_${group.key}`)?.value).forEach((v) => {
      if (!values.includes(v)) values.push(v);
    });
    if (values.length) {
      selected[group.key] = values;
      selectedFlat.push(...values);
    }
  });
  return {
    selected,
    selected_flat: selectedFlat,
    selected_count: selectedFlat.length,
    selected_groups: Object.keys(selected).length,
    profile_display: PRODUCT_PROFILE_GROUPS.filter((g) => selected[g.key]?.length).map((g) => ({
      group: g.label,
      values: selected[g.key],
    })),
  };
}

function setSelectedProductProfile(selectedMap = {}) {
  PRODUCT_PROFILE_GROUPS.forEach((group) => {
    const values = Array.isArray(selectedMap[group.key]) ? selectedMap[group.key] : [];
    group.options.forEach((opt) => {
      const el = document.getElementById(toProfileOptionId(group.key, opt));
      if (el) el.checked = values.includes(opt);
    });
    const customEl = document.getElementById(`pp_custom_${group.key}`);
    if (customEl) customEl.value = values.filter((v) => !group.options.includes(v)).join(", ");
  });
}

function renderTestEnvironmentOptions() {
  if (!testEnvironmentOptionsEl) return;
  testEnvironmentOptionsEl.innerHTML = `<div class="feature-profile-group"><div class="feature-option-grid env-grid">${TEST_ENVIRONMENT_OPTIONS.map((env) => {
    const id = `te_${env.id.toLowerCase()}`;
    return `<label class="feature-option"><input type="checkbox" id="${id}" data-test-env-id="${esc(env.id)}" /><span><strong>${esc(env.label)}</strong><span class="feature-hint">${esc(env.description)}</span></span></label>`;
  }).join("")}</div></div>`;
}

function getSelectedTestEnvironments() {
  const selectedIds = [];
  const selectedDetails = [];
  TEST_ENVIRONMENT_OPTIONS.forEach((env) => {
    const el = document.getElementById(`te_${env.id.toLowerCase()}`);
    if (el?.checked) {
      selectedIds.push(env.id);
      selectedDetails.push(env);
    }
  });
  return {
    selected_ids: selectedIds,
    selected_count: selectedIds.length,
    selected_details: selectedDetails,
    display: selectedDetails.map((env) => `${env.priority}. ${env.label}: ${env.description}`),
  };
}

function setSelectedTestEnvironments(selectedIds = []) {
  const set = new Set(Array.isArray(selectedIds) ? selectedIds.map((x) => String(x)) : []);
  TEST_ENVIRONMENT_OPTIONS.forEach((env) => {
    const el = document.getElementById(`te_${env.id.toLowerCase()}`);
    if (el) el.checked = set.has(env.id);
  });
}

function buildFrameworkCapabilityCatalog() {
  const base = (capabilityEl?.value || "").trim();
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  const productSummary = (productProfile.profile_display || [])
    .map((x) => `${x.group}: ${x.values.join(", ")}`)
    .join(" | ");
  const envSummary = (testEnvironments.selected_details || []).map((x) => `${x.label}`).join(", ");
  const extra = [
    productSummary ? `Product Profile: ${productSummary}` : "",
    envSummary ? `Available Test Environments: ${envSummary}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  return [base, extra].filter(Boolean).join("\n");
}

function esc(s) {
  return String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function formatTestEnvironmentSummary(env) {
  if (!env || typeof env !== "object") return "未指定";
  const primary = `${env.primary_label || env.primary || "未指定"}`.trim() || "未指定";
  const alternatives = Array.isArray(env.alternative_labels) && env.alternative_labels.length
    ? env.alternative_labels
    : Array.isArray(env.alternatives)
      ? env.alternatives
      : [];
  const parts = [primary];
  if (alternatives.length) {
    parts.push(`备选: ${alternatives.join("、")}`);
  }
  if (env.rationale) {
    parts.push(`依据: ${env.rationale}`);
  }
  return parts.join("；");
}

function formatTestEnvironmentRisk(env) {
  if (!env || typeof env !== "object") return "";
  return `${env.availability_risk || ""}`.trim();
}

function isBotPanelOpen() {
  return !!botPanel && !botPanel.classList.contains("hidden");
}

function updateBotUnreadUI() {
  if (botUnreadBadge) {
    botUnreadBadge.textContent = String(botUnread);
    botUnreadBadge.classList.toggle("hidden", botUnread <= 0);
  }
  botFab?.classList.toggle("has-unread", botUnread > 0);
}

function markBotRead() {
  botUnread = 0;
  updateBotUnreadUI();
}

function appendBotMessage(role, text, options = {}) {
  if (!botMessages) return;
  let cls = "bot-msg bot-msg-assistant";
  if (role === "user") cls = "bot-msg bot-msg-user";
  if (role === "system") cls = "bot-msg bot-msg-system";
  if (role === "system" && options?.actionNeeded) cls += " action-needed";
  const div = document.createElement("div");
  div.className = cls;
  div.innerHTML = esc(text || "");
  botMessages.appendChild(div);
  botMessages.scrollTop = botMessages.scrollHeight;
  if (!isBotPanelOpen()) {
    botUnread += 1;
    updateBotUnreadUI();
  }
}

function pushSystemBotMessage(text, options = {}) {
  appendBotMessage("system", text, options);
}

function closeHitlStream() {
  if (hitlStream) {
    hitlStream.close();
    hitlStream = null;
  }
  hitlStreamJobId = "";
}

function closeStageStream() {
  if (activeStageStream) {
    activeStageStream.close();
    activeStageStream = null;
  }
  activeStageJobId = "";
}

function handleHitlStreamEvent(ev) {
  const et = ev?.type || "";
  const payload = ev?.payload || {};
  if (et === "state") {
    if (payload.status && payload.status !== "starting") {
      pushSystemBotMessage(`HITL状态：${payload.status}（round=${payload.round || 0}）`);
    }
    if (payload.error) {
      pushSystemBotMessage(`HITL后台异常：${payload.error}`, { actionNeeded: true });
    }
    return;
  }
  if (et === "round_ready") {
    const r = payload.round || 0;
    const oq = (payload.open_questions || []).length;
    if (oq > 0) {
      pushSystemBotMessage(`HITL轮次 v${r} 完成，待确认问题 ${oq} 个。`, { actionNeeded: true });
    } else {
      pushSystemBotMessage(`HITL轮次 v${r} 完成。`);
    }
    return;
  }
  if (et === "waiting_answers") {
    const r = payload.round || 0;
    const n = (payload.open_questions || []).length;
    pushSystemBotMessage(`HITL等待人工补充（v${r}，${n} 个问题）。`, { actionNeeded: true });
    return;
  }
  if (et === "completed") {
    const r = payload.round || 0;
    pushSystemBotMessage(`HITL流程已完成（终稿 v${r}）。`);
    closeHitlStream();
    return;
  }
  if (et === "error") {
    pushSystemBotMessage(`HITL流程异常：${payload.error || "unknown error"}`, { actionNeeded: true });
    closeHitlStream();
  }
}

function ensureHitlStream(jobId) {
  if (!jobId) return;
  if (hitlStream && hitlStreamJobId === jobId) return;
  closeHitlStream();
  hitlStreamJobId = jobId;
  const es = new EventSource(`/api/hitl/requirements/${encodeURIComponent(jobId)}/stream`);
  hitlStream = es;

  es.onmessage = (msg) => {
    if (!msg?.data) return;
    try {
      const ev = JSON.parse(msg.data);
      handleHitlStreamEvent(ev);
    } catch (_) {}
  };
  es.onerror = async () => {
    const currentJob = hitlStreamJobId;
    closeHitlStream();
    if (!currentJob) return;
    // 页面刷新恢复的旧job、服务重启后的job丢失、或已完成任务，不应报错打扰用户
    try {
      const resp = await fetch(`/api/hitl/requirements/${encodeURIComponent(currentJob)}/state`);
      if (resp.status === 404) return;
      if (resp.ok) {
        const st = await resp.json();
        if (st?.status === "completed") return;
      }
    } catch (_) {}
    pushSystemBotMessage("HITL实时通道中断，请稍后重试或继续操作。", { actionNeeded: true });
  };
}

function stageLabel(stage) {
  if (stage === "design") return "测试设计";
  if (stage === "testcases") return "测试用例";
  if (stage === "scripts") return "测试脚本";
  return stage || "stage";
}

function nodeLabel(node) {
  const map = {
    TestDesignNode: "TestDesignNode",
    TestDesignSupervisorNode: "TestDesignSupervisorNode",
    TestCaseBatchGenNode: "TestCaseBatchGenNode",
    FinalizeTestCaseNode: "FinalizeTestCaseNode",
    TestCaseSupervisorNode: "TestCaseSupervisorNode",
    HarnessMapperNode: "HarnessMapperNode",
    ScriptWriterNode: "ScriptWriterNode",
  };
  return map[node] || node || "UnknownNode";
}

async function startStageJobAndWait(stage, payload) {
  const startResp = await postJson(`/api/stage/${stage}/start`, payload);
  const jobId = startResp.job_id;
  if (!jobId) throw new Error("stage job_id为空");

  closeStageStream();
  activeStageJobId = jobId;
  pushSystemBotMessage(`任务已提交到服务端：${stageLabel(stage)}（job=${jobId}）。`);

  return await new Promise((resolve, reject) => {
    const es = new EventSource(`/api/stage/${encodeURIComponent(jobId)}/stream`);
    activeStageStream = es;

    es.onmessage = (msg) => {
      if (!msg?.data) return;
      let ev = null;
      try {
        ev = JSON.parse(msg.data);
      } catch (_) {
        return;
      }
      const et = ev?.type || "";
      const p = ev?.payload || {};
      if (et === "state") {
        if (p?.status && p.status !== "running") pushSystemBotMessage(`${stageLabel(stage)}任务状态：${p.status}`);
        return;
      }
      if (et === "job_started") {
        pushSystemBotMessage(`${stageLabel(stage)}任务开始执行。`);
        return;
      }
      if (et === "node_running") {
        const n = nodeLabel(p.node);
        setStatus(`${stageLabel(stage)}执行中：${n}`);
        pushSystemBotMessage(`${stageLabel(stage)}执行节点：${n}`);
        return;
      }
      if (et === "module_result") {
        if (p.module) pushSystemBotMessage(`${stageLabel(stage)}模块完成：${p.module}`);
        return;
      }
      if (et === "completed") {
        pushSystemBotMessage(`${stageLabel(stage)}任务已完成。`);
        closeStageStream();
        resolve(p.result || {});
        return;
      }
      if (et === "error") {
        const msgText = p.error || "unknown error";
        pushSystemBotMessage(`${stageLabel(stage)}任务失败：${msgText}`, { actionNeeded: true });
        closeStageStream();
        reject(new Error(msgText));
      }
    };

    es.onerror = async () => {
      closeStageStream();
      try {
        const s = await fetch(`/api/stage/${encodeURIComponent(jobId)}/state`);
        if (s.ok) {
          const st = await s.json();
          if (st.status === "completed") {
            resolve(st.result || {});
            return;
          }
          const err = st?.error?.error || st?.error || "stage stream disconnected";
          reject(new Error(String(err)));
          return;
        }
      } catch (_) {}
      reject(new Error("stage stream disconnected"));
    };
  });
}

function resetBotConversation() {
  botHistory = [];
  if (!botMessages) return;
  botMessages.innerHTML = `
    <div class="bot-msg bot-msg-assistant">你好，我是 TestFlow 助手。可以问我测试流程、各阶段产出物或某条用例的含义。</div>
    <div class="bot-note">新对话已开始</div>
  `;
  if (botInput) botInput.value = "";
  markBotRead();
}

function saveLastResult(snapshot) {
  try { localStorage.setItem(LAST_RESULT_KEY, JSON.stringify(snapshot)); } catch (_) {}
}

function loadLastResult() {
  try {
    const raw = localStorage.getItem(LAST_RESULT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

function renderRequirements(spec) {
  const reqs = spec?.final_requirements || [];
  if (!reqs.length) {
    viewReq.innerHTML = "<em>暂无结构化需求</em>";
    return;
  }
  const rows = reqs
    .map((r) => `<tr><td>${esc(r.req_id)}</td><td>${esc(r.title)}</td><td>${esc(r.priority)}</td><td>${esc((r.rat_scope || []).join(", "))}</td><td>${esc((r.persona_sources || []).join(", "))}</td><td>${esc((r.acceptance?.pass_fail || []).join(" / "))}</td></tr>`)
    .join("");
  viewReq.innerHTML = `<table><thead><tr><th>需求ID</th><th>标题</th><th>优先级</th><th>RAT范围</th><th>评审来源</th><th>通过标准</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderReviewProcess(reviews) {
  const personas = [
    { key: "spec", label: "规范评审" },
    { key: "carrier", label: "运营商评审" },
    { key: "ux", label: "现网体验评审" },
  ];
  let html = "";
  personas.forEach((p) => {
    const items = reviews?.[p.key]?.reviews || [];
    if (!items.length) return;
    const rows = items
      .map((it) => `<tr><td>${esc(it.req_id)}</td><td>${esc((it.issues || []).join("；"))}</td><td>${esc((it.open_questions || []).join("；"))}</td></tr>`)
      .join("");
    html += `<h4>${p.label}</h4><table><thead><tr><th>需求ID</th><th>问题项</th><th>待确认问题</th></tr></thead><tbody>${rows}</tbody></table>`;
  });
  viewReview.innerHTML = html || "<em>暂无评审过程记录</em>";
}

function renderOpenQuestions(openQuestions = [], autoConfirmed = []) {
  const qItem = (q, auto) => {
    const key = `${q.req_id || "REQ"}::${q.question || ""}`;
    const pr = q.priority || "P1";
    const meta = [q.req_id, (q.personas || []).join("/") ? `${(q.personas || []).join("/")}评审` : ""].filter(Boolean).join(" · ");
    const hint = q.ai_answer
      ? `<div class="oq-ai"><span>AI ${auto ? "已采用" : "建议"}：</span>${esc(q.ai_answer)}${q.basis ? `<em>（依据：${esc(q.basis)}）</em>` : ""}</div>`
      : "";
    const placeholder = auto ? "如需修改，填写你的答案（留空则保持 AI 的答案）" : (q.ai_answer ? "留空则采纳 AI 建议" : "请输入你的确认/补充答案");
    return `<div class="oq-item"><div class="oq-q"><span class="prio prio-${esc(pr.toLowerCase())}">${esc(pr)}</span>${esc(q.question || "")}</div>
      <div class="oq-meta">${esc(meta)}</div>${hint}
      <input class="ui-input oq-answer" data-key="${esc(key)}" type="text" placeholder="${esc(placeholder)}" /></div>`;
  };
  const userHtml = openQuestions.length
    ? openQuestions.map((q) => qItem(q, false)).join("")
    : "<p class='feature-hint'>没有必须由你确认的问题，可以直接生成测试设计稿。</p>";
  const autoHtml = autoConfirmed.length
    ? `<details class="fold"><summary>AI 已自行确认 ${autoConfirmed.length} 个问题（按 3GPP 默认值 / 行业惯例，可修改）</summary>${autoConfirmed
        .map((q) => qItem(q, true))
        .join("")}</details>`
    : "";
  openQuestionsPanel.innerHTML = userHtml + autoHtml;
}

function collectOpenQuestionAnswers() {
  const answers = {};
  document.querySelectorAll(".oq-answer").forEach((el) => {
    const key = el.getAttribute("data-key");
    const value = (el.value || "").trim();
    if (key && value) answers[key] = value;
  });
  return answers;
}

function revokeDesignDocUrl() {
  if (latestDesignDocUrl) {
    URL.revokeObjectURL(latestDesignDocUrl);
    latestDesignDocUrl = "";
  }
}

function renderDocList(items = []) {
  const arr = Array.isArray(items) ? items.filter((x) => `${x || ""}`.trim()) : [];
  if (!arr.length) return "<p>无</p>";
  return `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
}

function renderDocKeyValueTable(rows = []) {
  const arr = Array.isArray(rows) ? rows.filter((x) => Array.isArray(x) && x.length >= 2) : [];
  if (!arr.length) return "<p>无</p>";
  return `<table><tbody>${arr.map((x) => `<tr><th>${esc(x[0])}</th><td>${esc(x[1])}</td></tr>`).join("")}</tbody></table>`;
}

function renderAnsweredQuestionsTable(items = []) {
  const rows = Array.isArray(items) ? items.filter((x) => x && typeof x === "object") : [];
  if (!rows.length) return "<p>无</p>";
  return `<table><thead><tr><th>来源轮次</th><th>需求ID</th><th>已确认问题</th><th>确认结果</th><th>确认方</th></tr></thead><tbody>${rows
    .map(
      (it) =>
        `<tr><td>${esc(it.source_round || "")}</td><td>${esc(it.req_id || "")}</td><td>${esc(it.question || "")}</td><td>${esc(
          it.answer || ""
        )}</td><td>${esc(it.source || "用户")}</td></tr>`
    )
    .join("")}</tbody></table>`;
}

function buildDesignDocumentHtml() {
  const design = stageState.test_design_spec || {};
  const requirementSpec = stageState.requirement_spec || {};
  const personaReviews = stageState.persona_reviews || {};
  const requirementReviewHistory = stageState.requirement_review_history || {};
  const requirementInputs = parseRequirements(requirementsEl?.value || "");
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  const nowText = new Date().toLocaleString("zh-CN", { hour12: false });
  const reqs = Array.isArray(requirementSpec.final_requirements) ? requirementSpec.final_requirements : [];
  const objectives = Array.isArray(design.objectives) ? design.objectives : [];
  const matrices = Array.isArray(design.coverage_matrices) ? design.coverage_matrices : [];
  const integrated = Array.isArray(design.integrated_matrix) ? design.integrated_matrix : [];
  const title = reqs[0]?.title || requirementInputs[0] || "测试设计文档";

  const reqTable = reqs.length
    ? `<table><thead><tr><th>需求ID</th><th>标题</th><th>优先级</th><th>RAT范围</th><th>通过标准</th></tr></thead><tbody>${reqs
        .map(
          (r) =>
            `<tr><td>${esc(r.req_id || "")}</td><td>${esc(r.title || "")}</td><td>${esc(r.priority || "")}</td><td>${esc(
              (r.rat_scope || []).join("、")
            )}</td><td>${esc(((r.acceptance || {}).pass_fail || []).join(" / "))}</td></tr>`
        )
        .join("")}</tbody></table>`
    : "<p>无</p>";

  const reviewSections = [
    ["规范评审", (personaReviews.spec || {}).reviews || []],
    ["运营商评审", (personaReviews.carrier || {}).reviews || []],
    ["现网体验评审", (personaReviews.ux || {}).reviews || []],
  ]
    .map(([label, items]) => {
      const list = Array.isArray(items) ? items : [];
      const body = list.length
        ? `<table><thead><tr><th>需求ID</th><th>问题项</th><th>待确认问题</th><th>改写建议</th></tr></thead><tbody>${list
            .map(
              (it) =>
                `<tr><td>${esc(it.req_id || "")}</td><td>${esc((it.issues || []).join("；"))}</td><td>${esc(
                  (it.open_questions || []).join("；")
                )}</td><td>${esc(it.rewrite_suggestion || "")}</td></tr>`
            )
            .join("")}</tbody></table>`
        : "<p>无</p>";
      return `<section><h3>${esc(label)}</h3>${body}</section>`;
    })
    .join("");

  const objectiveTable = objectives.length
    ? `<table><thead><tr><th>目标ID</th><th>关联需求</th><th>目标</th><th>成功标准</th><th>证据</th><th>优先级</th></tr></thead><tbody>${objectives
        .map(
          (o) =>
            `<tr><td>${esc(o.objective_id || "")}</td><td>${esc((o.linked_reqs || []).join("、"))}</td><td>${esc(
              o.goal || ""
            )}</td><td>${esc((o.success_criteria || []).join(" / "))}</td><td>${esc((o.evidence || []).join(" / "))}</td><td>${esc(
              o.priority || ""
            )}</td></tr>`
        )
        .join("")}</tbody></table>`
    : "<p>无</p>";

  const matrixText = matrices.length
    ? matrices
        .map((m) => {
          const dims = Array.isArray(m.dimensions)
            ? m.dimensions.map((d) => `${d.name || ""}: ${Array.isArray(d.values) ? d.values.join("、") : `${d.values || ""}`}`).join("<br/>")
            : "";
          const sampling = m.sampling_strategy || {};
          return `<article class="matrix-card"><h4>${esc(m.matrix_id || "覆盖矩阵")}</h4><div>${dims}</div><p><strong>采样策略：</strong>${esc(
            sampling.type || ""
          )}</p><p><strong>必选组合：</strong>${esc(JSON.stringify(sampling.must_include || [], null, 0))}</p><p><strong>排除组合：</strong>${esc(
            JSON.stringify(sampling.exclude || [], null, 0)
          )}</p></article>`;
        })
        .join("")
    : "<p>无</p>";

  const integratedTable = integrated.length
    ? `<table><thead><tr><th>行ID</th><th>需求ID</th><th>关联目标</th><th>测试场景</th><th>配置选取</th><th>通过标准</th><th>推荐测试环境</th><th>资源风险</th></tr></thead><tbody>${integrated
        .map((r, idx) => {
          const cfg = r.key_configuration || {};
          const cfgText = Object.keys(cfg)
            .map((k) => `${k}: ${cfg[k]}`)
            .join(" / ");
          const envText = formatTestEnvironmentSummary(r.test_environment);
          const riskText = formatTestEnvironmentRisk(r.test_environment);
          return `<tr><td>${esc(r.row_id || `ROW-${idx + 1}`)}</td><td>${esc(r.req_id || "")}</td><td>${esc(
            r.objective_id || ""
          )}</td><td>${esc(r.scenario || "")}</td><td>${esc(cfgText)}</td><td>${esc(
            (r.pass_criteria || []).join(" / ")
          )}</td><td>${esc(envText)}</td><td>${esc(riskText)}</td></tr>`;
        })
        .join("")}</tbody></table>`
    : "<p>无</p>";
  const answeredQuestionTable = renderAnsweredQuestionsTable(requirementReviewHistory.answered_questions || []);

  return `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${esc(title)} - 测试设计文档</title>
    <style>
      :root { color-scheme: light; }
      body { margin: 0; padding: 32px; font-family: "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background: #f4efe5; color: #1f2937; }
      .page { max-width: 1180px; margin: 0 auto; background: #fffdf8; border: 1px solid #e5dccd; border-radius: 18px; box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08); overflow: hidden; }
      .hero { padding: 28px 32px 24px; background: linear-gradient(135deg, #f6efe3 0%, #fffaf1 58%, #eef6f7 100%); border-bottom: 1px solid #e9ddcb; }
      .hero h1 { margin: 0; font-size: 30px; }
      .hero p { margin: 8px 0 0; color: #5b6472; }
      .section { padding: 24px 32px; border-top: 1px solid #efe6d8; }
      .section:first-of-type { border-top: none; }
      h2 { margin: 0 0 14px; font-size: 20px; }
      h3 { margin: 0 0 10px; font-size: 16px; }
      h4 { margin: 0 0 8px; font-size: 14px; }
      table { width: 100%; border-collapse: collapse; font-size: 13px; }
      th, td { border: 1px solid #e5dccd; padding: 9px 10px; text-align: left; vertical-align: top; }
      th { background: #f8f1e7; width: auto; }
      ul { margin: 8px 0 0 18px; }
      p { line-height: 1.7; margin: 8px 0; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
      .matrix-card { border: 1px solid #e7ddcf; border-radius: 12px; padding: 14px; background: #fff; margin-bottom: 12px; }
      .meta td:first-child, .meta th:first-child { width: 180px; }
      @media (max-width: 900px) { body { padding: 12px; } .section, .hero { padding: 18px; } .grid { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <div class="page">
      <section class="hero">
        <h1>标准测试设计文档</h1>
        <p>${esc(title)}</p>
      </section>
      <section class="section">
        <h2>一、文档信息</h2>
        ${renderDocKeyValueTable([
          ["生成时间", nowText],
          ["需求条目数", `${reqs.length}`],
          ["测试目标数", `${objectives.length}`],
          ["整合矩阵条目数", `${integrated.length}`],
        ])}
      </section>
      <section class="section">
        <h2>二、需求输入与产品背景</h2>
        <div class="grid">
          <div>
            <h3>原始需求输入</h3>
            ${renderDocList(requirementInputs)}
          </div>
          <div>
            <h3>产品通信背景与支持特性</h3>
            ${renderDocList((productProfile.profile_display || []).map((x) => `${x.group}: ${x.values.join("、")}`))}
          </div>
          <div>
            <h3>测试团队可用测试环境</h3>
            ${renderDocList(testEnvironments.display || [])}
          </div>
        </div>
      </section>
      <section class="section">
        <h2>三、测试需求解读稿</h2>
        ${reqTable}
      </section>
      <section class="section">
        <h2>四、三人评审记录</h2>
        ${reviewSections}
        <section>
          <h3>用户已确认问题</h3>
          ${answeredQuestionTable}
        </section>
      </section>
      <section class="section">
        <h2>五、测试目标</h2>
        ${objectiveTable}
      </section>
      <section class="section">
        <h2>六、覆盖矩阵</h2>
        ${matrixText}
      </section>
      <section class="section">
        <h2>七、整合覆盖矩阵</h2>
        ${integratedTable}
      </section>
      <section class="section">
        <h2>八、设计说明</h2>
        ${renderDocList(design.design_notes || [])}
      </section>
      <section class="section">
        <h2>九、范围裁剪与待跟进项</h2>
        <div class="grid">
          <div>
            <h3>去范围项</h3>
            ${renderDocList(design.de_scoped || [])}
          </div>
          <div>
            <h3>待确认问题</h3>
            ${renderDocList(requirementSpec.questions_to_ask || [])}
          </div>
        </div>
      </section>
    </div>
  </body>
</html>`;
}

function refreshDesignDocumentLink() {
  revokeDesignDocUrl();
  if (!stageState.test_design_spec) {
    designDocActions?.classList.add("hidden");
    if (designDocLink) designDocLink.removeAttribute("href");
    return;
  }
  if (stageState.design_history_doc_url) {
    if (designDocLink) {
      designDocLink.href = stageState.design_history_doc_url;
      designDocLink.title = "测试设计文档（固定URL）";
    }
    designDocActions?.classList.remove("hidden");
    return;
  }
  const title = (stageState.requirement_spec?.final_requirements || [])[0]?.title || "测试设计文档";
  const html = buildDesignDocumentHtml();
  latestDesignDocUrl = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
  if (designDocLink) {
    designDocLink.href = latestDesignDocUrl;
    designDocLink.title = `${title} - 测试设计文档`;
  }
  designDocActions?.classList.remove("hidden");
}

function renderDesign(design) {
  const objs = design?.objectives || [];
  const mats = design?.coverage_matrices || [];
  const integrated = design?.integrated_matrix || [];
  let html = "";

  if (objs.length) {
    const rows = objs.map((o) => `<tr><td>${esc(o.objective_id)}</td><td>${esc((o.linked_reqs || []).join(", "))}</td><td>${esc(o.goal)}</td><td>${esc((o.success_criteria || []).join(" / "))}</td><td>${esc(o.priority)}</td></tr>`).join("");
    html += `<h4>测试目标</h4><table><thead><tr><th>目标ID</th><th>关联需求</th><th>目标</th><th>成功标准</th><th>优先级</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  if (mats.length) {
    html += "<h4>覆盖矩阵</h4>";
    mats.forEach((m) => {
      const dims = Array.isArray(m.dimensions)
        ? m.dimensions.map((d) => `${d.name || "dimension"}: ${Array.isArray(d.values) ? d.values.join(", ") : String(d.values || "")}`).join("<br/>")
        : "";
      html += `<div><strong>${esc(m.matrix_id)}</strong><br/>${dims}</div>`;
    });
  }

  if (Array.isArray(integrated) && integrated.length) {
    const rows = integrated
      .map((r, idx) => {
        const cfg = r.key_configuration || {};
        const cfgStr = Object.keys(cfg).map((k) => `${k}: ${cfg[k]}`).join(" / ");
        const pass = Array.isArray(r.pass_criteria) ? r.pass_criteria.join(" / ") : String(r.pass_criteria || "");
        const envText = formatTestEnvironmentSummary(r.test_environment);
        const riskText = formatTestEnvironmentRisk(r.test_environment);
        return `<tr><td>${esc(r.row_id || `ROW-${idx + 1}`)}</td><td>${esc(r.req_id || "")}</td><td>${esc(r.objective_id || "")}</td><td>${esc(r.scenario || "")}</td><td>${esc(cfgStr)}</td><td>${esc(pass)}</td><td>${esc(envText)}</td><td>${esc(riskText)}</td></tr>`;
      })
      .join("");
    html += `<h4>整合覆盖矩阵</h4><table><thead><tr><th>行ID</th><th>需求ID</th><th>关联目标</th><th>具体测试场景</th><th>矩阵组合选取</th><th>通过标准</th><th>推荐测试环境</th><th>资源风险</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  if ((design?.design_notes || []).length) {
    html += `<h4>设计说明</h4><div>${design.design_notes.map((x) => `- ${esc(x)}`).join("<br/>")}</div>`;
  }

  if (design?.generation_meta) {
    html += `<h4>生成元信息</h4><div>测试设计由LLM生成：${esc(String(design.generation_meta.design_generated_by_llm))}<br/>整合覆盖矩阵由LLM生成：${esc(
      String(design.generation_meta.integrated_matrix_generated_by_llm)
    )}<br/>测试设计提示词：${esc(design.generation_meta.design_prompt || "")}<br/>整合矩阵提示词：${esc(
      design.generation_meta.integrated_prompt || ""
    )}</div>`;
  }

  viewDesign.innerHTML = html || "<em>暂无结构化设计</em>";
}

function renderCases(spec) {
  const tcs = spec?.testcases || [];
  if (!tcs.length) {
    viewCases.innerHTML = "<em>暂无结构化用例</em>";
    return;
  }
  const rows = tcs
    .map((tc) => {
      const tags = Array.isArray(tc.tags) ? tc.tags : [String(tc.tags || "")];
      const passFail = Array.isArray(tc.pass_fail) ? tc.pass_fail : [String(tc.pass_fail || "")];
      const envText = formatTestEnvironmentSummary(tc.test_environment);
      const riskText = formatTestEnvironmentRisk(tc.test_environment);
      return `<tr><td>${esc(tc.tc_id)}</td><td>${esc(tc.objective_id)}</td><td>${esc(tc.title)}</td><td>${esc(tags.join(", "))}</td><td>${esc(passFail.join(" / "))}</td><td>${esc(envText)}</td><td>${esc(riskText)}</td><td>${esc((tc.steps || []).length)}</td></tr>`;
    })
    .join("");
  viewCases.innerHTML = `<table><thead><tr><th>用例ID</th><th>目标ID</th><th>标题</th><th>标签</th><th>通过标准</th><th>测试环境</th><th>资源风险</th><th>步骤数</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderDesignHistoryList() {
  if (!designHistoryList) return;
  if (!designHistoryItems.length) {
    designHistoryList.innerHTML = "<em>暂无历史测试设计记录。</em>";
    return;
  }
  designHistoryList.innerHTML = `<div class="design-history-list">${designHistoryItems
    .map((item) => {
      const active = item.record_id === selectedDesignHistoryId ? "active" : "";
      const status = item.has_testcases ? "已生成测试用例" : "仅完成测试设计";
      return `<button class="design-history-item ${active}" data-record-id="${esc(item.record_id)}" type="button">
        <h4>${esc(item.title || item.record_id)}</h4>
        <p>更新时间：${esc(item.updated_at || "")}</p>
        <div class="design-history-chips">
          <span class="design-history-chip">${esc(status)}</span>
          <span class="design-history-chip">需求 ${esc(item.requirement_count || 0)}</span>
          <span class="design-history-chip">目标 ${esc(item.objective_count || 0)}</span>
          <span class="design-history-chip">矩阵 ${esc(item.matrix_row_count || 0)}</span>
          <span class="design-history-chip">用例 ${esc(item.testcase_count || 0)}</span>
        </div>
      </button>`;
    })
    .join("")}</div>`;
}

function renderDesignHistoryDetail(record) {
  selectedDesignHistoryRecord = record || null;
  if (!record) {
    if (designHistoryDetailTitle) designHistoryDetailTitle.textContent = "选择一条历史记录";
    if (designHistoryMeta) designHistoryMeta.innerHTML = "<em>选择左侧记录后，可查看固定URL文档、载入当前会话，或继续生成测试用例。</em>";
    if (designHistoryVisual) designHistoryVisual.innerHTML = "";
    if (designHistoryJson) designHistoryJson.textContent = "";
    if (designHistoryDocLink) {
      designHistoryDocLink.classList.add("hidden");
      designHistoryDocLink.removeAttribute("href");
    }
    if (designHistoryLoadBtn) designHistoryLoadBtn.disabled = true;
    if (designHistoryCasesBtn) designHistoryCasesBtn.disabled = true;
    return;
  }
  const summary = record.summary || {};
  if (designHistoryDetailTitle) designHistoryDetailTitle.textContent = record.title || record.record_id || "历史记录";
  if (designHistoryDocLink) {
    designHistoryDocLink.href = record.document_url || summary.document_url || "#";
    designHistoryDocLink.classList.remove("hidden");
  }
  if (designHistoryLoadBtn) designHistoryLoadBtn.disabled = false;
  if (designHistoryCasesBtn) {
    designHistoryCasesBtn.disabled = !record.test_design_spec;
    designHistoryCasesBtn.textContent = summary.has_testcases ? "重新生成测试用例" : "继续生成测试用例";
  }
  if (designHistoryMeta) {
    designHistoryMeta.innerHTML = `
      <div class="design-history-meta-grid">
        <div class="design-history-meta-card"><strong>记录ID</strong><span>${esc(record.record_id || "")}</span></div>
        <div class="design-history-meta-card"><strong>最近更新时间</strong><span>${esc(record.updated_at || "")}</span></div>
        <div class="design-history-meta-card"><strong>当前状态</strong><span>${esc(record.status || "")}</span></div>
        <div class="design-history-meta-card"><strong>固定URL文档</strong><span>${esc(record.document_url || summary.document_url || "")}</span></div>
      </div>
    `;
  }
  const reqs = Array.isArray(record.requirement_spec?.final_requirements) ? record.requirement_spec.final_requirements : [];
  const objectives = Array.isArray(record.test_design_spec?.objectives) ? record.test_design_spec.objectives : [];
  const integrated = Array.isArray(record.test_design_spec?.integrated_matrix) ? record.test_design_spec.integrated_matrix : [];
  const tcCount = Array.isArray(record.test_case_spec?.testcases) ? record.test_case_spec.testcases.length : 0;
  const answeredQuestions = Array.isArray(record.requirement_review_history?.answered_questions) ? record.requirement_review_history.answered_questions : [];
  const selectedTestEnvironments = Array.isArray(record.test_environments?.display)
    ? record.test_environments.display
    : Array.isArray(record.test_environments?.selected_details)
      ? record.test_environments.selected_details.map((env) => `${env.priority || ""}. ${env.label || ""}: ${env.description || ""}`.replace(/^\. /, ""))
      : [];
  if (designHistoryVisual) {
    const reqRows = reqs.length
      ? `<table><thead><tr><th>需求ID</th><th>标题</th><th>优先级</th></tr></thead><tbody>${reqs
          .map((r) => `<tr><td>${esc(r.req_id || "")}</td><td>${esc(r.title || "")}</td><td>${esc(r.priority || "")}</td></tr>`)
          .join("")}</tbody></table>`
      : "<p>无需求条目</p>";
    const objectiveRows = objectives.length
      ? `<table><thead><tr><th>目标ID</th><th>目标</th><th>优先级</th></tr></thead><tbody>${objectives
          .map((o) => `<tr><td>${esc(o.objective_id || "")}</td><td>${esc(o.goal || "")}</td><td>${esc(o.priority || "")}</td></tr>`)
          .join("")}</tbody></table>`
      : "<p>无测试目标</p>";
    designHistoryVisual.innerHTML = `
      <h4>记录概览</h4>
      <div class="design-history-chips">
        <span class="design-history-chip">需求 ${esc(reqs.length)}</span>
        <span class="design-history-chip">目标 ${esc(objectives.length)}</span>
        <span class="design-history-chip">整合矩阵 ${esc(integrated.length)}</span>
        <span class="design-history-chip">测试用例 ${esc(tcCount)}</span>
      </div>
      <h4>测试环境约束</h4>
      ${renderDocList(selectedTestEnvironments)}
      <h4>用户已确认问题</h4>
      ${renderAnsweredQuestionsTable(answeredQuestions)}
      <h4>需求摘要</h4>
      ${reqRows}
      <h4>测试目标摘要</h4>
      ${objectiveRows}
    `;
  }
  if (designHistoryJson) {
    designHistoryJson.textContent = JSON.stringify(record, null, 2);
  }
}

async function loadDesignHistory(preferredId = "") {
  const resp = await fetch("/api/design-history");
  if (!resp.ok) throw new Error(await resp.text() || "加载历史目录失败");
  const data = await resp.json();
  designHistoryItems = Array.isArray(data.items) ? data.items : [];
  renderDesignHistoryList();
  const targetId =
    preferredId ||
    selectedDesignHistoryId ||
    stageState.design_history_record_id ||
    (designHistoryItems[0] ? designHistoryItems[0].record_id : "");
  if (targetId) {
    await openDesignHistory(targetId);
  } else {
    renderDesignHistoryDetail(null);
  }
}

async function openDesignHistory(recordId) {
  if (!recordId) return;
  const resp = await fetch(`/api/design-history/${encodeURIComponent(recordId)}`);
  if (!resp.ok) throw new Error(await resp.text() || "加载历史记录失败");
  const record = await resp.json();
  selectedDesignHistoryId = record.record_id || recordId;
  renderDesignHistoryList();
  renderDesignHistoryDetail(record);
}

function applyHistoryRecordToCurrentSession(record) {
  if (!record) return;
  const reqInput = Array.isArray(record.requirement_input) ? record.requirement_input : [];
  if (requirementsEl) requirementsEl.value = reqInput[0] || "";
  setSelectedTestEnvironments(record.test_environments?.selected_ids || record.test_environments?.selected || []);
  setSelectedProductProfile(record.product_profile?.selected || {});
  stageState.requirement_spec = record.requirement_spec || null;
  stageState.persona_reviews = record.persona_reviews || null;
  stageState.requirement_review_history = record.requirement_review_history || null;
  stageState.test_design_spec = record.test_design_spec || null;
  stageState.test_case_spec = record.test_case_spec || null;
  stageState.executable_cases = record.executable_cases || null;
  stageState.design_history_record_id = record.record_id || "";
  stageState.design_history_doc_url = record.document_url || record.summary?.document_url || "";
  latestStructured = latestStructured || {};
  latestStructured.requirement_spec = record.requirement_spec || null;
  latestStructured.persona_reviews = record.persona_reviews || null;
  latestStructured.requirement_review_history = record.requirement_review_history || null;
  latestStructured.test_design_spec = record.test_design_spec || null;
  latestStructured.test_case_spec = record.test_case_spec || null;
  applyStageOutputs();
  persistCurrentState("已载入历史测试设计记录");
}

async function continueGenerateCasesFromHistory(recordId) {
  await openDesignHistory(recordId);
  if (!selectedDesignHistoryRecord) throw new Error("未找到历史记录");
  applyHistoryRecordToCurrentSession(selectedDesignHistoryRecord);
  await generateCases();
  await loadDesignHistory(recordId);
}

function applyStageOutputs() {
  if (stageState.requirement_spec) {
    outReq.textContent = JSON.stringify(stageState.requirement_spec, null, 2);
    renderRequirements(stageState.requirement_spec);
  }
  if (stageState.persona_reviews) {
    outReview.textContent = JSON.stringify(stageState.persona_reviews, null, 2);
    renderReviewProcess(stageState.persona_reviews);
  }
  if (stageState.test_design_spec) {
    outDesign.textContent = JSON.stringify(stageState.test_design_spec, null, 2);
    renderDesign(stageState.test_design_spec);
  }
  if (stageState.test_case_spec) {
    outCases.textContent = JSON.stringify(stageState.test_case_spec, null, 2);
    renderCases(stageState.test_case_spec);
  }
  renderExecutableCases(stageState.executable_cases);
  refreshDesignDocumentLink();
}

function restoreLastResultUI(snapshot) {
  if (!snapshot) return;
  requirementsEl.value = snapshot.form?.requirements || "";
  ragEl.value = snapshot.form?.rag || "";
  if (capabilityEl) capabilityEl.value = snapshot.form?.framework_capability_catalog || "";
  if (actionVocabEl) actionVocabEl.value = snapshot.form?.action_vocab || "";
  if (bzIdsEl) bzIdsEl.value = snapshot.form?.bz_ids || "";
  if (bzExcludedEl) bzExcludedEl.value = snapshot.form?.bz_excluded || "";
  setSelectedTestEnvironments(snapshot.form?.test_environment_selected || []);
  setSelectedProductProfile(snapshot.form?.product_profile_selected || {});
  statusEl.textContent = snapshot.status || "已恢复上次结果";

  latestStructured = snapshot.artifacts_structured || null;
  stageState.round = snapshot.stage_state?.round || 0;
  stageState.hitl_job_id = snapshot.stage_state?.hitl_job_id || "";
  stageState.requirement_spec = snapshot.stage_state?.requirement_spec || latestStructured?.requirement_spec || null;
  stageState.persona_reviews = snapshot.stage_state?.persona_reviews || latestStructured?.persona_reviews || null;
  stageState.requirement_review_history = snapshot.stage_state?.requirement_review_history || latestStructured?.requirement_review_history || null;
  stageState.test_design_spec = snapshot.stage_state?.test_design_spec || latestStructured?.test_design_spec || null;
  stageState.test_case_spec = snapshot.stage_state?.test_case_spec || latestStructured?.test_case_spec || null;
  stageState.executable_cases = snapshot.stage_state?.executable_cases || latestStructured?.executable_cases || null;
  stageState.bug_ids = Array.isArray(snapshot.stage_state?.bug_ids) ? snapshot.stage_state.bug_ids : [];
  stageState.design_history_record_id = snapshot.stage_state?.design_history_record_id || "";
  stageState.design_history_doc_url = snapshot.stage_state?.design_history_doc_url || "";
  ensureHitlStream(stageState.hitl_job_id);
  applyStageOutputs();
}

function persistCurrentState(customStatus) {
  saveLastResult({
    status: customStatus || statusEl.textContent,
    artifacts_structured: latestStructured || {},
    outputs: {
      test_requirements: outReq.textContent || "",
      review_process: outReview.textContent || "",
      test_design: outDesign.textContent || "",
      test_cases: outCases.textContent || "",
    },
    stage_state: stageState,
    form: {
      requirements: requirementsEl.value,
      rag: ragEl.value,
      framework_capability_catalog: capabilityEl?.value || "",
      action_vocab: actionVocabEl?.value || "",
      bz_ids: bzIdsEl?.value || "",
      bz_excluded: bzExcludedEl?.value || "",
      test_environment_selected: getSelectedTestEnvironments().selected_ids,
      product_profile_selected: getSelectedProductProfile().selected,
    },
  });
}

async function postJson(url, payload) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const t = await resp.text();
    try {
      const j = JSON.parse(t);
      if (j?.detail?.error || j?.detail?.failed_node) {
        const msg = [j.detail.failed_node ? `失败节点: ${j.detail.failed_node}` : null, j.detail.error ? `错误: ${j.detail.error}` : null]
          .filter(Boolean)
          .join("\n");
        throw new Error(msg || t || `HTTP ${resp.status}`);
      }
    } catch (e) {
      if (e instanceof Error && e.message) throw e;
    }
    throw new Error(t || `HTTP ${resp.status}`);
  }
  return await resp.json();
}

async function fetchRagDocs() {
  const resp = await fetch("/api/rag/docs");
  if (!resp.ok) throw new Error(await resp.text());
  const data = await resp.json();
  const docs = data.docs || [];
  if (!docs.length) {
    ragDocsEl.innerHTML = "<em>当前无已上传RAG文档</em>";
    return;
  }
  const items = docs
    .map((d) => `<li>${esc(d.filename)}（chunks: ${esc(String(d.chunk_count || 0))}）</li>`)
    .join("");
  ragDocsEl.innerHTML = `<ul class="rag-doc-list">${items}</ul>`;
}

async function uploadRagDocs() {
  const files = Array.from(ragFileEl.files || []);
  if (!files.length) throw new Error("请先选择至少一个文件");
  let ok = 0;
  const errors = [];
  for (const f of files) {
    try {
      const b64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const raw = String(reader.result || "");
          const idx = raw.indexOf("base64,");
          resolve(idx >= 0 ? raw.slice(idx + 7) : "");
        };
        reader.onerror = () => reject(reader.error || new Error("文件读取失败"));
        reader.readAsDataURL(f);
      });
      const resp = await fetch("/api/rag/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: f.name, content_base64: b64 }),
      });
      if (!resp.ok) {
        errors.push(`${f.name}: ${await resp.text()}`);
        continue;
      }
      ok += 1;
    } catch (e) {
      errors.push(`${f.name}: ${e.message || e}`);
    }
  }
  await fetchRagDocs();
  if (errors.length) {
    setStatus(`RAG上传完成：成功 ${ok}，失败 ${errors.length}\n- ${errors.join("\n- ")}`);
  } else {
    setStatus(`RAG上传完成：成功 ${ok}`);
  }
}

async function generateRequirementsRound(round) {
  const requirements = parseRequirements(requirementsEl.value);
  if (!requirements.length) throw new Error("请至少输入一条需求");
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  if (round <= 1) {
    stageState.requirement_review_history = null;
    if (latestStructured) latestStructured.requirement_review_history = null;
  }
  pushSystemBotMessage(`任务开始：测试需求评审 v${round}。`);
  let data = null;
  if (round <= 1 || !stageState.hitl_job_id) {
    data = await postJson("/api/hitl/requirements/start", {
      requirements,
      rag_context: ragEl.value,
      framework_capability_catalog: buildFrameworkCapabilityCatalog(),
      product_profile: productProfile,
      test_environments: testEnvironments,
    });
  } else {
    data = await postJson(`/api/hitl/requirements/${stageState.hitl_job_id}/next`, {
      open_question_answers: collectOpenQuestionAnswers(),
    });
  }
  stageState.hitl_job_id = data.job_id || stageState.hitl_job_id || "";
  ensureHitlStream(stageState.hitl_job_id);
  stageState.round = data.round;
  stageState.requirement_spec = data.requirement_spec;
  stageState.persona_reviews = data.persona_reviews;
  stageState.requirement_review_history = data.requirement_review_history || stageState.requirement_review_history || null;
  latestStructured = latestStructured || {};
  latestStructured.requirement_spec = data.requirement_spec;
  latestStructured.persona_reviews = data.persona_reviews;
  latestStructured.requirement_review_history = stageState.requirement_review_history;

  applyStageOutputs();
  renderOpenQuestions(data.open_questions || [], data.auto_confirmed || []);
  if ((data.open_questions || []).length) {
    pushSystemBotMessage(`测试需求评审 v${data.round} 已完成：${data.open_questions.length} 个关键问题需要你确认，另有 ${(data.auto_confirmed || []).length} 个问题 AI 已自行确认。`, { actionNeeded: true });
  } else {
    pushSystemBotMessage(`测试需求评审 v${data.round} 已完成。`);
  }
  setStatus(
    `测试需求评审完成：v${data.round}${data.is_final_round ? "（终稿）" : ""}` +
      (data.rag?.hits?.length ? `\nRAG命中: ${data.rag.hits.length} 条片段` : "\nRAG命中: 0") +
      (data.warnings?.length ? `\n告警:\n- ${data.warnings.join("\n- ")}` : "")
  );
  persistCurrentState();
}

async function generateDesign() {
  if (!stageState.requirement_spec) throw new Error("请先完成测试需求评审（至少v1）");
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  const data = await startStageJobAndWait("design", {
    requirement_input: parseRequirements(requirementsEl.value),
    requirement_spec: stageState.requirement_spec,
    persona_reviews: stageState.persona_reviews,
    requirement_review_history: stageState.requirement_review_history || {},
    product_profile: productProfile,
    test_environments: testEnvironments,
    history_record_id: stageState.design_history_record_id || "",
  });
  stageState.test_design_spec = data.test_design_spec;
  stageState.design_history_record_id = data.design_history?.record_id || stageState.design_history_record_id || "";
  stageState.design_history_doc_url = data.design_history?.document_url || stageState.design_history_doc_url || "";
  latestStructured = latestStructured || {};
  latestStructured.test_design_spec = data.test_design_spec;
  applyStageOutputs();
  if (stageState.design_history_record_id) {
    await loadDesignHistory(stageState.design_history_record_id).catch(() => {});
  }
  setStatus("测试设计稿已生成，并已归档到历史目录。");
  persistCurrentState();
}

async function generateCases() {
  if (!stageState.test_design_spec) throw new Error("请先生成测试设计稿");
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  const actionVocab = parseCSVLine(actionVocabEl?.value || "");
  const data = await startStageJobAndWait("testcases", {
    requirement_input: parseRequirements(requirementsEl.value),
    requirement_spec: stageState.requirement_spec,
    persona_reviews: stageState.persona_reviews,
    requirement_review_history: stageState.requirement_review_history || {},
    test_design_spec: stageState.test_design_spec,
    action_vocabulary: actionVocab,
    product_profile: productProfile,
    test_environments: testEnvironments,
    history_record_id: stageState.design_history_record_id || "",
  });
  stageState.test_case_spec = data.test_case_spec;
  stageState.design_history_record_id = data.design_history?.record_id || stageState.design_history_record_id || "";
  stageState.design_history_doc_url = data.design_history?.document_url || stageState.design_history_doc_url || "";
  latestStructured = latestStructured || {};
  latestStructured.test_case_spec = data.test_case_spec;
  applyStageOutputs();
  if (stageState.design_history_record_id) {
    await loadDesignHistory(stageState.design_history_record_id).catch(() => {});
  }
  setStatus("测试用例稿已生成。\n注：基于 integrated_matrix 分批生成。");
  persistCurrentState();
}

const EXEC_ROUTE_FILES = {
  artemis: "artemis-cases.json",
  at_agent: "at-agent-cases.json",
  amarisoft: "amarisoft-cases.json",
  protocol: "protocol-test-requirements.json",
};

const EXEC_ROUTE_HINTS = {
  artemis: "Artemis 验收测试中心 → 用例库 → 导入（artemis-case-library v1，profile=flash）",
  at_agent: "AT Agent 验收测试中心 → 用例库 → 导入（artemis-case-library v1，profile=at）",
  amarisoft: "交给 Amarisoft Agent：按 case 中的关键参数生成配置并控制模拟基站执行",
  protocol: "协议流程测试需求：供 PRTest 后续编写 XML 信令参数与 Python 流程",
};

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function renderExecutableCases(data) {
  if (!execCasesSummary) return;
  if (!data || !data.bundles) {
    execCasesSummary.innerHTML = "<em>尚未生成。完成测试用例后点击“生成可执行用例”。</em>";
    execCasesTrace.innerHTML = "";
    execCasesBundles.innerHTML = "";
    return;
  }
  const labels = data.route_labels || {};
  const summary = data.summary || {};
  execCasesSummary.innerHTML = `<table class="ui-table"><thead><tr><th>验收方案</th><th>用例数</th><th>可执行 case 数</th><th>去向</th><th></th></tr></thead><tbody>${
    Object.keys(EXEC_ROUTE_FILES).map((r) => {
      const bundle = data.bundles[r];
      const n = bundle ? (bundle.cases || bundle.items || []).length : 0;
      return `<tr><td>${esc(labels[r] || r)}</td><td>${esc(summary[r] || 0)}</td><td>${n}</td><td>${esc(EXEC_ROUTE_HINTS[r])}</td><td>${
        bundle ? `<button class="ui-btn ui-btn-secondary" type="button" data-exec-download="${r}">下载 JSON</button>` : ""
      }</td></tr>`;
    }).join("")
  }</tbody></table>
  <div class="btn-row"><button class="ui-btn ui-btn-secondary" type="button" data-exec-download="__all">下载全部（含追溯矩阵）</button></div>`;

  const rows = Array.isArray(data.traceability) ? data.traceability : [];
  execCasesTrace.innerHTML = rows.length
    ? `<table class="ui-table"><thead><tr><th>Bug</th><th>需求</th><th>测试目标</th><th>用例</th><th>测试环境</th><th>验收方案</th><th>可执行 case</th></tr></thead><tbody>${
        rows.map((r) => `<tr><td>${esc((r.bug_ids || []).join(", "))}</td><td>${esc((r.req_ids || []).join(", "))}<br/><span class="feature-hint">${esc((r.req_titles || []).join("；"))}</span></td><td>${esc(r.objective_id || "")}</td><td>${esc(r.tc_id || "")}<br/><span class="feature-hint">${esc(r.tc_title || "")}</span></td><td>${esc(r.test_environment || "")}</td><td>${esc(r.route_label || r.route || "")}</td><td>${esc((r.exec_case_ids || []).join(", "))}</td></tr>`).join("")
      }</tbody></table>`
    : "<em>无追溯数据</em>";

  execCasesBundles.innerHTML = Object.keys(EXEC_ROUTE_FILES)
    .filter((r) => data.bundles[r])
    .map((r) => `<details class="exec-bundle"><summary>${esc(labels[r] || r)}（${esc(EXEC_ROUTE_FILES[r])}）</summary>${
      r === "protocol" ? renderProtocolPreview(data.bundles[r]) : ""
    }<details class="raw-json"><summary>JSON</summary><pre class="ui-pre">${esc(JSON.stringify(data.bundles[r], null, 2))}</pre></details></details>`)
    .join("");
}

function renderProtocolPreview(bundle) {
  const items = Array.isArray(bundle?.items) ? bundle.items : [];
  const fmt = (v) => (typeof v === "object" && v !== null ? JSON.stringify(v) : `${v ?? ""}`);
  const shortPath = (p) => {
    const parts = `${p || ""}`.split(".");
    return parts.length > 3 ? `…${parts.slice(-3).join(".")}` : `${p || ""}`;
  };
  return items.map((it) => {
    const msgs = Array.isArray(it.message_configs) ? it.message_configs : [];
    const flow = Array.isArray(it.signaling_flow) ? it.signaling_flow : [];
    const msgHtml = msgs.length
      ? msgs.map((m) => `<div class="msg-config"><div class="msg-config-head"><span class="tag">${esc(m.msg_id || "")}</span><strong>${esc(m.message || "")}</strong>
          <span class="dir dir-${esc((m.direction || "").toLowerCase())}">${esc(m.direction || "")}</span><span class="feature-hint">${esc(m.purpose || "")}</span></div>
          <table class="ui-table"><thead><tr><th>IE 路径</th><th>取值</th><th>扫描参数</th><th>说明</th></tr></thead><tbody>${
            (m.ies || []).map((ie) => `<tr><td title="${esc(ie.path || "")}"><code>${esc(shortPath(ie.path))}</code></td><td><code>${esc(fmt(ie.value))}</code></td><td>${esc(ie.vary || "")}</td><td>${esc(ie.note || "")}</td></tr>`).join("")
          }</tbody></table></div>`).join("")
      : "<p class='feature-hint'>未生成关键消息配置</p>";
    const flowHtml = flow.length
      ? `<ol class="sig-flow">${flow.map((f) => `<li><span class="dir dir-${esc((f.direction || "").toLowerCase())}">${esc(f.direction || "")}</span> <strong>${esc(f.message || "")}</strong>${
          f.config_ref ? ` <span class="tag">${esc(f.config_ref)}</span>` : ""}${f.timing ? ` <span class="feature-hint">${esc(f.timing)}</span>` : ""}</li>`).join("")}</ol>`
      : "";
    return `<div class="proto-item"><h4>${esc(it.case_id || "")} ${esc(it.title || "")}</h4><p class="feature-hint">${esc(it.scenario || "")}</p>
      <div class="proto-grid"><div><h5>信令流程</h5>${flowHtml}</div><div><h5>关键消息配置</h5>${msgHtml}</div></div></div>`;
  }).join("");
}

async function generateExecCases() {
  if (!stageState.test_case_spec) throw new Error("请先生成测试用例稿");
  const data = await startStageJobAndWait("exec_cases", {
    requirement_spec: stageState.requirement_spec || {},
    test_case_spec: stageState.test_case_spec,
    product_profile: getSelectedProductProfile(),
    test_environments: getSelectedTestEnvironments(),
    bug_ids: stageState.bug_ids || [],
    history_record_id: stageState.design_history_record_id || "",
  });
  stageState.executable_cases = data.executable_cases || null;
  latestStructured = latestStructured || {};
  latestStructured.executable_cases = stageState.executable_cases;
  renderExecutableCases(stageState.executable_cases);
  const s = stageState.executable_cases?.summary || {};
  setStatus(`可执行用例已生成：Artemis ${s.artemis || 0}，AT Agent ${s.at_agent || 0}，Amarisoft ${s.amarisoft || 0}，协议流程 ${s.protocol || 0}` +
    (data.warnings?.length ? `\n告警:\n- ${data.warnings.join("\n- ")}` : ""));
  pushSystemBotMessage("可执行用例已生成，可在“可执行用例”页按验收方案下载。");
  persistCurrentState();
}

async function loadBugzillaSettings() {
  if (!bzUrlEl) return;
  const resp = await fetch("/api/bugzilla/settings");
  if (!resp.ok) return;
  const data = await resp.json();
  bzUrlEl.value = data.url || "";
  if (bzSettingsHint) bzSettingsHint.textContent = data.url ? (data.key_configured ? "已保存地址和 API Key" : "已保存地址（未配置 API Key）") : "未配置";
}

async function saveBugzillaSettings() {
  const data = await postJson("/api/bugzilla/settings", { url: bzUrlEl.value, api_key: bzKeyEl.value });
  bzKeyEl.value = "";
  if (bzSettingsHint) bzSettingsHint.textContent = data.key_configured ? "已保存地址和 API Key" : "已保存地址（未配置 API Key）";
  setStatus("Bugzilla 设置已保存");
}

async function fetchBugzillaRequirements() {
  const ids = (bzIdsEl?.value || "").trim();
  if (!ids) throw new Error("请填写 Bug 编号");
  const data = await postJson("/api/bugzilla/fetch", { ids, excluded_authors: bzExcludedEl?.value || "" });
  const bugs = Array.isArray(data.bugs) ? data.bugs : [];
  bzResult.innerHTML = bugs.map((b) => b.status === "ok"
    ? `<div>✓ <a href="${esc(b.url)}" target="_blank" rel="noopener noreferrer">BZ#${esc(b.id)}</a> ${esc(b.title || "")} <span class="feature-hint">${esc(b.product || "")} / ${esc(b.component || "")} · ${esc(b.bug_status || "")} · 评论 ${(b.comments || []).length} 条</span></div>`
    : `<div>✗ ${esc(b.requested_id)}：${esc(b.error || "读取失败")}</div>`).join("");
  if (data.requirement_text) {
    const current = (requirementsEl.value || "").trim();
    requirementsEl.value = current ? `${current}\n\n${data.requirement_text}` : data.requirement_text;
  }
  stageState.bug_ids = Array.from(new Set([...(stageState.bug_ids || []), ...(data.bug_ids || [])]));
  setStatus(`已从 Bugzilla 导入 ${(data.bug_ids || []).length} 条需求，内容已追加到需求描述。`);
  persistCurrentState();
}

async function loadPrompts() {
  const resp = await fetch("/api/settings/prompts");
  if (!resp.ok) throw new Error("加载模板失败");
  const data = await resp.json();
  promptCache = data.prompts || {};

  const names = Object.keys(promptCache).sort();
  promptSelect.innerHTML = "";
  names.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    promptSelect.appendChild(opt);
  });
  if (names.length) {
    promptSelect.value = names[0];
    promptEditor.value = promptCache[names[0]];
  } else {
    promptEditor.value = "";
  }
}

function renderPromptRoles(roles) {
  if (!roles || !roles.length) {
    flowPromptRoles.innerHTML = "<em>暂无Prompt角色映射</em>";
    return;
  }
  const rows = roles
    .map((r) => `<tr><td>${esc(r.role)}</td><td>${esc(r.node)}</td><td>${esc(r.prompt)}</td><td>${esc(r.exists ? "yes" : "no")}</td><td>${esc(r.first_line || "")}</td></tr>`)
    .join("");
  flowPromptRoles.innerHTML = `<table><thead><tr><th>Role</th><th>Node</th><th>Prompt</th><th>Exists</th><th>Preview</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderFlowGraph(graph, promptRoles = [], startNodeId = "") {
  // 流水线视图：按执行顺序把节点排成蛇形网格，Prompt 角色挂在节点下方，回流边用虚线弧标出。
  const nodes = graph?.nodes || [];
  const links = graph?.links || [];
  if (!nodes.length) {
    flowVizCanvas.innerHTML = "<em style='padding:16px;display:block'>暂无流程节点</em>";
    return;
  }

  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const order = [];
  const seen = new Set();
  const queue = [startNodeId && byId[startNodeId] ? startNodeId : nodes[0].id];
  while (queue.length) {
    const id = queue.shift();
    if (seen.has(id)) continue;
    seen.add(id);
    order.push(id);
    links.filter((l) => l.source === id && (l.action || "default") !== "retry").forEach((l) => queue.push(l.target));
  }
  nodes.forEach((n) => { if (!seen.has(n.id)) order.push(n.id); });

  const rolesByNode = {};
  (promptRoles || []).forEach((r) => {
    const nid = nodes.find((n) => n.label === r.node)?.id;
    if (nid) (rolesByNode[nid] = rolesByNode[nid] || []).push(r);
  });

  const width = Math.max(flowVizCanvas.clientWidth || 960, 640);
  const NODE_W = 184, NODE_H = 40, GAP_X = 36, ROLE_H = 34, PAD = 28, TOP = 56;
  const cols = Math.max(2, Math.floor((width - PAD * 2 + GAP_X) / (NODE_W + GAP_X)));
  const maxRoles = Math.max(0, ...Object.values(rolesByNode).map((r) => r.length));
  const rowH = NODE_H + 22 + maxRoles * (ROLE_H + 6) + 40;
  const rows = Math.ceil(order.length / cols);
  const height = TOP + PAD + rows * rowH - 30;
  const usedW = cols * NODE_W + (cols - 1) * GAP_X;
  const offsetX = Math.max(PAD, (width - usedW) / 2);

  const pos = {};
  order.forEach((id, i) => {
    const row = Math.floor(i / cols);
    let col = i % cols;
    if (row % 2 === 1) col = cols - 1 - col; // 蛇形排列，保证相邻节点挨着
    pos[id] = { x: offsetX + col * (NODE_W + GAP_X), y: TOP + row * rowH, idx: i };
  });

  const svgNS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs = {}, text) => {
    const e = document.createElementNS(svgNS, tag);
    Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const clip = (t, n) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);
  const css = getComputedStyle(document.documentElement);
  const c = (name) => css.getPropertyValue(name).trim();
  const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}` });
  const defs = el("defs");
  const marker = el("marker", { id: "flowArrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
  marker.appendChild(el("path", { d: "M0,0 L10,5 L0,10 z", fill: c("--muted-foreground") }));
  const markerBack = el("marker", { id: "flowArrowBack", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" });
  markerBack.appendChild(el("path", { d: "M0,0 L10,5 L0,10 z", fill: c("--warning") }));
  defs.append(marker, markerBack);
  svg.appendChild(defs);

  const edgeLayer = el("g");
  const nodeLayer = el("g");
  svg.append(edgeLayer, nodeLayer);

  links.forEach((l) => {
    const a = pos[l.source], b = pos[l.target];
    if (!a || !b) return;
    const back = b.idx <= a.idx;
    const action = l.action || "default";
    let d, lx, ly;
    if (!back && a.y === b.y) {
      const ltr = b.x > a.x;
      const x1 = ltr ? a.x + NODE_W : a.x, x2 = ltr ? b.x : b.x + NODE_W, y = a.y + NODE_H / 2;
      d = `M${x1},${y} L${x2 + (ltr ? -2 : 2)},${y}`;
      lx = (x1 + x2) / 2; ly = y - 6;
    } else if (!back) {
      // 换行：从行尾节点的外侧绕到下一行
      const right = a.x + NODE_W / 2 > width / 2;
      const xs = right ? a.x + NODE_W : a.x, xe = right ? b.x + NODE_W : b.x;
      const bulge = right ? Math.max(xs, xe) + 22 : Math.min(xs, xe) - 22;
      const ys = a.y + NODE_H / 2, ye = b.y + NODE_H / 2;
      d = `M${xs},${ys} C${bulge},${ys} ${bulge},${ye} ${xe + (right ? 2 : -2)},${ye}`;
      lx = bulge; ly = (ys + ye) / 2;
    } else {
      const x1 = a.x + NODE_W / 2, x2 = b.x + NODE_W / 2, y = Math.min(a.y, b.y);
      d = `M${x1},${a.y} C${x1},${y - 34} ${x2},${y - 34} ${x2},${b.y - 2}`;
      lx = (x1 + x2) / 2; ly = y - 26;
    }
    edgeLayer.appendChild(el("path", {
      d, fill: "none",
      stroke: back ? c("--warning") : c("--muted-foreground"),
      "stroke-width": back ? 1.4 : 1.4,
      "stroke-dasharray": back ? "5 4" : "",
      "stroke-opacity": back ? 0.9 : 0.6,
      "marker-end": back ? "url(#flowArrowBack)" : "url(#flowArrow)",
    }));
    if (action !== "default") {
      edgeLayer.appendChild(el("text", { x: lx, y: ly, "text-anchor": "middle", "font-size": 11, fill: back ? c("--warning") : c("--muted-foreground") }, action));
    }
  });

  order.forEach((id) => {
    const n = byId[id], p = pos[id];
    const isStart = id === startNodeId;
    const g = el("g", { transform: `translate(${p.x},${p.y})` });
    g.appendChild(el("rect", {
      width: NODE_W, height: NODE_H, rx: 9,
      fill: isStart ? c("--primary") : c("--card"),
      stroke: isStart ? c("--primary") : c("--input"), "stroke-width": 1.2,
    }));
    g.appendChild(el("text", {
      x: 12, y: NODE_H / 2 + 4, "font-size": 11, "font-weight": 700,
      fill: isStart ? "#fff" : c("--muted-foreground"),
    }, String(p.idx + 1).padStart(2, "0")));
    g.appendChild(el("text", {
      x: 34, y: NODE_H / 2 + 4, "font-size": 12, "font-weight": 600,
      fill: isStart ? "#fff" : c("--foreground"),
    }, String(n.label || "").replace(/Node$|Flow$/, "")));
    (rolesByNode[id] || []).forEach((r, i) => {
      const ry = NODE_H + 14 + i * (ROLE_H + 6);
      g.appendChild(el("line", { x1: 20, y1: NODE_H, x2: 20, y2: ry + ROLE_H / 2, stroke: c("--warning"), "stroke-opacity": 0.5, "stroke-dasharray": "3 3" }));
      g.appendChild(el("rect", { x: 30, y: ry, width: NODE_W - 30, height: ROLE_H, rx: 7, fill: c("--warning-soft"), stroke: c("--warning"), "stroke-opacity": 0.45 }));
      g.appendChild(el("text", { x: 40, y: ry + 14, "font-size": 11, "font-weight": 600, fill: c("--warning") }, clip(r.role || "Prompt", 24)));
      g.appendChild(el("text", { x: 40, y: ry + 27, "font-size": 10, fill: c("--muted-foreground") }, clip(r.prompt || "", 28)));
    });
    nodeLayer.appendChild(g);
  });

  flowVizCanvas.innerHTML = "";
  flowVizCanvas.style.height = `${height}px`;
  flowVizCanvas.appendChild(svg);
}

async function loadFlowVisualization() {
  const resp = await fetch("/api/settings/flow-visualization");
  if (!resp.ok) throw new Error(await resp.text());
  const data = await resp.json();
  flowMermaid.textContent = data.mermaid || "";
  renderPromptRoles(data.prompt_roles || []);
  renderFlowGraph(data.graph || {}, data.prompt_roles || [], data.graph?.start_node_id || "");
}

async function saveCurrentPrompt() {
  const name = promptSelect.value;
  if (!name) return;
  const body = { prompts: {} };
  body.prompts[name] = promptEditor.value;
  const resp = await fetch("/api/settings/prompts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error("保存模板失败");
  promptCache[name] = promptEditor.value;
}

async function downloadExcel() {
  if (!latestStructured?.test_case_spec) {
    setStatus("暂无可下载的测试用例");
    return;
  }
  const resp = await fetch("/api/export/testcases.xlsx", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requirement_input: parseRequirements(requirementsEl?.value || ""),
      requirement_spec: stageState.requirement_spec || latestStructured?.requirement_spec || {},
      persona_reviews: stageState.persona_reviews || latestStructured?.persona_reviews || {},
      requirement_review_history: stageState.requirement_review_history || latestStructured?.requirement_review_history || {},
      test_design_spec: stageState.test_design_spec || latestStructured?.test_design_spec || {},
      test_case_spec: latestStructured.test_case_spec,
      executable_cases: stageState.executable_cases || null,
    }),
  });
  if (!resp.ok) throw new Error(await resp.text());
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "testcases.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
  themeToggle.checked = theme === "dark";
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || "light";
  setTheme(saved);
}

function initTabs() {
  document.querySelectorAll(".sheet-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchSheetById(btn.getAttribute("data-sheet"));
    });
  });
}

function switchSheetById(id) {
  if (!id) return;
  document.querySelectorAll(".sheet-tab").forEach((b) => {
    b.classList.toggle("active", b.getAttribute("data-sheet") === id);
  });
  document.querySelectorAll(".sheet").forEach((s) => {
    s.classList.toggle("active", s.id === id);
  });
  if (id === "sheet6" && !flowVizLoaded) {
    loadFlowVisualization()
      .then(() => { flowVizLoaded = true; })
      .catch((e) => setStatus(`流程可视化加载失败: ${e.message}`));
  }
  if (id === "sheet8" && !designHistoryLoaded) {
    loadDesignHistory()
      .then(() => { designHistoryLoaded = true; })
      .catch((e) => setStatus(`测试设计历史加载失败: ${e.message}`));
  }
}

// bind events
runBtn.addEventListener("click", async () => {
  setSingleButtonBusy(runBtn, true, "生成中...");
  stageButtons.filter((b) => b !== runBtn).forEach((b) => b && (b.disabled = true));
  try {
    stageState.hitl_job_id = "";
    closeHitlStream();
    closeStageStream();
    setStatus("正在生成测试需求 v1 ...");
    await generateRequirementsRound(1);
    switchSheetById("sheet2");
  } catch (e) {
    setStatus(`执行失败: ${e.message}`);
    pushSystemBotMessage(`测试需求 v1 生成失败：${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(runBtn, false);
    stageButtons.filter((b) => b !== runBtn).forEach((b) => b && (b.disabled = false));
  }
});

regenReqBtn.addEventListener("click", async () => {
  setSingleButtonBusy(regenReqBtn, true, "生成中...");
  stageButtons.filter((b) => b !== regenReqBtn).forEach((b) => b && (b.disabled = true));
  try {
    if (!stageState.hitl_job_id) throw new Error("请先生成v1需求");
    const nextRound = Math.min((stageState.round || 1) + 1, 3);
    setStatus(`正在生成测试需求 v${nextRound} ...`);
    await generateRequirementsRound(nextRound);
    switchSheetById("sheet2");
  } catch (e) {
    setStatus(`再次生成失败: ${e.message}`);
    pushSystemBotMessage(`测试需求下一轮生成失败：${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(regenReqBtn, false);
    stageButtons.filter((b) => b !== regenReqBtn).forEach((b) => b && (b.disabled = false));
  }
});

genDesignBtn.addEventListener("click", async () => {
  setSingleButtonBusy(genDesignBtn, true, "生成中...");
  stageButtons.filter((b) => b !== genDesignBtn).forEach((b) => b && (b.disabled = true));
  try {
    setStatus("正在生成测试设计稿 ...");
    await generateDesign();
    switchSheetById("sheet3");
  } catch (e) {
    setStatus(`生成设计失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(genDesignBtn, false);
    stageButtons.filter((b) => b !== genDesignBtn).forEach((b) => b && (b.disabled = false));
  }
});

genCasesBtn.addEventListener("click", async () => {
  setSingleButtonBusy(genCasesBtn, true, "生成中...");
  stageButtons.filter((b) => b !== genCasesBtn).forEach((b) => b && (b.disabled = true));
  try {
    setStatus("正在生成测试用例稿 ...");
    await generateCases();
    switchSheetById("sheet4");
  } catch (e) {
    setStatus(`生成用例失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(genCasesBtn, false);
    stageButtons.filter((b) => b !== genCasesBtn).forEach((b) => b && (b.disabled = false));
  }
});

genExecCasesBtn.addEventListener("click", async () => {
  setSingleButtonBusy(genExecCasesBtn, true, "生成中...");
  stageButtons.filter((b) => b !== genExecCasesBtn).forEach((b) => b && (b.disabled = true));
  try {
    setStatus("正在生成可执行用例 ...");
    await generateExecCases();
    switchSheetById("sheet5");
  } catch (e) {
    setStatus(`生成可执行用例失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(genExecCasesBtn, false);
    stageButtons.filter((b) => b !== genExecCasesBtn).forEach((b) => b && (b.disabled = false));
  }
});

execCasesSummary?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-exec-download]");
  const data = stageState.executable_cases;
  if (!btn || !data?.bundles) return;
  const route = btn.dataset.execDownload;
  if (route === "__all") {
    downloadJson("executable-cases.json", data);
  } else if (data.bundles[route]) {
    downloadJson(EXEC_ROUTE_FILES[route] || `${route}.json`, data.bundles[route]);
  }
});

bzSaveBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(bzSaveBtn, true, "保存中...");
  try {
    await saveBugzillaSettings();
  } catch (e) {
    setStatus(`保存 Bugzilla 设置失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(bzSaveBtn, false);
  }
});

bzFetchBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(bzFetchBtn, true, "读取中...");
  try {
    await fetchBugzillaRequirements();
  } catch (e) {
    setStatus(`读取 Bugzilla 失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(bzFetchBtn, false);
  }
});

downloadExcelBtn.addEventListener("click", async () => {
  try {
    await downloadExcel();
  } catch (e) {
    setStatus(`下载Excel失败: ${e.message}`);
  }
});

refreshDesignHistoryBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(refreshDesignHistoryBtn, true, "刷新中...");
    await loadDesignHistory(selectedDesignHistoryId || stageState.design_history_record_id || "");
    designHistoryLoaded = true;
    setStatus("测试设计历史目录已刷新。");
  } catch (e) {
    setStatus(`测试设计历史刷新失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(refreshDesignHistoryBtn, false);
  }
});

designHistoryList?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-record-id]");
  if (!btn) return;
  const recordId = btn.getAttribute("data-record-id");
  openDesignHistory(recordId).catch((e) => setStatus(`历史记录加载失败: ${e.message}`));
});

designHistoryLoadBtn?.addEventListener("click", () => {
  if (!selectedDesignHistoryRecord) {
    setStatus("请先选择一条历史记录。");
    return;
  }
  applyHistoryRecordToCurrentSession(selectedDesignHistoryRecord);
  setStatus("已载入历史测试设计记录到当前会话。");
  switchSheetById(selectedDesignHistoryRecord.test_case_spec?.testcases?.length ? "sheet4" : "sheet3");
});

designHistoryCasesBtn?.addEventListener("click", async () => {
  if (!selectedDesignHistoryId) {
    setStatus("请先选择一条历史记录。");
    return;
  }
  try {
    setSingleButtonBusy(designHistoryCasesBtn, true, "生成中...");
    stageButtons.forEach((b) => b && (b.disabled = true));
    setStatus("正在基于历史测试设计生成测试用例稿 ...");
    await continueGenerateCasesFromHistory(selectedDesignHistoryId);
    switchSheetById("sheet4");
  } catch (e) {
    setStatus(`历史记录生成测试用例失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(designHistoryCasesBtn, false);
    stageButtons.forEach((b) => b && (b.disabled = false));
  }
});

function switchSettingsTab(name) {
  document.querySelectorAll(".settings-tab").forEach((b) => b.classList.toggle("active", b.dataset.settingsTab === name));
  document.querySelectorAll(".settings-pane").forEach((p) => p.classList.toggle("active", p.dataset.settingsPane === name));
}

async function openSettings(tab = "llm") {
  switchSettingsTab(tab);
  settingsModal.classList.remove("hidden");
  await Promise.all([
    loadLlmSettings().catch((e) => setStatus(`加载大模型设置失败: ${e.message}`)),
    loadBugzillaSettings().catch(() => {}),
    loadPrompts().catch((e) => setStatus(`加载模板失败: ${e.message}`)),
  ]);
}

function renderLlmStatus(data) {
  const ok = !!data?.enabled;
  llmStatusPill?.classList.toggle("ok", ok);
  if (llmStatusText) llmStatusText.textContent = ok ? data.model : "大模型未配置";
  if (llmStatusPill) llmStatusPill.title = ok ? `${data.api_base}\n点击修改` : "点击配置大模型";
  llmBanner?.classList.toggle("hidden", ok);
}

async function loadLlmSettings() {
  const resp = await fetch("/api/settings/llm");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  llmApiBaseEl.value = data.api_base || "";
  llmModelEl.value = data.model || "";
  llmTimeoutEl.value = data.timeout || 120;
  llmApiKeyEl.value = "";
  llmKeyHintEl.textContent = data.key_configured ? "（已保存，留空则沿用）" : "（未配置）";
  renderLlmStatus(data);
  return data;
}

function llmFormPayload(extra = {}) {
  return {
    api_base: llmApiBaseEl.value.trim(),
    model: llmModelEl.value.trim(),
    api_key: llmApiKeyEl.value.trim(),
    timeout: Number(llmTimeoutEl.value) || 120,
    ...extra,
  };
}

function showLlmTestResult(ok, text) {
  llmTestResultEl.classList.remove("hidden");
  llmTestResultEl.classList.toggle("ok", ok);
  llmTestResultEl.classList.toggle("err", !ok);
  llmTestResultEl.textContent = text;
}

async function saveLlmSettings(extra = {}) {
  await postJson("/api/settings/llm", llmFormPayload(extra));
  await loadLlmSettings();
}

settingsBtn.addEventListener("click", () => openSettings("llm"));
llmStatusPill?.addEventListener("click", () => openSettings("llm"));
document.getElementById("llmBannerBtn")?.addEventListener("click", () => openSettings("llm"));
document.querySelectorAll(".settings-tab").forEach((b) => b.addEventListener("click", () => switchSettingsTab(b.dataset.settingsTab)));
closeSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
settingsModal.addEventListener("click", (e) => { if (e.target === settingsModal) settingsModal.classList.add("hidden"); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") settingsModal.classList.add("hidden"); });
llmSaveBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(llmSaveBtn, true, "保存中...");
  try {
    await saveLlmSettings();
    showLlmTestResult(true, "已保存");
    setStatus("大模型设置已保存");
  } catch (e) {
    showLlmTestResult(false, `保存失败：${e.message}`);
  } finally {
    setSingleButtonBusy(llmSaveBtn, false);
  }
});
llmTestBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(llmTestBtn, true, "测试中...");
  try {
    const data = await postJson("/api/settings/llm/test", llmFormPayload());
    showLlmTestResult(true, `连接成功（${data.latency_ms} ms），模型回复：${data.reply || "(空)"}`);
  } catch (e) {
    showLlmTestResult(false, `连接失败：${e.message}`);
  } finally {
    setSingleButtonBusy(llmTestBtn, false);
  }
});
llmClearKeyBtn?.addEventListener("click", async () => {
  if (!confirm("确定清除已保存的 API Key？")) return;
  try {
    await saveLlmSettings({ api_key: "", clear_key: true });
    showLlmTestResult(true, "API Key 已清除");
  } catch (e) {
    showLlmTestResult(false, `清除失败：${e.message}`);
  }
});
reloadPromptsBtn.addEventListener("click", async () => {
  try { await loadPrompts(); } catch (e) { setStatus(`重载模板失败: ${e.message}`); }
});
savePromptBtn.addEventListener("click", async () => {
  try { await saveCurrentPrompt(); setStatus(`模板已保存: ${promptSelect.value}`); } catch (e) { setStatus(`保存模板失败: ${e.message}`); }
});
refreshFlowVizBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(refreshFlowVizBtn, true, "刷新中...");
    await loadFlowVisualization();
    flowVizLoaded = true;
  } catch (e) {
    setStatus(`流程可视化刷新失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(refreshFlowVizBtn, false);
  }
});
promptSelect.addEventListener("change", () => {
  const name = promptSelect.value;
  promptEditor.value = promptCache[name] || "";
});

themeToggle.addEventListener("change", () => setTheme(themeToggle.checked ? "dark" : "light"));
uploadRagBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(uploadRagBtn, true, "上传中...");
  try {
    await uploadRagDocs();
  } catch (e) {
    setStatus(`RAG上传失败: ${e.message}`);
    pushSystemBotMessage(`RAG 文档上传失败：${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(uploadRagBtn, false);
  }
});

botFab?.addEventListener("click", () => {
  botPanel?.classList.toggle("hidden");
  if (isBotPanelOpen()) markBotRead();
});

botCloseBtn?.addEventListener("click", () => {
  botPanel?.classList.add("hidden");
});

botRefreshBtn?.addEventListener("click", () => {
  resetBotConversation();
  setStatus("聊天机器人已开启新对话。");
  pushSystemBotMessage("已开启新对话。");
});

botSendBtn?.addEventListener("click", () => {
  sendBotMessage().catch((e) => setStatus(`机器人发送失败: ${e.message}`));
});

botInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    botSendBtn?.click();
  }
});

async function sendBotMessage() {
  const q = (botInput?.value || "").trim();
  if (!q) return;
  appendBotMessage("user", q);
  botHistory.push({ role: "user", content: q });
  botInput.value = "";
  setSingleButtonBusy(botSendBtn, true, "...");
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, history: botHistory }),
    });
    const text = await resp.text();
    if (!resp.ok) {
      let msg = text;
      try {
        const j = JSON.parse(text);
        msg = j?.detail || text;
      } catch (_) {}
      appendBotMessage("assistant", `请求失败: ${msg}`);
      return;
    }
    const data = JSON.parse(text);
    const reply = (data.reply || "").trim() || "收到，我再想想。";
    appendBotMessage("assistant", reply);
    botHistory.push({ role: "assistant", content: reply });
  } finally {
    setSingleButtonBusy(botSendBtn, false);
  }
}

goExecCasesBtn?.addEventListener("click", () => {
  switchSheetById("sheet5");
  genExecCasesBtn?.click();
});

// ---------- 对话修订面板 ----------
const REVIEW_STAGE_META = {
  requirements: { label: "测试需求稿", key: "requirement_spec", sheet: "sheet2" },
  design: { label: "测试设计稿", key: "test_design_spec", sheet: "sheet3" },
  testcases: { label: "测试用例稿", key: "test_case_spec", sheet: "sheet4" },
};
const REVIEW_ID_KEYS = {
  final_requirements: "req_id", objectives: "objective_id", coverage_matrices: "matrix_id",
  integrated_matrix: "row_id", testcases: "tc_id",
};
const REVIEW_OP_LABELS = { update: "修改", add: "新增", remove: "删除" };
const reviewDrawer = document.getElementById("reviewDrawer");
const reviewTitle = document.getElementById("reviewTitle");
const reviewMessages = document.getElementById("reviewMessages");
const reviewInput = document.getElementById("reviewInput");
const reviewSendBtn = document.getElementById("reviewSendBtn");
const reviewUndoBtn = document.getElementById("reviewUndoBtn");
const reviewState = {
  stage: "",
  chats: { requirements: [], design: [], testcases: [] },
  undo: { requirements: [], design: [], testcases: [] },
};

function reviewArtifact(stage) {
  return stageState[REVIEW_STAGE_META[stage].key];
}

function setReviewArtifact(stage, value) {
  const key = REVIEW_STAGE_META[stage].key;
  stageState[key] = value;
  latestStructured = latestStructured || {};
  latestStructured[key] = value;
  applyStageOutputs();
  persistCurrentState();
  syncReviewedArtifactToHistory(stage).catch(() => {});
}

async function syncReviewedArtifactToHistory(stage) {
  const id = stageState.design_history_record_id;
  if (!id) return;
  const key = REVIEW_STAGE_META[stage].key;
  const data = await postJson(`/api/design-history/${encodeURIComponent(id)}/artifacts`, { [key]: stageState[key] });
  if (data.design_history?.document_url) stageState.design_history_doc_url = data.design_history.document_url;
}

function applyReviewChanges(stage, changes) {
  const before = reviewArtifact(stage);
  const next = JSON.parse(JSON.stringify(before || {}));
  changes.forEach((ch) => {
    const idKey = REVIEW_ID_KEYS[ch.collection];
    if (!idKey) return;
    const list = Array.isArray(next[ch.collection]) ? next[ch.collection] : (next[ch.collection] = []);
    const idx = list.findIndex((x) => `${x?.[idKey] ?? ""}` === `${ch.target}`);
    if (ch.op === "update" && idx >= 0) list[idx] = ch.item;
    else if (ch.op === "add") idx >= 0 ? (list[idx] = ch.item) : list.push(ch.item);
    else if (ch.op === "remove" && idx >= 0) list.splice(idx, 1);
  });
  reviewState.undo[stage].push(before);
  setReviewArtifact(stage, next);
  reviewUndoBtn.disabled = false;
}

function renderReviewChat() {
  const stage = reviewState.stage;
  const chat = reviewState.chats[stage] || [];
  const intro = `<div class="bot-msg bot-msg-assistant">我已读取当前的${esc(REVIEW_STAGE_META[stage].label)}。可以问我某条为什么这样设计、哪里不合理，或者直接说要怎么改。</div>`;
  reviewMessages.innerHTML = intro + chat.map((m, i) => {
    if (m.role === "user") return `<div class="bot-msg bot-msg-user">${esc(m.content)}</div>`;
    if (m.role === "error") return `<div class="bot-msg bot-msg-system action-needed">${esc(m.content)}</div>`;
    const changes = m.changes || [];
    const cards = changes.length
      ? `<div class="review-changes">${changes.map((c) => `<div class="review-change"><span class="op op-${esc(c.op)}">${esc(REVIEW_OP_LABELS[c.op] || c.op)}</span><code>${esc(c.target)}</code><span>${esc(c.summary || "")}</span></div>`).join("")}
         <div class="btn-row">${m.status === "applied" ? "<span class='feature-hint'>✓ 已应用</span>" : m.status === "dismissed" ? "<span class='feature-hint'>已忽略</span>"
           : `<button class="ui-btn ui-btn-sm" data-review-apply="${i}">应用这 ${changes.length} 处修改</button><button class="ui-btn ui-btn-ghost ui-btn-sm" data-review-dismiss="${i}">忽略</button>`}</div></div>`
      : "";
    return `<div class="bot-msg bot-msg-assistant">${esc(m.content)}${cards}</div>`;
  }).join("") + (reviewState.pending ? `<div class="bot-msg bot-msg-assistant review-typing">AI 正在思考…</div>` : "");
  reviewMessages.scrollTop = reviewMessages.scrollHeight;
}

function openReviewDrawer(stage) {
  if (!reviewArtifact(stage)) {
    setStatus(`还没有${REVIEW_STAGE_META[stage].label}，请先生成。`);
    return;
  }
  reviewState.stage = stage;
  reviewTitle.textContent = `与 AI 讨论：${REVIEW_STAGE_META[stage].label}`;
  reviewUndoBtn.disabled = !reviewState.undo[stage].length;
  reviewDrawer.classList.remove("hidden");
  document.body.classList.add("review-open");
  renderReviewChat();
  reviewInput.focus();
}

async function sendReviewMessage() {
  const stage = reviewState.stage;
  const text = (reviewInput.value || "").trim();
  if (!stage || !text || reviewState.pending) return;
  const chat = reviewState.chats[stage];
  const history = chat.filter((m) => m.role === "user" || m.role === "assistant").map((m) => ({ role: m.role, content: m.content }));
  chat.push({ role: "user", content: text });
  reviewInput.value = "";
  reviewState.pending = true;
  reviewSendBtn.disabled = true;
  renderReviewChat();
  try {
    const data = await postJson("/api/review/chat", {
      stage,
      artifact: reviewArtifact(stage),
      message: text,
      history,
      context: {
        requirement_input: parseRequirements(requirementsEl.value),
        product_profile: getSelectedProductProfile().selected,
        test_environments: (getSelectedTestEnvironments().selected_details || []).map((x) => x.label),
        confirmed_answers: (stageState.requirement_review_history?.answered_questions || []).map((q) => ({ question: q.question, answer: q.answer })),
      },
    });
    chat.push({ role: "assistant", content: data.reply || "", changes: data.changes || [], status: "" });
  } catch (e) {
    chat.push({ role: "error", content: `请求失败：${e.message}` });
  } finally {
    reviewState.pending = false;
    reviewSendBtn.disabled = false;
    renderReviewChat();
  }
}

document.querySelectorAll("[data-review-stage]").forEach((b) => b.addEventListener("click", () => openReviewDrawer(b.dataset.reviewStage)));
document.getElementById("reviewCloseBtn")?.addEventListener("click", () => {
  reviewDrawer.classList.add("hidden");
  document.body.classList.remove("review-open");
});
reviewSendBtn?.addEventListener("click", () => sendReviewMessage());
reviewInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    sendReviewMessage();
  }
});
reviewMessages?.addEventListener("click", (e) => {
  const stage = reviewState.stage;
  const applyIdx = e.target.closest("[data-review-apply]")?.dataset.reviewApply;
  const dismissIdx = e.target.closest("[data-review-dismiss]")?.dataset.reviewDismiss;
  const msg = reviewState.chats[stage]?.[Number(applyIdx ?? dismissIdx)];
  if (!msg) return;
  if (applyIdx !== undefined) {
    applyReviewChanges(stage, msg.changes || []);
    msg.status = "applied";
    const downstream = stage === "requirements" ? "测试设计和用例" : stage === "design" ? "测试用例" : "可执行用例";
    setStatus(`已应用 ${msg.changes.length} 处修改到${REVIEW_STAGE_META[stage].label}。如需同步，请重新生成${downstream}。`);
  } else {
    msg.status = "dismissed";
  }
  renderReviewChat();
});
reviewUndoBtn?.addEventListener("click", () => {
  const stage = reviewState.stage;
  const prev = reviewState.undo[stage].pop();
  if (prev === undefined) return;
  setReviewArtifact(stage, prev);
  reviewUndoBtn.disabled = !reviewState.undo[stage].length;
  setStatus(`已撤销上次对${REVIEW_STAGE_META[stage].label}的修改。`);
});


// init
initTheme();
initTabs();
resetBotConversation();
renderTestEnvironmentOptions();
renderProductProfileOptions();
renderDesignHistoryDetail(null);
restoreLastResultUI(loadLastResult());
loadBugzillaSettings().catch(() => {});
loadLlmSettings().catch(() => {});
fetchRagDocs().catch((e) => setStatus(`加载RAG文档列表失败: ${e.message}`));

window.addEventListener("beforeunload", () => {
  revokeDesignDocUrl();
  closeHitlStream();
  closeStageStream();
});
