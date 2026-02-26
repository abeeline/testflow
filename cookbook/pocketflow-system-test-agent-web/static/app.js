const runBtn = document.getElementById("runBtn");
const regenReqBtn = document.getElementById("regenReqBtn");
const genDesignBtn = document.getElementById("genDesignBtn");
const genCasesBtn = document.getElementById("genCasesBtn");
const genScriptsBtn = document.getElementById("genScriptsBtn");
const debugScriptBtn = document.getElementById("debugScriptBtn");
const runOnlineBtn = document.getElementById("runOnlineBtn");
const loadAtAssetsBtn = document.getElementById("loadAtAssetsBtn");
const saveAtAssetsBtn = document.getElementById("saveAtAssetsBtn");
const runAtMbtBtn = document.getElementById("runAtMbtBtn");
const renderAtMbtGraphBtn = document.getElementById("renderAtMbtGraphBtn");
const compileAtBtn = document.getElementById("compileAtBtn");
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
const atSpecEditor = document.getElementById("atSpecEditor");
const atProfileEditor = document.getElementById("atProfileEditor");
const atManifestEditor = document.getElementById("atManifestEditor");
const atExtensionEditor = document.getElementById("atExtensionEditor");
const manifestFromJsonBtn = document.getElementById("manifestFromJsonBtn");
const manifestToJsonBtn = document.getElementById("manifestToJsonBtn");
const saveManifestBtn = document.getElementById("saveManifestBtn");
const mfBaseline = document.getElementById("mfBaseline");
const mfExtensionsList = document.getElementById("mfExtensionsList");
const mfMustList = document.getElementById("mfMustList");
const mfAllowedList = document.getElementById("mfAllowedList");
const mfDisableCapsList = document.getElementById("mfDisableCapsList");
const mfDisableCmdsList = document.getElementById("mfDisableCmdsList");
const mfAddExtBtn = document.getElementById("mfAddExtBtn");
const mfAddMustBtn = document.getElementById("mfAddMustBtn");
const mfAddAllowedBtn = document.getElementById("mfAddAllowedBtn");
const mfAddDisableCapBtn = document.getElementById("mfAddDisableCapBtn");
const mfAddDisableCmdBtn = document.getElementById("mfAddDisableCmdBtn");
const extFromJsonBtn = document.getElementById("extFromJsonBtn");
const extToJsonBtn = document.getElementById("extToJsonBtn");
const saveExtensionBtn = document.getElementById("saveExtensionBtn");
const extMetaId = document.getElementById("extMetaId");
const extMetaVersion = document.getElementById("extMetaVersion");
const extCapabilitiesList = document.getElementById("extCapabilitiesList");
const extCommandsList = document.getElementById("extCommandsList");
const extAddCapBtn = document.getElementById("extAddCapBtn");
const extAddCmdBtn = document.getElementById("extAddCmdBtn");
const atEfsmEditor = document.getElementById("atEfsmEditor");
const atMbtModeEl = document.getElementById("atMbtMode");
const atMbtMaxStepsEl = document.getElementById("atMbtMaxSteps");
const atMbtResultEl = document.getElementById("atMbtResult");
const atMbtGraphCanvas = document.getElementById("atMbtGraphCanvas");
const atCompileUseLlm = document.getElementById("atCompileUseLlm");
const atCompileReport = document.getElementById("atCompileReport");
const atActiveEfsmView = document.getElementById("atActiveEfsmView");
const atEffectiveAtspecView = document.getElementById("atEffectiveAtspecView");
const atEffectiveProfileView = document.getElementById("atEffectiveProfileView");
const atCommandSelector = document.getElementById("atCommandSelector");
const atCommandSelectionSummary = document.getElementById("atCommandSelectionSummary");
const atApplyCommandSelectionBtn = document.getElementById("atApplyCommandSelectionBtn");
const atConfigRequest = document.getElementById("atConfigRequest");
const atConfigCompileBtn = document.getElementById("atConfigCompileBtn");
const atChangeSpecView = document.getElementById("atChangeSpecView");
const atManifestPatchView = document.getElementById("atManifestPatchView");
const atExtensionPatchView = document.getElementById("atExtensionPatchView");

const requirementsEl = document.getElementById("requirements");
const ragEl = document.getElementById("rag");
const capabilityEl = document.getElementById("capability");
const capabilitiesJsonEl = document.getElementById("capabilitiesJson");
const actionVocabEl = document.getElementById("actionVocab");
const assertVocabEl = document.getElementById("assertVocab");
const modeAndroidEl = document.getElementById("modeAndroid");
const modeATEl = document.getElementById("modeAT");
const productProfileGroupsEl = document.getElementById("productProfileGroups");
const atBaudEl = document.getElementById("atBaud");
const adbDeviceSelectEl = document.getElementById("adbDeviceSelect");
const atPortSelectEl = document.getElementById("atPortSelect");
const refreshAdbBtn = document.getElementById("refreshAdbBtn");
const refreshSerialBtn = document.getElementById("refreshSerialBtn");
const automationExecModeEl = document.getElementById("automationExecMode");
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
const outCode = document.getElementById("outCode");
const outDebug = document.getElementById("outDebug");
const outRun = document.getElementById("outRun");
const agenticScriptMessages = document.getElementById("agenticScriptMessages");
const agenticScriptInput = document.getElementById("agenticScriptInput");
const agenticScriptSendBtn = document.getElementById("agenticScriptSendBtn");
const agenticScriptApplyBtn = document.getElementById("agenticScriptApplyBtn");
const agenticScriptClearBtn = document.getElementById("agenticScriptClearBtn");

const viewReq = document.getElementById("viewReq");
const viewReview = document.getElementById("viewReview");
const viewDesign = document.getElementById("viewDesign");
const viewCases = document.getElementById("viewCases");
const openQuestionsPanel = document.getElementById("openQuestionsPanel");
const downloadExcelBtn = document.getElementById("downloadExcelBtn");

const LAST_RESULT_KEY = "pocketflow_last_result_v2";
const THEME_KEY = "pocketflow_theme";
let promptCache = {};
let latestStructured = null;
let botHistory = [];
let botUnread = 0;
let flowVizLoaded = false;
let atAssetsLoaded = false;
let hitlStream = null;
let hitlStreamJobId = "";
let activeStageStream = null;
let activeStageJobId = "";
let agenticScriptHistory = [];
let latestAgenticCode = "";
let stageState = {
  requirement_spec: null,
  persona_reviews: null,
  test_design_spec: null,
  test_case_spec: null,
  round: 0,
  hitl_job_id: "",
  script_spec: null,
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

const stageButtons = [runBtn, regenReqBtn, genDesignBtn, genCasesBtn, genScriptsBtn, debugScriptBtn, runOnlineBtn];

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

function getSelectedAutomationModes() {
  const modes = [];
  if (modeAndroidEl?.checked) modes.push("android_adb");
  if (modeATEl?.checked) modes.push("at_serial");
  return modes;
}

function getAutomationProfile() {
  const selectedAdb = (adbDeviceSelectEl?.value || "").trim();
  const selectedAtPort = (atPortSelectEl?.value || "").trim();
  return {
    modes: getSelectedAutomationModes(),
    adb_device_id: selectedAdb,
    at_port: selectedAtPort,
    at_baud: Number(atBaudEl?.value || 115200) || 115200,
  };
}

function toProfileOptionId(groupKey, option) {
  return `pp_${groupKey}_${String(option).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "")}`;
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
    return `<div class="feature-profile-group"><h4>${esc(group.label)}</h4><div class="feature-option-grid">${items}</div></div>`;
  }).join("");
}

function getSelectedProductProfile() {
  const selected = {};
  const selectedFlat = [];
  PRODUCT_PROFILE_GROUPS.forEach((group) => {
    const values = [];
    group.options.forEach((opt) => {
      const id = toProfileOptionId(group.key, opt);
      const el = document.getElementById(id);
      if (el?.checked) {
        values.push(opt);
        selectedFlat.push(opt);
      }
    });
    if (values.length) selected[group.key] = values;
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
      const id = toProfileOptionId(group.key, opt);
      const el = document.getElementById(id);
      if (el) el.checked = values.includes(opt);
    });
  });
}

function setSelectOptions(selectEl, options, currentValue = "") {
  if (!selectEl) return;
  selectEl.innerHTML = "";
  options.forEach((opt) => {
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.label;
    selectEl.appendChild(o);
  });
  if (currentValue) {
    const match = options.some((x) => x.value === currentValue);
    if (match) selectEl.value = currentValue;
  }
}

async function fetchAdbDevices() {
  if (!adbDeviceSelectEl) return;
  setSingleButtonBusy(refreshAdbBtn, true, "刷新中...");
  try {
    const resp = await fetch("/api/devices/adb");
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    const devices = Array.isArray(data.devices) ? data.devices : [];
    const opts = [{ value: "", label: "未选择" }];
    devices.forEach((d) => {
      const label = `${d.id}${d.model ? ` (${d.model})` : ""} [${d.state || "unknown"}]`;
      opts.push({ value: d.id, label });
    });
    const current = (adbDeviceSelectEl?.value || "").trim();
    setSelectOptions(adbDeviceSelectEl, opts, current);
    if (!current && devices.length && adbDeviceSelectEl) adbDeviceSelectEl.value = devices[0].id || "";
  } catch (e) {
    setStatus(`ADB设备发现失败: ${e.message || e}`);
  } finally {
    setSingleButtonBusy(refreshAdbBtn, false);
  }
}

async function fetchSerialPorts() {
  if (!atPortSelectEl) return;
  setSingleButtonBusy(refreshSerialBtn, true, "刷新中...");
  try {
    const resp = await fetch("/api/devices/serial");
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    const ports = Array.isArray(data.ports) ? data.ports : [];
    const opts = [{ value: "", label: "未选择" }];
    ports.forEach((p) => {
      const label = `${p.device}${p.description ? ` (${p.description})` : ""}`;
      opts.push({ value: p.device, label });
    });
    const current = (atPortSelectEl?.value || "").trim();
    setSelectOptions(atPortSelectEl, opts, current);
    if (!current && ports.length && atPortSelectEl) atPortSelectEl.value = ports[0].device || "";
  } catch (e) {
    setStatus(`串口发现失败: ${e.message || e}`);
  } finally {
    setSingleButtonBusy(refreshSerialBtn, false);
  }
}

function getExecutionMode() {
  const preferred = (automationExecModeEl?.value || "auto").trim();
  if (preferred && preferred !== "auto") return preferred;
  const p = getAutomationProfile();
  return p.modes[0] || "";
}

function buildFrameworkCapabilityCatalog() {
  const base = (capabilityEl?.value || "").trim();
  const p = getAutomationProfile();
  const productProfile = getSelectedProductProfile();
  const productSummary = (productProfile.profile_display || [])
    .map((x) => `${x.group}: ${x.values.join(", ")}`)
    .join(" | ");
  const modeLabel = p.modes.map((m) => (m === "android_adb" ? "Android Web ADB" : "Web Serial AT")).join(", ");
  const extra = [
    `Automation Modes: ${modeLabel || "None"}`,
    p.adb_device_id ? `ADB Device: ${p.adb_device_id}` : "",
    p.at_port ? `AT Port: ${p.at_port} @ ${p.at_baud}` : "",
    productSummary ? `Product Profile: ${productSummary}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  return [base, extra].filter(Boolean).join("\n");
}

function inferCapabilitiesFromProfile() {
  const p = getAutomationProfile();
  const harnesses = [];
  const actionsSupported = {};
  if (p.modes.includes("android_adb")) {
    harnesses.push("WEB_ADB");
    actionsSupported.SET_DEVICE_STATE = ["adb"];
    actionsSupported.TRIGGER_REGISTRATION = ["adb"];
    actionsSupported.CHECK = ["adb_dumpsys"];
    actionsSupported.COLLECT_LOG = ["adb_logcat"];
  }
  if (p.modes.includes("at_serial")) {
    harnesses.push("WEB_SERIAL_AT");
    actionsSupported.SEND_AT = ["pyserial"];
    actionsSupported.TRIGGER_REGISTRATION = ["at"];
    actionsSupported.CHECK = ["at_creg"];
  }
  return { harnesses, actions_supported: actionsSupported };
}

function esc(s) {
  return String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
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
    <div class="bot-msg bot-msg-assistant">Welcome! I can help explain this test-agent workflow and output artifacts. What would you like to know?</div>
    <div class="bot-note">New conversation started!</div>
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

function normalizeScriptContextText(text, maxLen = 6000) {
  const s = String(text || "");
  if (!s) return "";
  if (s.length <= maxLen) return s;
  return `${s.slice(0, maxLen)}\n... [truncated ${s.length - maxLen} chars]`;
}

function buildAgenticScriptContext() {
  return {
    requirement_input: normalizeScriptContextText(requirementsEl?.value || "", 2000),
    test_case_spec_json: normalizeScriptContextText(outCases?.textContent || "", 12000),
    current_script_code: normalizeScriptContextText(outCode?.textContent || "", 16000),
    latest_debug_result: normalizeScriptContextText(outDebug?.textContent || "", 12000),
    latest_run_result: normalizeScriptContextText(outRun?.textContent || "", 12000),
    execution_mode: automationExecModeEl?.value || "auto",
  };
}

function extractLatestCodeBlock(text) {
  const t = String(text || "");
  const matches = [...t.matchAll(/```(?:python|py)?\s*([\s\S]*?)```/gi)];
  if (!matches.length) return "";
  const last = matches[matches.length - 1][1] || "";
  return last.trim();
}

function renderAgenticScriptMessages() {
  if (!agenticScriptMessages) return;
  if (!agenticScriptHistory.length) {
    agenticScriptMessages.innerHTML = `<div class="agentic-msg system">Agentic Coding 已就绪。你可以让 AI 生成/修改测试脚本，右侧联机调试结果会作为上下文用于 debug。</div>`;
    return;
  }
  agenticScriptMessages.innerHTML = agenticScriptHistory
    .map((m) => `<div class="agentic-msg ${m.role === "user" ? "user" : m.role === "assistant" ? "assistant" : "system"}">${esc(m.content || "")}</div>`)
    .join("");
  agenticScriptMessages.scrollTop = agenticScriptMessages.scrollHeight;
}

function pushAgenticScriptMessage(role, content) {
  agenticScriptHistory.push({ role, content: String(content || "") });
  const code = role === "assistant" ? extractLatestCodeBlock(content) : "";
  if (code) latestAgenticCode = code;
  renderAgenticScriptMessages();
  persistCurrentState();
}

async function sendAgenticScriptMessage() {
  const msg = (agenticScriptInput?.value || "").trim();
  if (!msg) return;
  pushAgenticScriptMessage("user", msg);
  agenticScriptInput.value = "";
  setSingleButtonBusy(agenticScriptSendBtn, true, "思考中...");
  try {
    const resp = await fetch("/api/agentic-coding/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        history: agenticScriptHistory.slice(-20),
        context: buildAgenticScriptContext(),
      }),
    });
    const text = await resp.text();
    if (!resp.ok) {
      let detail = text;
      try {
        detail = JSON.parse(text)?.detail || text;
      } catch (_) {}
      pushAgenticScriptMessage("system", `请求失败: ${detail}`);
      return;
    }
    const data = JSON.parse(text);
    const reply = String(data.reply || "").trim() || "未收到有效回复。";
    pushAgenticScriptMessage("assistant", reply);
  } catch (e) {
    pushAgenticScriptMessage("system", `请求异常: ${e.message || e}`);
  } finally {
    setSingleButtonBusy(agenticScriptSendBtn, false);
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
  viewReq.innerHTML = `<table><thead><tr><th>REQ ID</th><th>标题</th><th>优先级</th><th>RAT范围</th><th>persona_sources</th><th>通过标准</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderReviewProcess(reviews) {
  const personas = [
    { key: "spec", label: "Spec Lawyer" },
    { key: "carrier", label: "Carrier Reviewer" },
    { key: "ux", label: "UX Advocate" },
  ];
  let html = "";
  personas.forEach((p) => {
    const items = reviews?.[p.key]?.reviews || [];
    if (!items.length) return;
    const rows = items
      .map((it) => `<tr><td>${esc(it.req_id)}</td><td>${esc((it.issues || []).join("；"))}</td><td>${esc((it.open_questions || []).join("；"))}</td></tr>`)
      .join("");
    html += `<h4>${p.label}</h4><table><thead><tr><th>req_id</th><th>issues</th><th>open_questions</th></tr></thead><tbody>${rows}</tbody></table>`;
  });
  viewReview.innerHTML = html || "<em>暂无评审过程记录</em>";
}

function renderOpenQuestions(openQuestions = []) {
  if (!openQuestions.length) {
    openQuestionsPanel.innerHTML = "<em>当前无待人工确认问题。</em>";
    return;
  }
  openQuestionsPanel.innerHTML = openQuestions
    .map((q) => {
      const key = `${q.req_id || "REQ"}::${q.question || ""}`;
      return `<div class="oq-item"><div><strong>${esc(q.req_id || "")}</strong> ${esc(q.question || "")}</div><input class="oq-answer" data-key="${esc(key)}" type="text" placeholder="请输入你的确认/补充答案" /></div>`;
    })
    .join("");
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

function renderDesign(design) {
  const objs = design?.objectives || [];
  const mats = design?.coverage_matrices || [];
  const integrated = design?.integrated_matrix || [];
  let html = "";

  if (objs.length) {
    const rows = objs.map((o) => `<tr><td>${esc(o.objective_id)}</td><td>${esc((o.linked_reqs || []).join(", "))}</td><td>${esc(o.goal)}</td><td>${esc((o.success_criteria || []).join(" / "))}</td><td>${esc(o.priority)}</td></tr>`).join("");
    html += `<h4>测试目标</h4><table><thead><tr><th>Objective</th><th>关联需求</th><th>目标</th><th>成功标准</th><th>优先级</th></tr></thead><tbody>${rows}</tbody></table>`;
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
        return `<tr><td>${esc(r.row_id || `ROW-${idx + 1}`)}</td><td>${esc(r.req_id || "")}</td><td>${esc(r.objective_id || "")}</td><td>${esc(r.scenario || "")}</td><td>${esc(cfgStr)}</td><td>${esc(pass)}</td></tr>`;
      })
      .join("");
    html += `<h4>整合覆盖矩阵</h4><table><thead><tr><th>ID</th><th>REQ</th><th>关联目标</th><th>具体测试场景</th><th>矩阵组合选取</th><th>通过标准</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  if ((design?.design_notes || []).length) {
    html += `<h4>设计说明</h4><div>${design.design_notes.map((x) => `- ${esc(x)}`).join("<br/>")}</div>`;
  }

  if (design?.generation_meta) {
    html += `<h4>生成元信息</h4><div>design_generated_by_llm: ${esc(String(design.generation_meta.design_generated_by_llm))}<br/>integrated_matrix_generated_by_llm: ${esc(String(design.generation_meta.integrated_matrix_generated_by_llm))}<br/>design_prompt: ${esc(design.generation_meta.design_prompt || "")}<br/>integrated_prompt: ${esc(design.generation_meta.integrated_prompt || "")}</div>`;
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
      return `<tr><td>${esc(tc.tc_id)}</td><td>${esc(tc.objective_id)}</td><td>${esc(tc.title)}</td><td>${esc(tags.join(", "))}</td><td>${esc(passFail.join(" / "))}</td><td>${esc((tc.steps || []).length)}</td></tr>`;
    })
    .join("");
  viewCases.innerHTML = `<table><thead><tr><th>TC ID</th><th>Objective</th><th>标题</th><th>标签</th><th>通过标准</th><th>步骤数</th></tr></thead><tbody>${rows}</tbody></table>`;
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
}

function restoreLastResultUI(snapshot) {
  if (!snapshot) return;
  requirementsEl.value = snapshot.form?.requirements || "";
  ragEl.value = snapshot.form?.rag || "";
  capabilityEl.value = snapshot.form?.framework_capability_catalog || "";
  capabilitiesJsonEl.value = snapshot.form?.capabilities_json || "";
  actionVocabEl.value = snapshot.form?.action_vocab || "";
  assertVocabEl.value = snapshot.form?.assert_vocab || "";
  modeAndroidEl.checked = snapshot.form?.mode_android !== false;
  modeATEl.checked = !!snapshot.form?.mode_at;
  atBaudEl.value = snapshot.form?.at_baud || 115200;
  if (adbDeviceSelectEl) adbDeviceSelectEl.value = snapshot.form?.adb_device_id || "";
  if (atPortSelectEl) atPortSelectEl.value = snapshot.form?.at_port || "";
  if (automationExecModeEl) automationExecModeEl.value = snapshot.form?.exec_mode || "auto";
  setSelectedProductProfile(snapshot.form?.product_profile_selected || {});
  statusEl.textContent = snapshot.status || "已恢复上次结果";
  outCode.textContent = snapshot.outputs?.test_code_reference || "";
  outDebug.textContent = snapshot.outputs?.debug_result || "";
  outRun.textContent = snapshot.outputs?.run_result || "";
  agenticScriptHistory = Array.isArray(snapshot.outputs?.agentic_script_history) ? snapshot.outputs.agentic_script_history : [];
  latestAgenticCode = snapshot.outputs?.agentic_latest_code || "";
  if (agenticScriptInput) agenticScriptInput.value = snapshot.outputs?.agentic_draft_input || "";
  renderAgenticScriptMessages();
  atMbtResultEl.textContent = snapshot.outputs?.at_mbt_result || "";
  atSpecEditor.value = snapshot.outputs?.at_spec_editor || "";
  atProfileEditor.value = snapshot.outputs?.at_profile_editor || "";
  atManifestEditor.value = snapshot.outputs?.at_manifest_editor || "";
  atExtensionEditor.value = snapshot.outputs?.at_extension_editor || "";
  atEfsmEditor.value = snapshot.outputs?.at_efsm_editor || "";
  atCompileReport.textContent = snapshot.outputs?.at_compile_report || "";
  atActiveEfsmView.textContent = snapshot.outputs?.at_active_efsm || "";
  atEffectiveAtspecView.textContent = snapshot.outputs?.at_effective_atspec || "";
  atEffectiveProfileView.textContent = snapshot.outputs?.at_effective_profile || "";

  latestStructured = snapshot.artifacts_structured || null;
  stageState.round = snapshot.stage_state?.round || 0;
  stageState.hitl_job_id = snapshot.stage_state?.hitl_job_id || "";
  stageState.requirement_spec = snapshot.stage_state?.requirement_spec || latestStructured?.requirement_spec || null;
  stageState.persona_reviews = snapshot.stage_state?.persona_reviews || latestStructured?.persona_reviews || null;
  stageState.test_design_spec = snapshot.stage_state?.test_design_spec || latestStructured?.test_design_spec || null;
  stageState.test_case_spec = snapshot.stage_state?.test_case_spec || latestStructured?.test_case_spec || null;
  stageState.script_spec = snapshot.stage_state?.script_spec || latestStructured?.script_spec || null;
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
      test_code_reference: outCode.textContent || "",
      debug_result: outDebug.textContent || "",
      run_result: outRun.textContent || "",
      agentic_script_history: agenticScriptHistory || [],
      agentic_latest_code: latestAgenticCode || "",
      agentic_draft_input: agenticScriptInput?.value || "",
      at_mbt_result: atMbtResultEl.textContent || "",
      at_spec_editor: atSpecEditor.value || "",
      at_profile_editor: atProfileEditor.value || "",
      at_manifest_editor: atManifestEditor.value || "",
      at_extension_editor: atExtensionEditor.value || "",
      at_efsm_editor: atEfsmEditor.value || "",
      at_compile_report: atCompileReport.textContent || "",
      at_active_efsm: atActiveEfsmView.textContent || "",
      at_effective_atspec: atEffectiveAtspecView.textContent || "",
      at_effective_profile: atEffectiveProfileView.textContent || "",
    },
    stage_state: stageState,
    form: {
      requirements: requirementsEl.value,
      rag: ragEl.value,
      framework_capability_catalog: capabilityEl.value,
      capabilities_json: capabilitiesJsonEl.value,
      action_vocab: actionVocabEl.value,
      assert_vocab: assertVocabEl.value,
      mode_android: !!modeAndroidEl?.checked,
      mode_at: !!modeATEl?.checked,
      adb_device_id: adbDeviceSelectEl?.value || "",
      at_port: atPortSelectEl?.value || "",
      at_baud: atBaudEl?.value || "",
      exec_mode: automationExecModeEl?.value || "auto",
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

function renderStringList(container, values = []) {
  if (!container) return;
  const items = Array.isArray(values) ? values : [];
  container.innerHTML = "";
  items.forEach((val, idx) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const input = document.createElement("input");
    input.className = "ui-input";
    input.type = "text";
    input.value = String(val || "");
    input.dataset.idx = String(idx);
    const del = document.createElement("button");
    del.className = "ui-btn ui-btn-secondary";
    del.type = "button";
    del.textContent = "-";
    del.dataset.delIdx = String(idx);
    row.appendChild(input);
    row.appendChild(del);
    container.appendChild(row);
  });
}

function collectStringList(container) {
  if (!container) return [];
  return Array.from(container.querySelectorAll("input"))
    .map((x) => (x.value || "").trim())
    .filter((x) => !!x);
}

function addStringListItem(container, defaultValue = "") {
  const values = collectStringList(container);
  values.push(defaultValue);
  renderStringList(container, values);
}

function removeStringListItem(container, idx) {
  const values = collectStringList(container);
  values.splice(idx, 1);
  renderStringList(container, values);
}

function buildManifestFromForm() {
  return {
    baseline: (mfBaseline?.value || "").trim(),
    extensions: collectStringList(mfExtensionsList),
    policy: {
      must_have_capabilities: collectStringList(mfMustList),
      allowed_missing_capabilities: collectStringList(mfAllowedList),
    },
    test_scope: {
      enable_capabilities: ["*"],
      disable_capabilities: collectStringList(mfDisableCapsList),
      enable_commands: [],
      disable_commands: collectStringList(mfDisableCmdsList),
    },
    env: {},
  };
}

function fillManifestForm(manifest) {
  const m = manifest || {};
  if (mfBaseline) mfBaseline.value = m.baseline || "";
  renderStringList(mfExtensionsList, m.extensions || []);
  renderStringList(mfMustList, (m.policy || {}).must_have_capabilities || []);
  renderStringList(mfAllowedList, (m.policy || {}).allowed_missing_capabilities || []);
  renderStringList(mfDisableCapsList, (m.test_scope || {}).disable_capabilities || []);
  renderStringList(mfDisableCmdsList, (m.test_scope || {}).disable_commands || []);
}

function buildExtensionFromForm() {
  const capRows = Array.from(extCapabilitiesList?.querySelectorAll(".list-row") || []);
  const caps = capRows
    .map((row) => {
      const inputs = row.querySelectorAll("input");
      return { id: (inputs[0]?.value || "").trim(), desc: (inputs[1]?.value || "").trim() };
    })
    .filter((x) => x.id);

  const cmdRows = Array.from(extCommandsList?.querySelectorAll(".list-row") || []);
  const cmds = cmdRows
    .map((row) => {
      const inputs = row.querySelectorAll("input");
      const id = (inputs[0]?.value || "").trim();
      const capability = (inputs[1]?.value || "").trim();
      const at = (inputs[2]?.value || "").trim();
      if (!id) return null;
      return { id, capability, forms: { set: at }, responses: { ok: ["OK"], err: ["ERROR", "+CME ERROR:{err}"] } };
    })
    .filter(Boolean);

  return {
    meta: { id: (extMetaId?.value || "").trim(), version: (extMetaVersion?.value || "").trim() || "1.0" },
    capabilities: caps,
    commands: cmds,
  };
}

function renderExtensionCapabilities(caps = []) {
  if (!extCapabilitiesList) return;
  extCapabilitiesList.innerHTML = "";
  (Array.isArray(caps) ? caps : []).forEach((c, idx) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const idInput = document.createElement("input");
    idInput.className = "ui-input";
    idInput.placeholder = "capability id";
    idInput.value = c?.id || "";
    const descInput = document.createElement("input");
    descInput.className = "ui-input";
    descInput.placeholder = "desc";
    descInput.value = c?.desc || "";
    const del = document.createElement("button");
    del.className = "ui-btn ui-btn-secondary";
    del.type = "button";
    del.textContent = "-";
    del.dataset.capDelIdx = String(idx);
    row.appendChild(idInput);
    row.appendChild(descInput);
    row.appendChild(del);
    extCapabilitiesList.appendChild(row);
  });
}

function renderExtensionCommands(cmds = []) {
  if (!extCommandsList) return;
  extCommandsList.innerHTML = "";
  (Array.isArray(cmds) ? cmds : []).forEach((c, idx) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const idInput = document.createElement("input");
    idInput.className = "ui-input";
    idInput.placeholder = "command id";
    idInput.value = c?.id || "";
    const capInput = document.createElement("input");
    capInput.className = "ui-input";
    capInput.placeholder = "capability";
    capInput.value = c?.capability || "";
    const atInput = document.createElement("input");
    atInput.className = "ui-input";
    atInput.placeholder = "AT form(set)";
    atInput.value = (c?.forms || {}).set || "";
    const del = document.createElement("button");
    del.className = "ui-btn ui-btn-secondary";
    del.type = "button";
    del.textContent = "-";
    del.dataset.cmdDelIdx = String(idx);
    row.appendChild(idInput);
    row.appendChild(capInput);
    row.appendChild(atInput);
    row.appendChild(del);
    extCommandsList.appendChild(row);
  });
}

function fillExtensionForm(ext) {
  const e = ext || {};
  if (extMetaId) extMetaId.value = (e.meta || {}).id || "";
  if (extMetaVersion) extMetaVersion.value = (e.meta || {}).version || "1.0";
  renderExtensionCapabilities(e.capabilities || []);
  renderExtensionCommands(e.commands || []);
}

function getUncheckedAtCommandIds() {
  if (!atCommandSelector) return [];
  const ids = [];
  atCommandSelector.querySelectorAll("input[type='checkbox'][data-cmd-id]").forEach((cb) => {
    if (!cb.checked) ids.push(cb.getAttribute("data-cmd-id"));
  });
  return ids.filter(Boolean);
}

function updateAtCommandSelectionSummary() {
  if (!atCommandSelectionSummary) return;
  const all = atCommandSelector ? atCommandSelector.querySelectorAll("input[type='checkbox'][data-cmd-id]").length : 0;
  const disabled = getUncheckedAtCommandIds();
  atCommandSelectionSummary.innerHTML = `
    <div>总命令数：${all}，勾选：${Math.max(0, all - disabled.length)}，未勾选：${disabled.length}</div>
    <div>未勾选命令ID：${disabled.length ? esc(disabled.join(", ")) : "无"}</div>
  `;
}

function renderAtCommandSelector(spec, manifest) {
  if (!atCommandSelector) return;
  const commands = Array.isArray(spec?.commands) ? spec.commands.filter((c) => c && c.id) : [];
  const disabled = new Set(
    Array.isArray(manifest?.test_scope?.disable_commands) ? manifest.test_scope.disable_commands.map((x) => String(x)) : []
  );
  if (!commands.length) {
    atCommandSelector.innerHTML = "<em>ATSpec中暂无可展示命令。</em>";
    updateAtCommandSelectionSummary();
    return;
  }
  atCommandSelector.innerHTML = commands
    .map((c, i) => {
      const id = String(c.id || "");
      const desc = String(c.desc || c.title || c.name || id);
      const checked = !disabled.has(id) ? "checked" : "";
      return `<label style="display:block;margin:6px 0;">
        <input type="checkbox" data-cmd-id="${esc(id)}" ${checked} />
        <span>${i + 1}. ${esc(desc)}</span>
      </label>`;
    })
    .join("");
  updateAtCommandSelectionSummary();
}

function applyAtCommandSelectionToManifestEditor() {
  let manifest = {};
  try {
    manifest = JSON.parse(atManifestEditor.value || "{}");
  } catch (e) {
    throw new Error(`Manifest JSON解析失败: ${e.message || e}`);
  }
  if (!manifest.test_scope || typeof manifest.test_scope !== "object") manifest.test_scope = {};
  manifest.test_scope.disable_commands = getUncheckedAtCommandIds();
  atManifestEditor.value = JSON.stringify(manifest, null, 2);
  updateAtCommandSelectionSummary();
  persistCurrentState();
}

async function loadAtAgentAssets() {
  const [specResp, profileResp, manifestResp, extResp, efsmResp, buildResp] = await Promise.all([
    fetch("/api/at-agent/spec"),
    fetch("/api/at-agent/profile"),
    fetch("/api/at-agent/manifest"),
    fetch("/api/at-agent/extension"),
    fetch("/api/at-agent/efsm"),
    fetch("/api/at-agent/build"),
  ]);
  if (!specResp.ok) throw new Error(`加载ATSpec失败: ${await specResp.text()}`);
  if (!profileResp.ok) throw new Error(`加载Profile失败: ${await profileResp.text()}`);
  if (!manifestResp.ok) throw new Error(`加载Manifest失败: ${await manifestResp.text()}`);
  if (!extResp.ok) throw new Error(`加载Extension失败: ${await extResp.text()}`);
  if (!efsmResp.ok) throw new Error(`加载EFSM失败: ${await efsmResp.text()}`);
  const spec = await specResp.json();
  const profile = await profileResp.json();
  const manifest = await manifestResp.json();
  const extension = await extResp.json();
  const efsm = await efsmResp.json();
  atSpecEditor.value = JSON.stringify(spec, null, 2);
  atProfileEditor.value = JSON.stringify(profile, null, 2);
  atManifestEditor.value = JSON.stringify(manifest, null, 2);
  atExtensionEditor.value = JSON.stringify(extension, null, 2);
  atEfsmEditor.value = JSON.stringify(efsm, null, 2);
  renderAtCommandSelector(spec, manifest);
  if (atChangeSpecView) atChangeSpecView.textContent = "";
  if (atManifestPatchView) atManifestPatchView.textContent = "";
  if (atExtensionPatchView) atExtensionPatchView.textContent = "";
  fillManifestForm(manifest);
  fillExtensionForm(extension);
  if (buildResp.ok) {
    const build = await buildResp.json();
    atCompileReport.textContent = JSON.stringify(build.report || {}, null, 2);
    atActiveEfsmView.textContent = JSON.stringify(build.active_efsm || {}, null, 2);
    atEffectiveAtspecView.textContent = JSON.stringify(build.effective_atspec || {}, null, 2);
    atEffectiveProfileView.textContent = JSON.stringify(build.effective_profile || {}, null, 2);
    await renderAtMbtGraph(build.active_efsm || null);
  } else {
    atCompileReport.textContent = "";
    atActiveEfsmView.textContent = "";
    atEffectiveAtspecView.textContent = "";
    atEffectiveProfileView.textContent = "";
    await renderAtMbtGraph();
  }
  persistCurrentState();
}

async function resetAtAgentBaseline() {
  const data = await postJson("/api/at-agent/reset-baseline", {});
  atManifestEditor.value = JSON.stringify(data.manifest || {}, null, 2);
  atExtensionEditor.value = JSON.stringify(data.extension || {}, null, 2);
  try {
    const spec = JSON.parse(atSpecEditor.value || "{}");
    renderAtCommandSelector(spec, data.manifest || {});
  } catch (_) {}
  const compiled = data.compile_result || {};
  atCompileReport.textContent = JSON.stringify(compiled.report || {}, null, 2);
  atActiveEfsmView.textContent = JSON.stringify(compiled.active_efsm || {}, null, 2);
  atEffectiveAtspecView.textContent = JSON.stringify(compiled.effective_atspec || {}, null, 2);
  atEffectiveProfileView.textContent = JSON.stringify(compiled.effective_profile || {}, null, 2);
  await loadAtAgentAssets();
  setStatus("AT配置已重置为基线（Manifest/Extension）并重新编译。");
  pushSystemBotMessage("AT测试Agent: 已执行基线重置并更新模型。");
}

async function saveAtAgentAssets() {
  const spec = JSON.parse(atSpecEditor.value || "{}");
  const profile = JSON.parse(atProfileEditor.value || "{}");
  const manifest = JSON.parse(atManifestEditor.value || "{}");
  const extension = JSON.parse(atExtensionEditor.value || "{}");
  const efsm = JSON.parse(atEfsmEditor.value || "{}");
  await postJson("/api/at-agent/spec", { data: spec, locked_baseline: true });
  await postJson("/api/at-agent/profile", { data: profile });
  await postJson("/api/at-agent/manifest", { data: manifest });
  await postJson("/api/at-agent/extension", { data: extension });
  await postJson("/api/at-agent/efsm", { data: efsm });
  await renderAtMbtGraph();
  persistCurrentState();
}

async function compileAtArtifacts() {
  const data = await postJson("/api/at-agent/compile", {
    use_llm: !!atCompileUseLlm?.checked,
  });
  atCompileReport.textContent = JSON.stringify(data.report || {}, null, 2);
  atActiveEfsmView.textContent = JSON.stringify(data.active_efsm || {}, null, 2);
  atEffectiveAtspecView.textContent = JSON.stringify(data.effective_atspec || {}, null, 2);
  atEffectiveProfileView.textContent = JSON.stringify(data.effective_profile || {}, null, 2);
  await renderAtMbtGraph(data.active_efsm || null);
  setStatus("AT 编译完成：已生成 effective_atspec / effective_profile / active_efsm");
  pushSystemBotMessage("AT测试Agent: 编译完成，Active EFSM已更新。");
  persistCurrentState();
}

async function configCompileAtArtifacts() {
  const requestText = (atConfigRequest?.value || "").trim();
  if (!requestText) throw new Error("请先输入配置需求");
  const data = await postJson("/api/at-agent/config-compile", {
    request_text: requestText,
    use_llm: !!atCompileUseLlm?.checked,
    apply_changes: true,
    compile_after_apply: true,
  });

  atChangeSpecView.textContent = JSON.stringify(data.change_spec || {}, null, 2);
  atManifestPatchView.textContent = JSON.stringify(data.manifest_patch || [], null, 2);
  atExtensionPatchView.textContent = JSON.stringify(
    { extension_mode: data.extension_mode || "replace", extension_patch: data.extension_patch || [] },
    null,
    2
  );

  atManifestEditor.value = JSON.stringify(data.manifest || {}, null, 2);
  atExtensionEditor.value = JSON.stringify(data.extension || {}, null, 2);

  const compiled = data.compile_result || {};
  atCompileReport.textContent = JSON.stringify(compiled.report || {}, null, 2);
  atActiveEfsmView.textContent = JSON.stringify(compiled.active_efsm || {}, null, 2);
  atEffectiveAtspecView.textContent = JSON.stringify(compiled.effective_atspec || {}, null, 2);
  atEffectiveProfileView.textContent = JSON.stringify(compiled.effective_profile || {}, null, 2);
  await renderAtMbtGraph(compiled.active_efsm || null);

  setStatus(`AT配置已更新并编译完成（重试次数: ${data.retries_used || 1}）`);
  pushSystemBotMessage("AT测试Agent: Manifest/Extension 已通过LLM更新并完成编译。");
  persistCurrentState();
}

async function runAtMbtCoverage() {
  if (!atActiveEfsmView?.textContent?.trim()) {
    await compileAtArtifacts();
  }
  const mode = (atMbtModeEl?.value || "at_serial").trim();
  const maxSteps = Number(atMbtMaxStepsEl?.value || 20) || 20;
  const p = getAutomationProfile();
  const payload = {
    mode,
    max_steps: maxSteps,
    device_id: p.adb_device_id,
    at_port: p.at_port,
    baudrate: p.at_baud,
  };
  const data = await postJson("/api/at-agent/mbt/run", payload);
  atMbtResultEl.textContent = JSON.stringify(data, null, 2);
  setStatus(`AT MBT执行完成: 覆盖 ${data.coverage?.covered || 0}/${data.coverage?.total || 0}`);
  pushSystemBotMessage(`AT测试Agent: MBT执行完成，覆盖 ${data.coverage?.covered || 0}/${data.coverage?.total || 0}`);
  persistCurrentState();
}

async function renderAtMbtGraph(efsmOverride = null) {
  if (!atMbtGraphCanvas) return;
  atMbtGraphCanvas.innerHTML = "";

  let efsm = null;
  if (efsmOverride && typeof efsmOverride === "object") {
    efsm = efsmOverride;
  } else {
    try {
      const activeText = (atActiveEfsmView?.textContent || "").trim();
      efsm = activeText ? JSON.parse(activeText) : JSON.parse(atEfsmEditor?.value || "{}");
    } catch (e) {
      atMbtGraphCanvas.innerHTML = `<em>EFSM JSON 解析失败：${esc(e.message || e)}</em>`;
      return;
    }
  }
  const states = Array.isArray(efsm?.states) ? efsm.states.filter((s) => s && s.id) : [];
  const transitions = Array.isArray(efsm?.transitions)
    ? efsm.transitions.filter((t) => t && t.from && t.to && String(t.from) !== "*" && String(t.to) !== "*")
    : [];
  if (!states.length) {
    atMbtGraphCanvas.innerHTML = "<em>暂无可渲染状态（states 为空）</em>";
    return;
  }

  try {
    await ensureD3Loaded();
  } catch (_) {
    const lines = transitions.map((t) => `${t.from} -> ${t.to} [${t.id || ""}]`).join("<br/>");
    atMbtGraphCanvas.innerHTML = `<div style="padding:12px"><strong>MBT关系文本：</strong><br/>${lines || "无转移"}</div>`;
    return;
  }

  const d3 = window.d3;
  const width = atMbtGraphCanvas.clientWidth || 960;
  const height = atMbtGraphCanvas.clientHeight || 420;
  const svg = d3.select(atMbtGraphCanvas).append("svg").attr("width", width).attr("height", height);

  const nodeMap = new Map();
  states.forEach((s, idx) => {
    nodeMap.set(String(s.id), { id: String(s.id), isStart: idx === 0 });
  });

  const links = transitions.map((t) => ({
    source: String(t.from),
    target: String(t.to),
    label: t.id || "",
  }));

  links.forEach((l) => {
    if (!nodeMap.has(String(l.source))) {
      nodeMap.set(String(l.source), { id: String(l.source), isStart: false });
    }
    if (!nodeMap.has(String(l.target))) {
      nodeMap.set(String(l.target), { id: String(l.target), isStart: false });
    }
  });

  const nodes = Array.from(nodeMap.values());

  const simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance(130))
    .force("charge", d3.forceManyBody().strength(-580))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(44));

  svg
    .append("defs")
    .append("marker")
    .attr("id", "mbt-arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 18)
    .attr("refY", 0)
    .attr("markerWidth", 7)
    .attr("markerHeight", 7)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#60a5fa");

  const link = svg
    .append("g")
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("stroke", "#60a5fa")
    .attr("stroke-opacity", 0.9)
    .attr("stroke-width", 1.6)
    .attr("marker-end", "url(#mbt-arrow)");

  const linkLabel = svg
    .append("g")
    .selectAll("text")
    .data(links)
    .enter()
    .append("text")
    .text((d) => d.label)
    .attr("font-size", 10)
    .attr("fill", "#cbd5e1");

  const node = svg
    .append("g")
    .selectAll("g")
    .data(nodes)
    .enter()
    .append("g")
    .call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.25).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    );

  node
    .append("circle")
    .attr("r", 16)
    .attr("fill", (d) => (d.isStart ? "#16a34a" : "#0ea5b7"))
    .attr("stroke", "#e2e8f0")
    .attr("stroke-width", 1.2);

  node
    .append("text")
    .text((d) => d.id)
    .attr("text-anchor", "middle")
    .attr("dy", 30)
    .attr("font-size", 11)
    .attr("fill", "#cbd5e1");

  node
    .filter((d) => d.isStart)
    .append("text")
    .text("start")
    .attr("text-anchor", "middle")
    .attr("dy", 3)
    .attr("font-size", 8)
    .attr("font-weight", "700")
    .attr("fill", "#ecfdf5");

  simulation.on("tick", () => {
    nodes.forEach((d) => {
      d.x = Math.max(24, Math.min(width - 24, d.x || 24));
      d.y = Math.max(24, Math.min(height - 24, d.y || 24));
    });
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);
    linkLabel
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2 - 4);
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
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
  const profile = getAutomationProfile();
  const productProfile = getSelectedProductProfile();
  if (!profile.modes.length) throw new Error("请至少选择一种自动化测试方式（Android Web ADB 或 Web 串口 AT）");
  pushSystemBotMessage(`任务开始：测试需求评审 v${round}。`);
  let data = null;
  if (round <= 1 || !stageState.hitl_job_id) {
    data = await postJson("/api/hitl/requirements/start", {
      requirements,
      rag_context: ragEl.value,
      framework_capability_catalog: buildFrameworkCapabilityCatalog(),
      product_profile: productProfile,
      automation_modes: profile.modes,
      adb_device_id: profile.adb_device_id,
      at_port: profile.at_port,
      at_baudrate: profile.at_baud,
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
  latestStructured = latestStructured || {};
  latestStructured.requirement_spec = data.requirement_spec;
  latestStructured.persona_reviews = data.persona_reviews;

  applyStageOutputs();
  renderOpenQuestions(data.open_questions || []);
  if ((data.open_questions || []).length) {
    pushSystemBotMessage(`测试需求评审 v${data.round} 已完成，存在 ${data.open_questions.length} 个 Open Questions，等待人工补充后再进入下一轮。`, { actionNeeded: true });
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
  const data = await startStageJobAndWait("design", {
    requirement_spec: stageState.requirement_spec,
    persona_reviews: stageState.persona_reviews,
    product_profile: productProfile,
  });
  stageState.test_design_spec = data.test_design_spec;
  latestStructured = latestStructured || {};
  latestStructured.test_design_spec = data.test_design_spec;
  applyStageOutputs();
  setStatus("测试设计稿已生成（LLM严格模式）。");
  persistCurrentState();
}

async function generateCases() {
  if (!stageState.test_design_spec) throw new Error("请先生成测试设计稿");
  const productProfile = getSelectedProductProfile();
  const actionVocab = parseCSVLine(actionVocabEl.value);
  const data = await startStageJobAndWait("testcases", {
    requirement_spec: stageState.requirement_spec,
    test_design_spec: stageState.test_design_spec,
    action_vocabulary: actionVocab,
    product_profile: productProfile,
  });
  stageState.test_case_spec = data.test_case_spec;
  latestStructured = latestStructured || {};
  latestStructured.test_case_spec = data.test_case_spec;
  applyStageOutputs();
  setStatus("测试用例稿已生成。\n注：基于 integrated_matrix 分批生成。");
  persistCurrentState();
}

async function generateScripts() {
  if (!stageState.test_case_spec) throw new Error("请先生成测试用例稿");
  const productProfile = getSelectedProductProfile();
  let capabilities = null;
  if (capabilitiesJsonEl.value.trim()) {
    capabilities = JSON.parse(capabilitiesJsonEl.value);
  } else {
    capabilities = inferCapabilitiesFromProfile();
  }
  const assertVocab = parseCSVLine(assertVocabEl.value);
  const data = await startStageJobAndWait("scripts", {
    requirement_spec: stageState.requirement_spec,
    test_case_spec: stageState.test_case_spec,
    capabilities,
    assertion_vocabulary: assertVocab,
    product_profile: productProfile,
  });
  latestStructured = latestStructured || {};
  latestStructured.script_spec = data.script_spec;
  stageState.script_spec = data.script_spec;
  outCode.textContent = data.test_code_reference || "";
  pushAgenticScriptMessage("system", "右侧脚本参考已更新：已生成最新自动化脚本参考，可继续提问进行定向修改。");
  setStatus("测试脚本参考已生成。");
  persistCurrentState();
}

async function debugAutomationScript() {
  const profile = getAutomationProfile();
  const mode = getExecutionMode();
  if (!mode) throw new Error("请先在需求准备中选择至少一种自动化测试方式");
  const data = await postJson("/api/automation/debug", {
    mode,
    device_id: profile.adb_device_id,
    at_port: profile.at_port,
    baudrate: profile.at_baud,
    script_spec: stageState.script_spec || latestStructured?.script_spec || {},
  });
  outDebug.textContent = JSON.stringify(data, null, 2);
  pushAgenticScriptMessage("system", `右侧联机调试已完成：${data.ok ? "通过" : "失败"}。你可以要求我基于该结果修复脚本。`);
  setStatus(`联机调试完成：${data.ok ? "通过" : "失败"}`);
  pushSystemBotMessage(`联机调试完成：${data.ok ? "通过" : "失败"}`);
  persistCurrentState();
}

async function runAutomationOnline() {
  const profile = getAutomationProfile();
  const mode = getExecutionMode();
  if (!mode) throw new Error("请先在需求准备中选择至少一种自动化测试方式");
  if (!stageState.test_case_spec) throw new Error("缺少测试用例稿");
  const data = await postJson("/api/automation/run", {
    mode,
    device_id: profile.adb_device_id,
    at_port: profile.at_port,
    baudrate: profile.at_baud,
    test_case_spec: stageState.test_case_spec || {},
    script_spec: stageState.script_spec || latestStructured?.script_spec || {},
  });
  outRun.textContent = JSON.stringify(data, null, 2);
  pushAgenticScriptMessage("system", `右侧在线自动化执行完成：${data.summary?.passed || 0}/${data.summary?.total || 0} 通过。可据此继续优化脚本。`);
  setStatus(`在线自动化测试完成：${data.summary?.passed || 0}/${data.summary?.total || 0}`);
  pushSystemBotMessage(`在线自动化测试完成：${data.summary?.passed || 0}/${data.summary?.total || 0}`);
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

async function ensureD3Loaded() {
  if (window.d3) return;
  await new Promise((resolve, reject) => {
    const existing = document.querySelector("script[data-d3='1']");
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("D3加载失败")), { once: true });
      return;
    }
    const s = document.createElement("script");
    s.src = "https://d3js.org/d3.v7.min.js";
    s.async = true;
    s.dataset.d3 = "1";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("D3加载失败"));
    document.head.appendChild(s);
  });
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
  flowVizCanvas.innerHTML = "";
  const flowNodes = (graph?.nodes || []).map((n) => ({ ...n, type: "flow" }));
  const flowLinks = (graph?.links || []).map((l) => ({ ...l, kind: "flow" }));
  const labelToIds = {};
  flowNodes.forEach((n) => {
    if (!labelToIds[n.label]) labelToIds[n.label] = [];
    labelToIds[n.label].push(n.id);
  });

  const roleNodes = [];
  const roleLinks = [];
  (promptRoles || []).forEach((r, idx) => {
    const rid = `R${idx + 1}`;
    roleNodes.push({
      id: rid,
      type: "role",
      role: r.role || "Prompt Role",
      label: r.prompt || "prompt",
      nodeRef: r.node || "",
    });
    const targets = labelToIds[r.node] || [];
    if (targets.length) {
      roleLinks.push({
        source: targets[0],
        target: rid,
        action: "prompt",
        kind: "role",
      });
    }
  });

  const nodes = [...flowNodes, ...roleNodes];
  const links = [...flowLinks, ...roleLinks];
  if (!nodes.length) {
    flowVizCanvas.innerHTML = "<em>暂无流程节点</em>";
    return;
  }
  if (!window.d3) {
    const lines = links.map((l) => `${l.source} -> ${l.target} (${l.action})`).join("<br/>");
    flowVizCanvas.innerHTML = `<div style="padding:12px"><strong>D3未加载，展示文本关系：</strong><br/>${lines || "无边"}</div>`;
    return;
  }

  const d3 = window.d3;
  const width = flowVizCanvas.clientWidth || 920;
  const height = flowVizCanvas.clientHeight || 360;
  const FLOW_RADIUS = 17; // 24 * 0.7 ~= 17, shrink 30%
  const margin = 18;
  const svg = d3
    .select(flowVizCanvas)
    .append("svg")
    .attr("width", width)
    .attr("height", height);

  const simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance(130))
    .force("charge", d3.forceManyBody().strength(-560))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius((d) => (d.type === "role" ? 72 : 28)));

  const link = svg
    .append("g")
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("stroke", (d) => (d.kind === "role" ? "#f59e0b" : "#64748b"))
    .attr("stroke-opacity", 0.85)
    .attr("stroke-width", (d) => (d.kind === "role" ? 1.8 : 1.5))
    .attr("stroke-dasharray", (d) => (d.kind === "role" ? "6 4" : null));

  const linkLabel = svg
    .append("g")
    .selectAll("text")
    .data(links)
    .enter()
    .append("text")
    .text((d) => (d.kind === "role" ? "prompt" : (d.action || "default")))
    .attr("font-size", 11)
    .attr("fill", (d) => (d.kind === "role" ? "#fbbf24" : "#94a3b8"));

  const node = svg
    .append("g")
    .selectAll("g")
    .data(nodes)
    .enter()
    .append("g")
    .call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
    );

  const flowNode = node.filter((d) => d.type === "flow");
  const roleNode = node.filter((d) => d.type === "role");

  flowNode
    .append("circle")
    .attr("r", FLOW_RADIUS)
    .attr("fill", (d) => (d.id === startNodeId ? "#16a34a" : "#0ea5b7"))
    .attr("stroke", "#cbd5e1")
    .attr("stroke-width", 1.3);
  roleNode
    .append("rect")
    .attr("x", -66)
    .attr("y", -20)
    .attr("width", 132)
    .attr("height", 40)
    .attr("rx", 9)
    .attr("fill", "#3b2f11")
    .attr("stroke", "#f59e0b")
    .attr("stroke-width", 1.5);

  flowNode
    .append("text")
    .text((d) => d.label)
    .attr("text-anchor", "middle")
    .attr("dy", 31)
    .attr("font-size", 11)
    .attr("fill", "#cbd5e1");

  flowNode
    .filter((d) => d.id === startNodeId)
    .append("text")
    .text("start")
    .attr("text-anchor", "middle")
    .attr("dy", 4)
    .attr("font-size", 9)
    .attr("font-weight", "700")
    .attr("fill", "#ecfdf5");

  roleNode
    .append("text")
    .text((d) => d.role)
    .attr("text-anchor", "middle")
    .attr("dy", -2)
    .attr("font-size", 11)
    .attr("font-weight", "700")
    .attr("fill", "#fde68a");

  roleNode
    .append("text")
    .text((d) => d.label)
    .attr("text-anchor", "middle")
    .attr("dy", 12)
    .attr("font-size", 10)
    .attr("fill", "#f8fafc");

  simulation.on("tick", () => {
    nodes.forEach((d) => {
      const halfW = d.type === "role" ? 66 : FLOW_RADIUS;
      const halfH = d.type === "role" ? 20 : FLOW_RADIUS;
      const minX = margin + halfW;
      const maxX = width - margin - halfW;
      const minY = margin + halfH;
      const maxY = height - margin - halfH - (d.type === "flow" ? 18 : 0);
      d.x = Math.max(minX, Math.min(maxX, d.x || minX));
      d.y = Math.max(minY, Math.min(maxY, d.y || minY));
    });

    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    linkLabel.attr("x", (d) => (d.source.x + d.target.x) / 2).attr("y", (d) => (d.source.y + d.target.y) / 2);

    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
}

async function loadFlowVisualization() {
  const resp = await fetch("/api/settings/flow-visualization");
  if (!resp.ok) throw new Error(await resp.text());
  const data = await resp.json();
  flowMermaid.textContent = data.mermaid || "";
  renderPromptRoles(data.prompt_roles || []);
  try {
    await ensureD3Loaded();
  } catch (_) {}
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
      test_design_spec: stageState.test_design_spec || latestStructured?.test_design_spec || {},
      test_case_spec: latestStructured.test_case_spec,
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
  if (id === "sheet7" && !atAssetsLoaded) {
    loadAtAgentAssets()
      .then(() => { atAssetsLoaded = true; })
      .catch((e) => setStatus(`AT资产加载失败: ${e.message}`));
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

genScriptsBtn.addEventListener("click", async () => {
  setSingleButtonBusy(genScriptsBtn, true, "生成中...");
  stageButtons.filter((b) => b !== genScriptsBtn).forEach((b) => b && (b.disabled = true));
  try {
    setStatus("正在生成测试脚本参考 ...");
    await generateScripts();
    switchSheetById("sheet5");
  } catch (e) {
    setStatus(`生成脚本失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(genScriptsBtn, false);
    stageButtons.filter((b) => b !== genScriptsBtn).forEach((b) => b && (b.disabled = false));
  }
});

debugScriptBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(debugScriptBtn, true, "调试中...");
  stageButtons.filter((b) => b !== debugScriptBtn).forEach((b) => b && (b.disabled = true));
  try {
    await debugAutomationScript();
    switchSheetById("sheet5");
  } catch (e) {
    setStatus(`联机调试失败: ${e.message}`);
    pushSystemBotMessage(`联机调试失败：${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(debugScriptBtn, false);
    stageButtons.filter((b) => b !== debugScriptBtn).forEach((b) => b && (b.disabled = false));
  }
});

runOnlineBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(runOnlineBtn, true, "执行中...");
  stageButtons.filter((b) => b !== runOnlineBtn).forEach((b) => b && (b.disabled = true));
  try {
    await runAutomationOnline();
    switchSheetById("sheet5");
  } catch (e) {
    setStatus(`在线自动化测试失败: ${e.message}`);
    pushSystemBotMessage(`在线自动化测试失败：${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(runOnlineBtn, false);
    stageButtons.filter((b) => b !== runOnlineBtn).forEach((b) => b && (b.disabled = false));
  }
});

loadAtAssetsBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(loadAtAssetsBtn, true, "重置中...");
    await resetAtAgentBaseline();
    atAssetsLoaded = true;
  } catch (e) {
    setStatus(`AT资产加载失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(loadAtAssetsBtn, false);
  }
});

saveAtAssetsBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(saveAtAssetsBtn, true, "保存中...");
    await saveAtAgentAssets();
    setStatus("ATSpec(Profile锁定基线)/Manifest/Extension/EFSM 已保存。");
    pushSystemBotMessage("AT测试Agent: 规范与模型已保存。");
  } catch (e) {
    setStatus(`AT资产保存失败: ${e.message}`);
    pushSystemBotMessage(`AT资产保存失败: ${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(saveAtAssetsBtn, false);
  }
});

compileAtBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(compileAtBtn, true, "编译中...");
    await compileAtArtifacts();
  } catch (e) {
    setStatus(`AT编译失败: ${e.message}`);
    pushSystemBotMessage(`AT编译失败: ${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(compileAtBtn, false);
  }
});

atConfigCompileBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(atConfigCompileBtn, true, "处理中...");
    await configCompileAtArtifacts();
  } catch (e) {
    setStatus(`AT配置更新失败: ${e.message}`);
    pushSystemBotMessage(`AT配置更新失败: ${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(atConfigCompileBtn, false);
  }
});

atCommandSelector?.addEventListener("change", () => {
  updateAtCommandSelectionSummary();
});

atApplyCommandSelectionBtn?.addEventListener("click", () => {
  try {
    applyAtCommandSelectionToManifestEditor();
    setStatus("已将未勾选AT命令写入 Manifest.test_scope.disable_commands（仅预览，需保存后生效）");
  } catch (e) {
    setStatus(`应用命令勾选失败: ${e.message || e}`);
  }
});

runAtMbtBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(runAtMbtBtn, true, "执行中...");
    await runAtMbtCoverage();
  } catch (e) {
    setStatus(`AT MBT执行失败: ${e.message}`);
    pushSystemBotMessage(`AT MBT执行失败: ${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(runAtMbtBtn, false);
  }
});

renderAtMbtGraphBtn?.addEventListener("click", async () => {
  try {
    setSingleButtonBusy(renderAtMbtGraphBtn, true, "绘制中...");
    await renderAtMbtGraph();
    setStatus("MBT模型图已更新。");
  } catch (e) {
    setStatus(`MBT模型图绘制失败: ${e.message}`);
  } finally {
    setSingleButtonBusy(renderAtMbtGraphBtn, false);
  }
});

manifestFromJsonBtn?.addEventListener("click", () => {
  try {
    const m = JSON.parse(atManifestEditor.value || "{}");
    fillManifestForm(m);
    setStatus("Manifest: 已从JSON载入到结构化UI。");
  } catch (e) {
    setStatus(`Manifest JSON解析失败: ${e.message}`);
  }
});

manifestToJsonBtn?.addEventListener("click", () => {
  try {
    const m = buildManifestFromForm();
    atManifestEditor.value = JSON.stringify(m, null, 2);
    setStatus("Manifest: 结构化UI已应用到JSON。");
    persistCurrentState();
  } catch (e) {
    setStatus(`Manifest 表单转JSON失败: ${e.message}`);
  }
});

saveManifestBtn?.addEventListener("click", async () => {
  try {
    const m = buildManifestFromForm();
    atManifestEditor.value = JSON.stringify(m, null, 2);
    await postJson("/api/at-agent/manifest", { data: m });
    setStatus("Manifest 已保存。");
    persistCurrentState();
  } catch (e) {
    setStatus(`Manifest 保存失败: ${e.message}`);
  }
});

extFromJsonBtn?.addEventListener("click", () => {
  try {
    const e = JSON.parse(atExtensionEditor.value || "{}");
    fillExtensionForm(e);
    setStatus("Extension: 已从JSON载入到结构化UI。");
  } catch (err) {
    setStatus(`Extension JSON解析失败: ${err.message}`);
  }
});

extToJsonBtn?.addEventListener("click", () => {
  try {
    const e = buildExtensionFromForm();
    atExtensionEditor.value = JSON.stringify(e, null, 2);
    setStatus("Extension: 结构化UI已应用到JSON。");
    persistCurrentState();
  } catch (err) {
    setStatus(`Extension 表单转JSON失败: ${err.message}`);
  }
});

saveExtensionBtn?.addEventListener("click", async () => {
  try {
    const e = buildExtensionFromForm();
    atExtensionEditor.value = JSON.stringify(e, null, 2);
    await postJson("/api/at-agent/extension", { data: e });
    setStatus("Extension 已保存。");
    persistCurrentState();
  } catch (err) {
    setStatus(`Extension 保存失败: ${err.message}`);
  }
});

mfAddExtBtn?.addEventListener("click", () => addStringListItem(mfExtensionsList, "atspec.vendor.xxx@1.0"));
mfAddMustBtn?.addEventListener("click", () => addStringListItem(mfMustList, "capability.id"));
mfAddAllowedBtn?.addEventListener("click", () => addStringListItem(mfAllowedList, "capability.id"));
mfAddDisableCapBtn?.addEventListener("click", () => addStringListItem(mfDisableCapsList, "capability.id"));
mfAddDisableCmdBtn?.addEventListener("click", () => addStringListItem(mfDisableCmdsList, "COMMAND_ID"));

extAddCapBtn?.addEventListener("click", () => {
  const current = buildExtensionFromForm();
  current.capabilities.push({ id: "vendor.cap.new", desc: "new vendor capability" });
  fillExtensionForm(current);
});

extAddCmdBtn?.addEventListener("click", () => {
  const current = buildExtensionFromForm();
  current.commands.push({
    id: "VENDOR_CMD_NEW",
    capability: "vendor.cap.new",
    forms: { set: "AT+VENDOR={x}" },
    responses: { ok: ["OK"], err: ["ERROR", "+CME ERROR:{err}"] },
  });
  fillExtensionForm(current);
});

[mfExtensionsList, mfMustList, mfAllowedList, mfDisableCapsList, mfDisableCmdsList].forEach((container) => {
  container?.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-del-idx]");
    if (!btn) return;
    const idx = Number(btn.dataset.delIdx || -1);
    if (idx < 0) return;
    removeStringListItem(container, idx);
  });
});

extCapabilitiesList?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-cap-del-idx]");
  if (!btn) return;
  const idx = Number(btn.dataset.capDelIdx || -1);
  if (idx < 0) return;
  const cur = buildExtensionFromForm();
  cur.capabilities.splice(idx, 1);
  fillExtensionForm(cur);
});

extCommandsList?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-cmd-del-idx]");
  if (!btn) return;
  const idx = Number(btn.dataset.cmdDelIdx || -1);
  if (idx < 0) return;
  const cur = buildExtensionFromForm();
  cur.commands.splice(idx, 1);
  fillExtensionForm(cur);
});

downloadExcelBtn.addEventListener("click", async () => {
  try {
    await downloadExcel();
  } catch (e) {
    setStatus(`下载Excel失败: ${e.message}`);
  }
});

settingsBtn.addEventListener("click", async () => {
  try {
    await loadPrompts();
    settingsModal.classList.remove("hidden");
  } catch (e) {
    setStatus(`打开Settings失败: ${e.message}`);
  }
});
closeSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
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

refreshAdbBtn?.addEventListener("click", () => {
  fetchAdbDevices().catch((e) => setStatus(`ADB设备发现失败: ${e.message || e}`));
});

refreshSerialBtn?.addEventListener("click", () => {
  fetchSerialPorts().catch((e) => setStatus(`串口发现失败: ${e.message || e}`));
});

modeAndroidEl?.addEventListener("change", () => {
  if (modeAndroidEl.checked) fetchAdbDevices().catch(() => {});
});

modeATEl?.addEventListener("change", () => {
  if (modeATEl.checked) fetchSerialPorts().catch(() => {});
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

agenticScriptSendBtn?.addEventListener("click", () => {
  sendAgenticScriptMessage().catch((e) => setStatus(`Agentic Coding 发送失败: ${e.message || e}`));
});

agenticScriptInput?.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    agenticScriptSendBtn?.click();
  }
});

agenticScriptApplyBtn?.addEventListener("click", () => {
  if (!latestAgenticCode) {
    setStatus("未检测到可应用的代码块，请让 Agent 以 ```python ... ``` 输出代码。");
    return;
  }
  outCode.textContent = latestAgenticCode;
  setStatus("已将最新 Agentic Coding 代码应用到“脚本参考”。");
  pushAgenticScriptMessage("system", "最新代码已应用到右侧“脚本参考”。");
});

agenticScriptClearBtn?.addEventListener("click", () => {
  agenticScriptHistory = [];
  latestAgenticCode = "";
  if (agenticScriptInput) agenticScriptInput.value = "";
  renderAgenticScriptMessages();
  persistCurrentState();
  setStatus("Agentic Coding 对话已清空。");
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

// init
initTheme();
initTabs();
renderProductProfileOptions();
restoreLastResultUI(loadLastResult());
renderAgenticScriptMessages();
fetchRagDocs().catch((e) => setStatus(`加载RAG文档列表失败: ${e.message}`));
fetchAdbDevices().catch(() => {});
fetchSerialPorts().catch(() => {});

window.addEventListener("beforeunload", () => {
  closeHitlStream();
  closeStageStream();
});
