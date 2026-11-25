const runBtn = document.getElementById("runBtn");
const autoRunBtn = document.getElementById("autoRunBtn");
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
const themeToggle = document.getElementById("themeToggle");

const requirementsEl = document.getElementById("requirements");
const ragEl = document.getElementById("rag");
const testEnvironmentOptionsEl = document.getElementById("testEnvironmentOptions");
const productProfileGroupsEl = document.getElementById("productProfileGroups");
const ragFileEl = document.getElementById("ragFile");
const uploadRagBtn = document.getElementById("uploadRagBtn");
const ragDocsEl = document.getElementById("ragDocs");
const statusEl = document.getElementById("status");

const outReq = document.getElementById("outReq");
const outReview = document.getElementById("outReview");
const outDesign = document.getElementById("outDesign");
const outCases = document.getElementById("outCases");
const execCasesSummary = document.getElementById("execCasesSummary");
const execCasesTrace = document.getElementById("execCasesTrace");
const execCasesFreshnessEl = document.getElementById("execCasesFreshness");
const execCasesDiffCard = document.getElementById("execCasesDiffCard");
const execCasesDiffEl = document.getElementById("execCasesDiff");
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
const llmMaxTokensEl = document.getElementById("llmMaxTokens");
const expertReviewToggle = document.getElementById("expertReviewToggle");
const EXPERT_REVIEW_KEY = "testflow.expertReview";
if (expertReviewToggle) {
  try { expertReviewToggle.checked = localStorage.getItem(EXPERT_REVIEW_KEY) !== "0"; } catch (_) {}
  expertReviewToggle.addEventListener("change", () => {
    try { localStorage.setItem(EXPERT_REVIEW_KEY, expertReviewToggle.checked ? "1" : "0"); } catch (_) {}
  });
}
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
const designMapLink = document.getElementById("designMapLink");
const designHistoryMapLink = document.getElementById("designHistoryMapLink");
const refreshDesignHistoryBtn = document.getElementById("refreshDesignHistoryBtn");
const designHistoryList = document.getElementById("designHistoryList");
const designHistoryDetailTitle = document.getElementById("designHistoryDetailTitle");
const designHistoryMeta = document.getElementById("designHistoryMeta");
const designHistoryVisual = document.getElementById("designHistoryVisual");
const designHistoryJson = document.getElementById("designHistoryJson");
const designHistoryDocLink = document.getElementById("designHistoryDocLink");
const designHistoryLoadBtn = document.getElementById("designHistoryLoadBtn");
const designHistoryCasesBtn = document.getElementById("designHistoryCasesBtn");
const designHistoryAllProjects = document.getElementById("designHistoryAllProjects");
const ragTargetEl = document.getElementById("ragTarget");
const projectSelect = document.getElementById("projectSelect");
const currentProjectTag = document.getElementById("currentProjectTag");
const reqProjectSelect = document.getElementById("reqProjectSelect");
const reqProjectHint = document.getElementById("reqProjectHint");
const reqProjectManageBtn = document.getElementById("reqProjectManageBtn");
const projectListEl = document.getElementById("projectList");
const projectFormTitle = document.getElementById("projectFormTitle");
const projectNameEl = document.getElementById("projectName");
const projectCodeEl = document.getElementById("projectCode");
const projectDescEl = document.getElementById("projectDesc");
const projectDefaultsEl = document.getElementById("projectDefaults");
const projectCaptureDefaultsEl = document.getElementById("projectCaptureDefaults");
const newProjectBtn = document.getElementById("newProjectBtn");
const saveProjectBtn = document.getElementById("saveProjectBtn");
const useProjectBtn = document.getElementById("useProjectBtn");
const deleteProjectBtn = document.getElementById("deleteProjectBtn");
const projectDocsSection = document.getElementById("projectDocsSection");
const projectDocsHint = document.getElementById("projectDocsHint");
const projectDocFileEl = document.getElementById("projectDocFile");
const uploadProjectDocBtn = document.getElementById("uploadProjectDocBtn");
const projectDocsEl = document.getElementById("projectDocs");
const projectDesignsSection = document.getElementById("projectDesignsSection");
const projectDesignsEl = document.getElementById("projectDesigns");
const projectKbUrlEl = document.getElementById("projectKbUrl");
const projectKbTestBtn = document.getElementById("projectKbTestBtn");
const projectKbResult = document.getElementById("projectKbResult");
const kbMcpUrlEl = document.getElementById("kbMcpUrl");
const kbTimeoutEl = document.getElementById("kbTimeout");
const kbMaxQueryEl = document.getElementById("kbMaxQuery");
const kbTestQueryEl = document.getElementById("kbTestQuery");
const kbTestResult = document.getElementById("kbTestResult");
const kbSaveBtn = document.getElementById("kbSaveBtn");
const kbTestBtn = document.getElementById("kbTestBtn");

const LAST_RESULT_KEY = "pocketflow_last_result_v2";
const THEME_KEY = "pocketflow_theme";
const CURRENT_PROJECT_KEY = "testflow_current_project";
const DEFAULT_PROJECT_ID = "default";
let projects = [];
let currentProjectId = DEFAULT_PROJECT_ID;
let editingProjectId = "";
let promptCache = {};
let latestStructured = null;
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

const stageButtons = [runBtn, autoRunBtn, regenReqBtn, genDesignBtn, genCasesBtn, genExecCasesBtn, goExecCasesBtn];

function setStatus(text) {
  statusEl.textContent = text;
  if (typeof assistantOnStatus === "function") assistantOnStatus(text);
}

function setSingleButtonBusy(button, busy, pendingText) {
  if (!button) return;
  // 流程按钮忙碌 = 有生成任务在跑：同步给侧栏运行状态和助手面板
  if (stageButtons.includes(button) && typeof assistantOnTaskBusy === "function") {
    assistantOnTaskBusy((button.dataset.defaultText || button.textContent || "").trim(), !!busy);
  }
  if (!button.dataset.defaultText) button.dataset.defaultText = button.textContent || "";
  button.disabled = !!busy;
  button.textContent = busy ? (pendingText || "处理中...") : button.dataset.defaultText;
}

// 批量导入的需求清单：{ filename, requirements: [文本], meta: [{req_id, group}], groups, warnings }
let importedRequirements = null;

function parseRequirements(text) {
  if (importedRequirements?.requirements?.length) return importedRequirements.requirements.slice();
  const one = (text || "").trim();
  return one ? [one] : [];
}

// 恢复会话或载入历史记录时还原需求输入：多条需求（导入的清单）恢复成导入状态，单条放回输入框
function restoreRequirementInput(list, meta, filename) {
  const reqs = (Array.isArray(list) ? list : []).map((x) => String(x || "")).filter((x) => x.trim());
  const metaOk = Array.isArray(meta) && meta.length === reqs.length && meta.some((m) => m?.req_id);
  if (reqs.length > 1 || (reqs.length && metaOk)) {
    const m = metaOk ? meta : reqs.map(() => ({}));
    importedRequirements = { filename: filename || "", requirements: reqs, meta: m, groups: [], warnings: [] };
  } else {
    importedRequirements = null;
    if (requirementsEl) requirementsEl.value = reqs[0] || "";
  }
  renderRequirementImport();
}

function requirementMeta() {
  return importedRequirements?.requirements?.length ? importedRequirements.meta : null;
}

function renderRequirementImport() {
  const box = document.getElementById("reqImportResult");
  if (!box) return;
  const imp = importedRequirements;
  if (!imp?.requirements?.length) {
    box.innerHTML = "";
    if (requirementsEl) requirementsEl.readOnly = false;
    return;
  }
  if (requirementsEl) {
    requirementsEl.readOnly = true;
    requirementsEl.value = imp.requirements.join("\n\n");
  }
  const groups = (imp.groups || []).map((g) => `<li>${esc(g.name)}（${g.count} 条）</li>`).join("");
  const warns = (imp.warnings || []).map((w) => `<p class="feature-hint">⚠ ${esc(w)}</p>`).join("");
  box.innerHTML = `<p>已导入 <b>${imp.requirements.length}</b> 条需求（${esc(imp.filename || "")}），每行一条，用例按“一级模块 / 二级模块”分组。
    <button id="reqImportClear" class="ui-btn ui-btn-secondary" type="button">清除导入</button></p>${warns}${
    groups ? `<details class="fold"><summary>一级模块 ${imp.groups.length} 个</summary><ul>${groups}</ul></details>` : ""}`;
  document.getElementById("reqImportClear")?.addEventListener("click", () => {
    importedRequirements = null;
    if (requirementsEl) requirementsEl.value = "";
    renderRequirementImport();
    persistCurrentState();
  });
}

async function importRequirementFile(file) {
  const buf = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  const data = await postJson("/api/requirements/import", { filename: file.name, content_base64: btoa(bin) });
  importedRequirements = { filename: file.name, ...data };
  renderRequirementImport();
  persistCurrentState();
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
    test_types: getSelectedTestTypes(),
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

const TEST_TYPE_OPTIONS = [
  { id: "functional", label: "功能", description: "正常、异常、边界、定时器、冲突、移动性、互操作、能力组合。", checked: true },
  { id: "performance", label: "性能", description: "时延、成功率、吞吐、精度等指标，带样本量和统计口径。" },
  { id: "stability", label: "稳定性", description: "长时间保持、反复执行、异常后恢复（鲁棒性）。" },
];

function renderTestTypeOptions() {
  const host = document.getElementById("testTypeOptions");
  if (!host) return;
  host.innerHTML = `<div class="feature-profile-group"><div class="feature-option-grid env-grid">${TEST_TYPE_OPTIONS.map((t) =>
    `<label class="feature-option"><input type="checkbox" id="tt_${t.id}"${t.checked ? " checked" : ""} /><span><strong>${esc(t.label)}</strong><span class="feature-hint">${esc(t.description)}</span></span></label>`
  ).join("")}</div></div>`;
}

function getSelectedTestTypes() {
  const picked = TEST_TYPE_OPTIONS.filter((t) => document.getElementById(`tt_${t.id}`)?.checked).map((t) => t.id);
  return picked.length ? picked : ["functional"];
}

function setSelectedTestTypes(ids) {
  const set = new Set(Array.isArray(ids) && ids.length ? ids.map(String) : ["functional"]);
  TEST_TYPE_OPTIONS.forEach((t) => {
    const el = document.getElementById(`tt_${t.id}`);
    if (el) el.checked = set.has(t.id);
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

let hitlRequestInFlight = false;

function handleHitlStreamEvent(ev) {
  // 评审结果和待确认问题由 generateRequirementsRound 汇总成一条消息；这里只处理进度和异常，避免同一件事刷多条。
  const et = ev?.type || "";
  const payload = ev?.payload || {};
  if (et === "state") {
    if (payload.error) pushSystemBotMessage(`测试需求评审后台出错：${payload.error}`, { actionNeeded: true });
    return;
  }
  if (et === "node_running") {
    // 只在有评审请求在途时显示进度；刚连上通道时补发的旧事件不能盖掉已经出来的结果
    if (hitlRequestInFlight) setStatus(`测试需求评审执行中：${nodeLabel(payload.node, payload)}`);
    return;
  }
  if (et === "completed") {
    closeHitlStream();
    return;
  }
  if (et === "error") {
    pushSystemBotMessage(`需求评审异常：${payload.error || "未知错误"}`, { actionNeeded: true });
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
    pushSystemBotMessage("需求评审的实时进度通道中断，请稍后重试或继续操作。", { actionNeeded: true });
  };
}

function stageLabel(stage) {
  const map = { design: "测试设计", testcases: "测试用例", exec_cases: "可执行用例", auto: "一键生成", requirements: "测试需求评审" };
  return map[stage] || stage || "stage";
}

const NODE_LABELS = {
  IntakeNode: "需求录入", ReqParseNode: "需求解析", TriPersonaReviewNode: "三方评审", SynthesisNode: "综合定稿",
  TestDesignNode: "测试设计", TestDesignSupervisorNode: "设计质量门", TestCaseBatchGenNode: "编写测试用例",
  FinalizeTestCaseNode: "汇总测试用例", TestCaseSupervisorNode: "用例质量门", ExecutableCaseNode: "生成可执行用例",
};

function nodeLabel(node, payload = {}) {
  const base = payload.label || NODE_LABELS[node] || node || "处理中";
  return payload.detail ? `${base}（${payload.detail}）` : base;
}

function usageLine(result) {
  return result?.llm_usage_text ? `\n${result.llm_usage_text}` : "";
}

// ---------- 运行进度：阶段流程条 + 侧栏步骤状态 ----------
// 一键生成 / 分步生成都走这里：主区顶部显示阶段流程条，侧栏步骤打状态标记；
// 助手“运行动态”只记阶段级结果（每阶段完成一条、失败一条），不再每个节点刷一条。
const RUN_STAGE_PLANS = {
  requirements: { label: "测试需求评审", sheet: "sheet2", steps: [
    ["KnowledgeRetrieve", "检索参考资料"], ["IntakeNode", "需求录入"], ["ReqParseNode", "需求解析"],
    ["TriPersonaReviewNode", "三方评审"], ["SynthesisNode", "综合定稿"], ["KnowledgeResolve", "查证评审问题"]] },
  design: { label: "测试设计", sheet: "sheet3", steps: [
    ["KnowledgeRetrieve", "检索设计资料"], ["TestDesignNode", "设计测试点"], ["TestDesignSupervisorNode", "设计质量门"]] },
  testcases: { label: "测试用例", sheet: "sheet4", steps: [
    ["TestCaseBatchGenNode", "编写测试用例"], ["FinalizeTestCaseNode", "汇总测试用例"], ["TestCaseSupervisorNode", "用例质量门"]] },
  exec_cases: { label: "可执行用例", sheet: "sheet5", steps: [["ExecutableCaseNode", "生成可执行用例"]] },
};
const RUN_STATUS_TEXT = { pending: "等待", running: "进行中", done: "完成", failed: "失败" };

let runState = null;
let runTimer = null;
const runPanelEl = document.getElementById("runProgress");

function fmtDuration(ms) {
  const sec = Math.max(0, Math.round((ms || 0) / 1000));
  const m = Math.floor(sec / 60), s = sec % 60;
  return m ? `${m}分${String(s).padStart(2, "0")}秒` : `${s}秒`;
}

function runStart(title, stageKeys) {
  runState = {
    title, status: "running", start: Date.now(), end: 0, error: "", note: "", noteAction: false,
    stages: stageKeys.map((key) => {
      const plan = RUN_STAGE_PLANS[key] || { label: stageLabel(key), sheet: "", steps: [] };
      return { key, label: plan.label, sheet: plan.sheet, status: "pending", start: 0, end: 0, summary: "", collapsed: false,
        steps: plan.steps.map(([node, label]) => ({ node, label, status: "pending", detail: "", runs: 0 })) };
    }),
  };
  runPanelCollapsed = false;
  clearInterval(runTimer);
  runTimer = setInterval(renderRun, 1000);
  if (stageKeys.length === 1) runEnterStage(stageKeys[0]);
  renderRun();
}

function runCurrentStage() {
  if (!runState) return null;
  return runState.stages.find((s) => s.status === "running") || null;
}

function runEnterStage(key) {
  if (!runState) return;
  const now = Date.now();
  for (const st of runState.stages) {
    if (st.key === key) {
      st.status = "running"; st.start = st.start || now;
      break;
    }
    if (st.status !== "done") { runFinishSteps(st); st.status = "done"; st.end = st.end || now; }
  }
  renderRun();
}

function runFinishSteps(st) {
  st.steps.forEach((s) => { if (s.status === "running") s.status = "done"; });
}

function runNode(node, label, detail) {
  const st = runCurrentStage();
  if (!st) return;
  let idx = st.steps.findIndex((s) => s.node === node);
  if (idx < 0) {
    st.steps.push({ node, label: label || node, status: "pending", detail: "", runs: 0 });
    idx = st.steps.length - 1;
  }
  const step = st.steps[idx];
  if (step.status !== "running") step.runs += 1;
  st.steps.forEach((s, i) => {
    if (i < idx && s.status !== "done") s.status = "done";
    if (i > idx && s.status === "running") s.status = "pending";  // 质量门回流重做时，后面的步骤回到等待
  });
  step.status = "running";
  step.detail = detail || "";
  renderRun();
}

function summarizeStageResult(key, res) {
  res = res || {};
  if (key === "requirements") {
    const n = (res.requirement_spec?.final_requirements || []).length;
    const ai = (res.auto_answered_user_questions || []).length;
    return `${n} 条测试需求` + (ai ? `，${ai} 个问题采用 AI 答案` : "");
  }
  if (key === "design") return `${(res.test_design_spec?.integrated_matrix || []).length} 个测试点`;
  if (key === "testcases") return `${(res.test_case_spec?.testcases || []).length} 条用例`;
  if (key === "exec_cases") {
    const s = res.executable_cases?.summary || {};
    return `Artemis ${s.artemis || 0} · AT ${s.at_agent || 0} · Amarisoft ${s.amarisoft || 0} · 协议 ${s.protocol || 0}`;
  }
  return "";
}

function runStageDone(key, res) {
  if (!runState) return;
  const st = runState.stages.find((s) => s.key === key);
  if (!st || st.status === "done") return;
  st.steps.forEach((s) => { s.status = "done"; });
  st.status = "done";
  st.start = st.start || Date.now();
  st.end = Date.now();
  st.summary = summarizeStageResult(key, res);
  pushSystemBotMessage(`${st.label}完成：${st.summary || "已生成"}（${fmtDuration(st.end - st.start)}）`);
  renderRun();
}

function runFinish(ok, error = "", failedNode = "") {
  if (!runState || runState.status !== "running") return;
  runState.end = Date.now();
  runState.status = ok ? "done" : "failed";
  if (ok) {
    runState.stages.forEach((st) => { if (st.status !== "done") { st.steps.forEach((s) => { s.status = "done"; }); st.status = "done"; st.end = st.end || runState.end; } });
  } else {
    runState.error = error || "未知错误";
    const st = runCurrentStage() || runState.stages.find((s) => s.status === "pending");
    if (st) {
      st.status = "failed"; st.end = runState.end; st.start = st.start || runState.end;
      const step = st.steps.find((s) => s.status === "running") || st.steps.find((s) => s.node === failedNode);
      if (step) step.status = "failed";
    }
  }
  clearInterval(runTimer);
  runTimer = null;
  // 运行动态只记阶段级的结果：一次一键生成最多 4 条阶段完成 + 1 条收尾，不再逐节点刷
  if (ok) {
    if (runState.stages.length > 1) pushSystemBotMessage(`${runState.title}完成，用时 ${fmtDuration(runState.end - runState.start)}。`);
  } else {
    const st = runState.stages.find((s) => s.status === "failed");
    pushSystemBotMessage(`${st ? st.label : runState.title}失败：${runState.error}`, { actionNeeded: true });
  }
  renderRun();
}

// 阶段跑完后由调用方补一句结果说明（显示在流程条底部；需要处理时也记进运行动态）
function runNote(text, options = {}) {
  if (!runState) return;
  runState.note = text || "";
  runState.noteAction = !!options.actionNeeded;
  if (runState.noteAction) pushSystemBotMessage(runState.note, { actionNeeded: true });
  renderRun();
}

function runFailedAlready() {
  return !!runState && runState.status === "failed";
}

let runPanelCollapsed = false;

function runStepIcon(status, n) {
  if (status === "done") return "✓";
  if (status === "failed") return "✕";
  if (status === "running") return '<span class="run-spin"></span>';
  return n == null ? "" : String(n);
}

function runStepsHtml(steps, compact = false) {
  return steps.map((s) => {
    const retry = s.runs > 1 ? `<span class="run-retry">第 ${s.runs} 次</span>` : "";
    const detail = s.status === "running" && s.detail ? `<span class="run-substep-detail">${esc(s.detail)}</span>` : "";
    return `<li class="run-substep is-${s.status}"><span class="run-substep-dot">${s.status === "done" ? "✓" : s.status === "failed" ? "✕" : ""}</span>` +
      `<span class="run-substep-label">${esc(s.label)}${compact ? "" : retry}</span>${detail}</li>`;
  }).join("");
}

function runHeaderHtml(withActions) {
  const r = runState;
  const elapsed = fmtDuration((r.end || Date.now()) - r.start);
  const doneN = r.stages.filter((s) => s.status === "done").length;
  const chip = r.status === "running" ? `进行中 · ${doneN}/${r.stages.length}` : r.status === "done" ? "已完成" : "失败";
  const actions = withActions
    ? `<div class="run-actions"><button class="run-icon-btn" data-run-act="toggle" title="${runPanelCollapsed ? "展开" : "收起"}">${runPanelCollapsed ? "▾" : "▴"}</button>` +
      (r.status !== "running" ? `<button class="run-icon-btn" data-run-act="close" title="关闭">×</button>` : "") + "</div>"
    : "";
  return `<div class="run-head"><div class="run-title">${esc(r.title)}</div>` +
    `<span class="run-chip is-${r.status}">${chip}</span><span class="run-elapsed">${r.status === "running" ? "已用时" : "用时"} ${elapsed}</span>${actions}</div>`;
}

function runStageSub(st) {
  if (st.status === "done") return `${st.summary ? esc(st.summary) + " · " : ""}${fmtDuration(st.end - st.start)}`;
  if (st.status === "running") {
    const cur = st.steps.find((s) => s.status === "running");
    return cur ? esc(cur.label + (cur.detail ? `（${cur.detail}）` : "")) : "准备中…";
  }
  if (st.status === "failed") return "出错，见下方说明";
  return "等待";
}

function renderRunPanel() {
  if (!runPanelEl) return;
  if (!runState) { runPanelEl.classList.add("hidden"); runPanelEl.innerHTML = ""; return; }
  const r = runState;
  const multi = r.stages.length > 1;
  let body = "";
  if (!runPanelCollapsed) {
    // 多阶段（一键生成）：上面是阶段流程条，下面是当前阶段的细分步骤；单阶段：流程条直接画细分步骤
    const items = multi
      ? r.stages.map((st, i) => ({ status: st.status, n: i + 1, label: st.label, sub: runStageSub(st), sheet: st.sheet }))
      : r.stages[0].steps.map((s, i) => ({ status: s.status, n: i + 1, label: s.label,
          sub: s.status === "running" ? esc(s.detail || "进行中…") + (s.runs > 1 ? ` · 第 ${s.runs} 次` : "") : RUN_STATUS_TEXT[s.status], sheet: "" }));
    body += `<ol class="run-stepper">${items.map((it) => `
      <li class="run-step is-${it.status}${it.sheet && it.status === "done" ? " is-link" : ""}"${it.sheet ? ` data-run-sheet="${it.sheet}"` : ""}>
        <span class="run-step-icon">${runStepIcon(it.status, it.n)}</span>
        <span class="run-step-text"><span class="run-step-label">${esc(it.label)}</span><span class="run-step-sub">${it.sub}</span></span>
      </li>`).join("")}</ol>`;
    if (multi) {
      const focus = r.stages.find((s) => s.status === "running" || s.status === "failed");
      if (focus) body += `<div class="run-detail"><span class="run-detail-label">${esc(focus.label)}</span><ol class="run-substeps">${runStepsHtml(focus.steps)}</ol></div>`;
    }
  }
  if (r.status === "failed") {
    body += `<div class="run-error"><b>失败原因：</b>${esc(r.error)}<div class="run-error-hint">已完成阶段的结果已保留，可到对应页面检查输入后分步重跑。</div></div>`;
  }
  if (r.note) body += `<div class="run-note${r.noteAction ? " is-action" : ""}">${esc(r.note)}</div>`;
  runPanelEl.className = `run-progress is-${r.status}${runPanelCollapsed ? " is-collapsed" : ""}`;
  runPanelEl.innerHTML = runHeaderHtml(true) + body;
}

function renderRunNav() {
  const stages = runState ? runState.stages : [];
  document.querySelectorAll("#sheetTabs .sheet-tab").forEach((btn) => {
    btn.classList.remove("run-running", "run-done", "run-failed");
    const st = stages.find((s) => s.sheet === btn.dataset.sheet);
    if (st && st.status !== "pending") btn.classList.add(`run-${st.status}`);
  });
}

function renderRun() {
  renderRunPanel();
  renderRunNav();
}

runPanelEl?.addEventListener("click", (e) => {
  const act = e.target.closest("[data-run-act]")?.dataset.runAct;
  if (act === "toggle") { runPanelCollapsed = !runPanelCollapsed; renderRunPanel(); return; }
  if (act === "close") { runState = null; renderRunPanel(); renderRunNav(); return; }
  const step = e.target.closest(".run-step.is-link");
  if (step?.dataset.runSheet) switchSheetById(step.dataset.runSheet);
});

async function startStageJobAndWait(stage, payload, handlers = {}) {
  const startResp = await postJson(`/api/stage/${stage}/start`, { ...payload, requirement_meta: requirementMeta(), expert_review: expertReviewToggle ? expertReviewToggle.checked : true });
  const jobId = startResp.job_id;
  if (!jobId) throw new Error("stage job_id为空");

  closeStageStream();
  activeStageJobId = jobId;
  if (stage === "auto") runStart(handlers.title || "一键生成", ["requirements", "design", "testcases", "exec_cases"]);
  else runStart(handlers.title || stageLabel(stage), [stage]);

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
      if (et === "state") return;
      streamErrors = 0;
      if (et === "job_started") return;
      if (et === "node_running") {
        const n = nodeLabel(p.node, p);
        const prefix = handlers.currentStage ? `${stageLabel(stage)} ${handlers.stageIndex}/${handlers.stageTotal} · ${stageLabel(handlers.currentStage)}` : stageLabel(stage);
        setStatus(`${prefix}执行中：${n}`);
        runNode(p.node, p.label || NODE_LABELS[p.node], p.detail);
        return;
      }
      if (et === "stage_progress") {
        handlers.currentStage = p.stage;
        handlers.stageIndex = p.index;
        handlers.stageTotal = p.total;
        runEnterStage(p.stage);
        return;
      }
      if (et === "stage_result") {
        runStageDone(p.stage, p.result || {});
        try { handlers.onStageResult?.(p.stage, p.result || {}); } catch (e) { console.error(e); }
        return;
      }
      if (et === "module_result") {
        return;
      }
      if (et === "completed") {
        if (stage !== "auto") runStageDone(stage, p.result || {});
        runFinish(true);
        closeStageStream();
        resolve(p.result || {});
        return;
      }
      if (et === "error") {
        const msgText = p.error || "unknown error";
        runFinish(false, msgText, p.failed_node);
        closeStageStream();
        reject(new Error(msgText));
      }
    };

    // 连接中断时先问任务状态：还在跑就让 EventSource 自动重连（服务端按 Last-Event-ID 续发，不丢不重），
    // 只有任务已经结束或服务端找不到任务时才收尾。
    let streamErrors = 0;
    es.onerror = async () => {
      if (activeStageStream !== es) return;
      streamErrors += 1;
      try {
        const s = await fetch(`/api/stage/${encodeURIComponent(jobId)}/state`);
        if (activeStageStream !== es) return;
        if (s.ok) {
          const st = await s.json();
          if (st.status === "completed") {
            if (stage !== "auto") runStageDone(stage, st.result || {});
            runFinish(true);
            closeStageStream();
            resolve(st.result || {});
            return;
          }
          if (st.status === "running" && es.readyState !== EventSource.CLOSED && streamErrors <= 20) return;
          closeStageStream();
          const errText = String(st?.error?.error || (st.status === "running" ? "与服务端的进度通道中断，任务仍在后台运行，请稍后在历史记录中查看" : "任务失败"));
          runFinish(false, errText, st?.error?.failed_node);
          reject(new Error(errText));
          return;
        }
        if (s.status !== 404 && es.readyState !== EventSource.CLOSED && streamErrors <= 20) return;
      } catch (_) {
        if (es.readyState !== EventSource.CLOSED && streamErrors <= 20) return;  // 服务暂时连不上，继续等重连
      }
      closeStageStream();
      runFinish(false, "与服务端的连接中断");
      reject(new Error("与服务端的连接中断"));
    };
  });
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
    const kbTag = q.kb_status === "resolved" ? "知识库已确认" : q.kb_status === "conflict" ? "资料冲突，需确认" : "";
    const meta = [q.req_id, (q.personas || []).join("/") ? `${(q.personas || []).join("/")}评审` : "", kbTag].filter(Boolean).join(" · ");
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
    ? `<details class="fold"><summary>AI 已自行确认 ${autoConfirmed.length} 个问题（${autoConfirmed.filter((q) => q.kb_status === "resolved").length} 个有知识库依据，其余按 3GPP 默认值 / 行业惯例，可修改）</summary>${autoConfirmed
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


// 还没归档时的预览：交给后端用归档文档同一个模板生成，页面样式和测试架构图保持一致
let designDocPreviewSeq = 0;
async function buildDesignDocumentPreview() {
  const res = await fetch("/api/export/design-document.html", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requirement_input: parseRequirements(requirementsEl?.value || ""),
      requirement_spec: stageState.requirement_spec || {},
      persona_reviews: stageState.persona_reviews || {},
      requirement_review_history: stageState.requirement_review_history || {},
      test_design_spec: stageState.test_design_spec || {},
      test_case_spec: stageState.test_case_spec || {},
      product_profile: getSelectedProductProfile(),
      test_environments: getSelectedTestEnvironments(),
      project_id: currentProjectId,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

function refreshDesignDocumentLink() {
  revokeDesignDocUrl();
  // 测试架构图按归档记录现算：有归档（测试设计完成后自动归档）才显示入口
  const mapUrl = stageState.test_design_spec && stageState.design_history_doc_url
    ? stageState.design_history_doc_url.replace(/\/document$/, "/map") : "";
  if (designMapLink) {
    designMapLink.classList.toggle("hidden", !mapUrl);
    if (mapUrl) designMapLink.href = mapUrl; else designMapLink.removeAttribute("href");
  }
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
  const seq = ++designDocPreviewSeq;
  buildDesignDocumentPreview()
    .then((html) => {
      if (seq !== designDocPreviewSeq) return;
      revokeDesignDocUrl();
      latestDesignDocUrl = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
      if (designDocLink) {
        designDocLink.href = latestDesignDocUrl;
        designDocLink.title = `${title} - 测试设计文档`;
      }
      designDocActions?.classList.remove("hidden");
    })
    .catch((err) => console.warn("测试设计文档预览生成失败", err));
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
        const tp = purposeHtml(r.test_purpose);
        const refs = (r.references || []).length ? `<br/><span class="feature-hint">${esc(r.references.join("；"))}</span>` : "";
        return `<tr><td>${esc(r.row_id || `ROW-${idx + 1}`)}</td><td>${esc(r.req_id || "")}</td><td>${esc(r.objective_id || "")}</td><td>${techniqueTag(r.technique)}</td><td>${esc(r.scenario || "")}${tp}${refs}</td><td>${esc(cfgStr)}</td><td>${esc(pass)}</td><td>${esc(envText)}</td><td>${esc(riskText)}</td></tr>`;
      })
      .join("");
    const techCount = {};
    integrated.forEach((r) => { const t = r.technique || "normal"; techCount[t] = (techCount[t] || 0) + 1; });
    const techSummary = Object.keys(techCount).map((t) => `${TECHNIQUE_LABELS[t] || t} ${techCount[t]}`).join(" · ");
    html += `<h4>整合覆盖矩阵（测试点）</h4><p class="feature-hint">共 ${integrated.length} 个测试点：${esc(techSummary)}</p><table><thead><tr><th>行ID</th><th>需求ID</th><th>关联目标</th><th>测试技术</th><th>测试场景 / 测试目的</th><th>关键配置</th><th>通过标准</th><th>推荐测试环境</th><th>资源风险</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  if ((design?.design_advice || []).length) {
    html += `<h4>设计提示</h4><div class="banner">${design.design_advice.map((x) => `• ${esc(x)}`).join("<br/>")}</div>`;
  }

  if ((design?.design_notes || []).length) {
    html += `<h4>设计说明</h4><div>${design.design_notes.map((x) => `- ${esc(x)}`).join("<br/>")}</div>`;
  }

  if (design?.generation_meta) {
    const m = design.generation_meta;
    html += `<details class="fold"><summary>生成信息</summary><div class="feature-hint">补漏生成的测试点：${esc(m.gap_filled_rows ?? 0)}；按需求原值补入的配置：${esc(
      m.patched_configs ?? 0)}；补入的数值门限：${esc(m.patched_metrics ?? 0)}；提示词：${esc(m.design_prompt || "")}、${esc(m.integrated_prompt || "")}</div></details>`;
  }

  viewDesign.innerHTML = html || "<em>暂无结构化设计</em>";
}

const TECHNIQUE_LABELS = {
  normal: "正常流程", abnormal: "异常/拒绝", boundary: "边界值", timer: "定时器", collision: "流程冲突",
  mobility: "移动性", interworking: "互操作", capability: "能力组合", performance: "性能/KPI", stability: "长稳/恢复",
};

function techniqueTag(t) {
  if (!t) return "";
  return `<span class="tag tech-${esc(t)}">${esc(TECHNIQUE_LABELS[t] || t)}</span>`;
}

function purposeHtml(tp) {
  if (!tp || !(tp.when || tp.then)) return "";
  const part = (k, v) => (v ? `<div><b>${k}</b> ${esc(v)}</div>` : "");
  return `<div class="tp-box">${part("with", tp.with)}${part("when", tp.when)}${part("then", tp.then)}</div>`;
}

function fmtVal(v) {
  return typeof v === "object" && v !== null ? JSON.stringify(v) : `${v ?? ""}`;
}

function kvInline(obj) {
  return Object.entries(obj || {}).map(([k, v]) => `<code>${esc(k)}=${esc(fmtVal(v))}</code>`).join(" ");
}

function renderTcdDetail(tc) {
  const ic = tc.initial_conditions || {};
  const cfg = tc.configuration || {};
  const icRows = [["网络侧", ic.system_simulator], ["UE", ic.ue], ["Preamble", ic.preamble]]
    .filter(([, v]) => (v || []).length)
    .map(([k, v]) => `<tr><th>${k}</th><td>${(v || []).map(esc).join("<br/>")}</td></tr>`).join("");
  const cfgRows = [
    ...(cfg.cells || []).map((c, i) => [`小区 ${esc(c.cell_id || `Cell${i + 1}`)}`, kvInline(Object.fromEntries(Object.entries(c).filter(([k]) => k !== "cell_id")))]),
    ...(Object.keys(cfg.core || {}).length ? [["核心网/NAS", kvInline(cfg.core)]] : []),
    ...(Object.keys(cfg.ue || {}).length ? [["UE", kvInline(cfg.ue)]] : []),
    ...(Object.keys(cfg.other || {}).length ? [["其他", kvInline(cfg.other)]] : []),
  ].map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("");
  const steps = (tc.procedure || []).map((p) => `<tr class="${p.verdict ? "verdict-row" : ""}"><td>${esc(p.step)}</td><td>${esc(p.actor || "")}</td><td>${
    p.direction ? `<span class="dir dir-${esc(p.direction.toLowerCase())}">${esc(p.direction)}</span>` : ""}</td><td>${esc(p.layer || "")}</td><td><strong>${esc(p.message || p.action || "")}</strong>${
    p.msg_ref ? ` <span class="tag">${esc(p.msg_ref)}</span>` : ""}${Object.keys(p.params || {}).length ? `<br/>${kvInline(p.params)}` : ""}</td><td>${esc(p.expected || "")}${
    p.timing ? `<br/><span class="feature-hint">${esc(p.timing)}</span>` : ""}</td><td>${p.verdict ? "✔" : ""}</td></tr>`).join("");
  const msgs = (tc.message_contents || []).map((m) => `<div class="msg-config"><div class="msg-config-head"><span class="tag">${esc(m.msg_id || "")}</span><strong>${esc(m.message || "")}</strong>
      <span class="dir dir-${esc((m.direction || "").toLowerCase())}">${esc(m.direction || "")}</span><span class="feature-hint">${esc(m.purpose || m.based_on || "")}</span></div>
      <table class="ui-table"><thead><tr><th>IE 路径</th><th>取值</th><th>扫描</th><th>说明</th></tr></thead><tbody>${
        (m.ies || []).map((ie) => `<tr><td><code>${esc(ie.path || "")}</code></td><td><code>${esc(fmtVal(ie.value))}</code></td><td>${esc(ie.vary || "")}</td><td>${esc(ie.note || "")}</td></tr>`).join("")
      }</tbody></table></div>`).join("");
  const rcAll = tc.requirement_configs || [];
  const rc = rcAll.filter((c) => c.status === "patched");
  const rcConflict = rcAll.filter((c) => c.status === "conflict");
  const notes = tc.review_notes || [];
  return `<div class="tcd-detail">
    ${purposeHtml(tc.test_purpose)}
    ${(tc.references || []).length ? `<p class="feature-hint">参考条款：${esc(tc.references.join("；"))}${tc.applicability ? `　适用性：${esc(tc.applicability)}` : ""}</p>` : ""}
    ${icRows ? `<h5>初始条件</h5><table class="ui-table kv-table">${icRows}</table>` : ""}
    ${cfgRows ? `<h5>关键配置</h5><table class="ui-table kv-table">${cfgRows}</table>` : ""}
    ${steps ? `<h5>测试步骤</h5><table class="ui-table"><thead><tr><th>St</th><th>发起方</th><th>方向</th><th>层</th><th>消息 / 动作</th><th>期望</th><th>判定</th></tr></thead><tbody>${steps}</tbody></table>` : ""}
    ${msgs ? `<h5>特定消息内容</h5>${msgs}` : ""}
    ${(tc.parameter_variations || []).length ? `<h5>参数扫描</h5><ul>${tc.parameter_variations.map((v) => `<li><code>${esc(v.name || "")}</code>：${esc(fmtVal(v.values))} ${esc(v.purpose || "")}</li>`).join("")}</ul>` : ""}
    ${rc.length ? `<p class="feature-hint">以下需求配置由质量门按需求原值补入：${rc.map((c) => `${esc(c.name)}=${esc(fmtVal(c.value))}`).join("，")}</p>` : ""}
    ${rcConflict.length ? `<p class="feature-hint warn-text">需求配置与用例取值不一致（需求值已另存，请确认）：${rcConflict.map((c) => esc(c.note || `${c.name}=${fmtVal(c.value)}`)).join("；")}</p>` : ""}
    ${notes.length ? `<h5>专家评审意见</h5><ul class="review-notes">${notes.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    ${(tc.open_points || []).length ? `<h5>待确认</h5><ul>${tc.open_points.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
  </div>`;
}

function renderCases(spec) {
  const tcs = spec?.testcases || [];
  if (!tcs.length) {
    viewCases.innerHTML = "<em>暂无结构化用例</em>";
    return;
  }
  const caseHtml = (tc) => {
      const passFail = Array.isArray(tc.pass_fail) ? tc.pass_fail : [String(tc.pass_fail || "")];
      const envText = formatTestEnvironmentSummary(tc.test_environment);
      const riskText = formatTestEnvironmentRisk(tc.test_environment);
      const nSteps = (tc.procedure || tc.steps || []).length;
      const nMsg = (tc.procedure || []).filter((p) => p.message).length;
      return `<details class="tc-item"><summary><span class="tc-id">${esc(tc.tc_id)}</span>${techniqueTag(tc.technique)}<span class="tc-title">${esc(tc.title)}</span>
        <span class="feature-hint">${esc(envText)} · ${nSteps} 步${nMsg ? ` / ${nMsg} 条信令` : ""} · ${esc((tc.trace?.req_ids || []).join(","))}${
          (tc.review_notes || []).length ? ` · 评审意见 ${tc.review_notes.length}` : ""}</span></summary>
        <div class="tc-body"><p><b>通过标准：</b>${esc(passFail.join(" / "))}</p>${riskText ? `<p class="feature-hint">${esc(riskText)}</p>` : ""}${
          tc.procedure ? renderTcdDetail(tc) : `<p class="feature-hint">旧格式用例：${esc((tc.steps || []).map((s) => s.action).join(" → "))}</p>`}</div></details>`;
  };
  // 按“一级模块 / 二级模块”分组展示；只有一个分组时不套层级，保持原来的平铺列表
  const tree = new Map();
  tcs.forEach((tc) => {
    const l1 = tc.suite?.level1 || "未分组";
    const l2 = tc.suite?.level2 || "未分组";
    if (!tree.has(l1)) tree.set(l1, new Map());
    if (!tree.get(l1).has(l2)) tree.get(l1).set(l2, []);
    tree.get(l1).get(l2).push(tc);
  });
  const nLevel2 = [...tree.values()].reduce((n, m) => n + m.size, 0);
  let rows = "";
  if (nLevel2 <= 1) {
    rows = tcs.map(caseHtml).join("");
  } else {
    rows = [...tree.entries()].map(([l1, subs]) => {
      const total = [...subs.values()].reduce((n, list) => n + list.length, 0);
      const inner = [...subs.entries()].map(([l2, list]) =>
        `<details class="tc-suite tc-suite-l2"><summary><span class="tc-title">${esc(l2)}</span><span class="feature-hint">${list.length} 条</span></summary>${list.map(caseHtml).join("")}</details>`).join("");
      return `<details class="tc-suite tc-suite-l1"${tree.size === 1 ? " open" : ""}><summary><b>${esc(l1)}</b><span class="feature-hint">${subs.size} 个二级模块 · ${total} 条用例</span></summary>${inner}</details>`;
    }).join("");
  }
  viewCases.innerHTML = `<p class="feature-hint">共 ${tcs.length} 条用例${nLevel2 > 1 ? `，分为 ${tree.size} 个一级模块、${nLevel2} 个二级模块` : ""}，点击展开测试目的、初始条件、配置、步骤和消息内容。</p>${rows}`;
}

function renderDesignHistoryList() {
  if (!designHistoryList) return;
  if (!designHistoryItems.length) {
    designHistoryList.innerHTML = designHistoryAllProjects?.checked
      ? "<em>暂无历史测试设计记录。</em>"
      : `<em>项目“${esc(currentProject()?.name || "")}”下暂无测试设计记录。勾选右上角“显示全部项目”可查看其他项目。</em>`;
    return;
  }
  designHistoryList.innerHTML = `<div class="design-history-list">${designHistoryItems
    .map((item) => {
      const active = item.record_id === selectedDesignHistoryId ? "active" : "";
      const status = item.has_testcases ? "已生成测试用例" : "仅完成测试设计";
      const projectLine = designHistoryAllProjects?.checked ? `项目：${esc(item.project_name || "")} · ` : "";
      return `<button class="design-history-item ${active}" data-record-id="${esc(item.record_id)}" type="button">
        <h4>${esc(item.title || item.record_id)}</h4>
        <p>${projectLine}更新时间：${esc(item.updated_at || "")}</p>
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
      designHistoryMapLink?.classList.add("hidden");
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
  if (designHistoryMapLink) {
    designHistoryMapLink.href = record.map_url || summary.map_url || "#";
    designHistoryMapLink.classList.remove("hidden");
  }
  if (designHistoryLoadBtn) designHistoryLoadBtn.disabled = false;
  if (designHistoryCasesBtn) {
    designHistoryCasesBtn.disabled = !record.test_design_spec;
    designHistoryCasesBtn.textContent = summary.has_testcases ? "重新生成测试用例" : "继续生成测试用例";
  }
  if (designHistoryMeta) {
    designHistoryMeta.innerHTML = `
      <div class="design-history-meta-grid">
        <div class="design-history-meta-card"><strong>所属项目</strong>
          <select class="ui-input" id="designHistoryProjectSelect" data-record-id="${esc(record.record_id || "")}">${projects
            .map((p) => `<option value="${esc(p.project_id)}" ${p.project_id === (summary.project_id || DEFAULT_PROJECT_ID) ? "selected" : ""}>${esc(projectLabel(p))}</option>`)
            .join("")}</select></div>
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
  const query = designHistoryAllProjects?.checked ? "" : `?project_id=${encodeURIComponent(currentProjectId)}`;
  const resp = await fetch(`/api/design-history${query}`);
  if (!resp.ok) throw new Error(await resp.text() || "加载历史目录失败");
  const data = await resp.json();
  designHistoryItems = Array.isArray(data.items) ? data.items : [];
  const inList = (id) => id && designHistoryItems.some((x) => x.record_id === id);
  renderDesignHistoryList();
  const targetId =
    [preferredId, selectedDesignHistoryId, stageState.design_history_record_id].find(inList) ||
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
  const recordProjectId = record.summary?.project_id || record.project_id || DEFAULT_PROJECT_ID;
  setCurrentProject(recordProjectId, { applyDefaults: false, askReset: false });
  restoreRequirementInput(record.requirement_input, record.requirement_meta, "历史记录");
  setSelectedTestEnvironments(record.test_environments?.selected_ids || record.test_environments?.selected || []);
  setSelectedProductProfile(record.product_profile?.selected || {});
  setSelectedTestTypes(record.product_profile?.test_types || record.test_design_spec?.test_types);
  stageState.requirement_spec = record.requirement_spec || null;
  stageState.persona_reviews = record.persona_reviews || null;
  if (typeof clarifyOnSpecChanged === "function") clarifyOnSpecChanged();
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
  const imp = snapshot.form?.imported_requirements;
  if (imp?.requirements?.length) {
    importedRequirements = imp;
    renderRequirementImport();
  } else {
    restoreRequirementInput([snapshot.form?.requirements || ""]);
  }
  ragEl.value = snapshot.form?.rag || "";
  if (bzIdsEl) bzIdsEl.value = snapshot.form?.bz_ids || "";
  if (bzExcludedEl) bzExcludedEl.value = snapshot.form?.bz_excluded || "";
  setSelectedTestEnvironments(snapshot.form?.test_environment_selected || []);
  setSelectedProductProfile(snapshot.form?.product_profile_selected || {});
  setSelectedTestTypes(snapshot.form?.test_types);
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
  if (typeof assistantOnSessionChanged === "function") assistantOnSessionChanged();
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
      imported_requirements: importedRequirements,
      rag: ragEl.value,
      bz_ids: bzIdsEl?.value || "",
      bz_excluded: bzExcludedEl?.value || "",
      test_environment_selected: getSelectedTestEnvironments().selected_ids,
      product_profile_selected: getSelectedProductProfile().selected,
      test_types: getSelectedTestTypes(),
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

function readFileBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const raw = String(reader.result || "");
      const idx = raw.indexOf("base64,");
      resolve(idx >= 0 ? raw.slice(idx + 7) : "");
    };
    reader.onerror = () => reject(reader.error || new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function uploadDocsTo(url, files) {
  let ok = 0;
  const errors = [];
  for (const f of files) {
    try {
      const b64 = await readFileBase64(f);
      const resp = await fetch(url, {
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
  return { ok, errors };
}

function projectDocsUrl(projectId) {
  return `/api/projects/${encodeURIComponent(projectId)}/docs`;
}

function renderDocRows(docs, scope, projectId = "") {
  if (!docs.length) return "<em>暂无文档</em>";
  return docs
    .map((d) => `<div class="doc-row"><span>${esc(d.filename)}<span class="feature-hint">${esc(String(d.chunk_count || 0))} 段 · ${esc(d.created_at || "")}</span></span>
      <button class="ui-btn ui-btn-ghost ui-btn-sm danger-text" type="button" data-doc-delete="${esc(d.doc_id)}" data-doc-scope="${scope}" data-project-id="${esc(projectId)}">删除</button></div>`)
    .join("");
}

async function fetchJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(await resp.text());
  return await resp.json();
}

async function fetchRagDocs() {
  const [projectData, publicData] = await Promise.all([
    fetchJson(projectDocsUrl(currentProjectId)).catch(() => ({ docs: [] })),
    fetchJson("/api/rag/docs"),
  ]);
  const noProject = currentProjectId === DEFAULT_PROJECT_ID;
  const projectName = noProject ? "未选择项目，归入默认项目" : projectLabel(currentProject());
  const targetOpt = document.getElementById("ragTargetProject");
  if (targetOpt) targetOpt.textContent = noProject ? "存入默认项目资料（未选择项目）" : `存入项目资料（${projectLabel(currentProject())}）`;
  ragDocsEl.innerHTML = `
    <div class="rag-scope-title">项目资料（${esc(projectName)}）</div>
    ${renderDocRows(projectData.docs || [], "project", currentProjectId)}
    <div class="rag-scope-title">公共资料</div>
    ${renderDocRows(publicData.docs || [], "public")}`;
}

async function deleteDoc(scope, docId, projectId) {
  if (!confirm("确定删除这份资料？删除后不再参与检索。")) return;
  const url = scope === "public"
    ? `/api/rag/docs/${encodeURIComponent(docId)}`
    : `${projectDocsUrl(projectId)}/${encodeURIComponent(docId)}`;
  const resp = await fetch(url, { method: "DELETE" });
  if (!resp.ok) throw new Error(await resp.text());
  await fetchRagDocs().catch(() => {});
  if (scope === "project") await loadProjects().catch(() => {});
}

async function uploadRagDocs() {
  const files = Array.from(ragFileEl.files || []);
  if (!files.length) throw new Error("请先选择至少一个文件");
  const toPublic = ragTargetEl?.value === "public";
  const { ok, errors } = await uploadDocsTo(toPublic ? "/api/rag/upload" : projectDocsUrl(currentProjectId), files);
  ragFileEl.value = "";
  await fetchRagDocs();
  if (!toPublic) await loadProjects().catch(() => {});
  const where = toPublic ? "公共资料" : `项目资料（${currentProject()?.name || ""}）`;
  if (errors.length) {
    setStatus(`${where}上传完成：成功 ${ok}，失败 ${errors.length}\n- ${errors.join("\n- ")}`);
  } else {
    setStatus(`${where}上传完成：成功 ${ok}`);
  }
}

// ---------- 项目 / Product ----------

function currentProject() {
  return projects.find((p) => p.project_id === currentProjectId) || null;
}

function projectLabel(p) {
  if (!p) return "";
  return p.code ? `${p.name}（${p.code}）` : p.name;
}

function renderProjectSelect() {
  if (projectSelect) {
    projectSelect.innerHTML = projects
      .map((p) => `<option value="${esc(p.project_id)}" ${p.project_id === currentProjectId ? "selected" : ""}>${esc(projectLabel(p))}</option>`)
      .join("");
  }
  if (currentProjectTag) currentProjectTag.textContent = projectLabel(currentProject());
  renderReqProjectSelect();
  if (typeof assistantOnProjectChanged === "function") assistantOnProjectChanged();
}

// 需求准备页的项目选择：“不选择项目”即默认项目，保持原来的行为；选了项目后各阶段和问答助手都查该项目的知识库。
function renderReqProjectSelect() {
  if (!reqProjectSelect) return;
  const others = projects.filter((p) => p.project_id !== DEFAULT_PROJECT_ID);
  reqProjectSelect.innerHTML = [
    `<option value="${esc(DEFAULT_PROJECT_ID)}" ${currentProjectId === DEFAULT_PROJECT_ID ? "selected" : ""}>不选择项目</option>`,
    ...others.map((p) => `<option value="${esc(p.project_id)}" ${p.project_id === currentProjectId ? "selected" : ""}>${esc(projectLabel(p))}</option>`),
  ].join("");
  if (!reqProjectHint) return;
  const p = currentProject();
  if (!p || currentProjectId === DEFAULT_PROJECT_ID) {
    reqProjectHint.textContent = others.length
      ? "未选择项目：只检索公共知识库和公共资料，测试设计归入“默认项目”。"
      : "还没有项目。可以在“项目管理”里新建项目并配置它的知识库（MCP 地址）和资料。";
    return;
  }
  const parts = [];
  parts.push(p.kb_mcp_url ? "已配置项目知识库" : "未配置项目知识库（可在“项目管理”里填写 MCP 地址）");
  parts.push(`项目资料 ${p.doc_count || 0} 份`);
  reqProjectHint.textContent = `需求评审、测试设计、评审问题查证和问答助手会检索“${projectLabel(p)}”的资料 + 公共资料。${parts.join("，")}。`;
}

async function loadProjects() {
  const data = await fetchJson("/api/projects");
  projects = Array.isArray(data.items) ? data.items : [];
  if (!projects.some((p) => p.project_id === currentProjectId)) {
    currentProjectId = projects.some((p) => p.project_id === DEFAULT_PROJECT_ID) ? DEFAULT_PROJECT_ID : projects[0]?.project_id || DEFAULT_PROJECT_ID;
  }
  renderProjectSelect();
  renderProjectList();
  if (editingProjectId && !projects.some((p) => p.project_id === editingProjectId)) editingProjectId = "";
}

function hasSessionWork() {
  return Boolean(stageState.requirement_spec || stageState.test_design_spec || stageState.test_case_spec || stageState.hitl_job_id);
}

function resetSession() {
  closeHitlStream();
  closeStageStream();
  stageState = {
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
  latestStructured = null;
  [outReq, outReview, outDesign, outCases].forEach((el) => el && (el.textContent = ""));
  [viewReq, viewReview, viewDesign, viewCases, openQuestionsPanel].forEach((el) => el && (el.innerHTML = ""));
  if (typeof clarifyOnSpecChanged === "function") clarifyOnSpecChanged();
  if (requirementsEl) requirementsEl.value = "";
  if (bzIdsEl) bzIdsEl.value = "";
  renderExecutableCases(null);
  refreshDesignDocumentLink();
}

function applyProjectDefaults(project) {
  if (!project) return;
  const hasProfile = project.product_profile_selected && Object.keys(project.product_profile_selected).length;
  const hasEnvs = Array.isArray(project.test_environment_ids) && project.test_environment_ids.length;
  if (hasProfile) setSelectedProductProfile(project.product_profile_selected);
  if (hasEnvs) setSelectedTestEnvironments(project.test_environment_ids);
}

// 切换项目：当前会话属于旧项目，切换后开始新会话（已完成的设计已归档在历史里）。
function setCurrentProject(projectId, { applyDefaults = true, askReset = true } = {}) {
  if (!projects.some((p) => p.project_id === projectId)) return false;
  if (projectId === currentProjectId) return true;
  if (askReset && hasSessionWork()) {
    const ok = confirm("切换项目会开始新的测试设计会话（已完成的测试设计已归档在原项目的历史里）。继续？");
    if (!ok) {
      renderProjectSelect();
      return false;
    }
    resetSession();
  }
  currentProjectId = projectId;
  try { localStorage.setItem(CURRENT_PROJECT_KEY, projectId); } catch (_) {}
  if (applyDefaults) applyProjectDefaults(currentProject());
  renderProjectSelect();
  renderProjectList();
  fetchRagDocs().catch(() => {});
  if (designHistoryLoaded) loadDesignHistory().catch(() => {});
  persistCurrentState(`当前项目：${projectLabel(currentProject())}`);
  setStatus(`当前项目：${projectLabel(currentProject())}`);
  return true;
}

function renderProjectList() {
  if (!projectListEl) return;
  if (!projects.length) {
    projectListEl.innerHTML = "<em>暂无项目</em>";
    return;
  }
  projectListEl.innerHTML = `<div class="design-history-list">${projects
    .map((p) => {
      const active = p.project_id === editingProjectId ? "active" : "";
      const current = p.project_id === currentProjectId ? `<span class="design-history-chip current-chip">当前项目</span>` : "";
      return `<button class="design-history-item ${active}" data-project-id="${esc(p.project_id)}" type="button">
        <h4>${esc(projectLabel(p))}</h4>
        <p>${esc((p.description || "").slice(0, 60) || "无说明")}</p>
        <div class="design-history-chips">
          ${current}
          <span class="design-history-chip">测试设计 ${esc(p.design_count || 0)}</span>
          <span class="design-history-chip">资料 ${esc(p.doc_count || 0)}</span>
        </div>
      </button>`;
    })
    .join("")}</div>`;
}

function describeProjectDefaults(project) {
  const lines = [];
  const sel = project?.product_profile_selected || {};
  PRODUCT_PROFILE_GROUPS.forEach((g) => {
    if (Array.isArray(sel[g.key]) && sel[g.key].length) lines.push(`${g.label}: ${sel[g.key].join("、")}`);
  });
  const envIds = new Set(project?.test_environment_ids || []);
  const envs = TEST_ENVIRONMENT_OPTIONS.filter((e) => envIds.has(e.id)).map((e) => e.label);
  if (envs.length) lines.push(`测试环境: ${envs.join("、")}`);
  return lines.length ? renderDocList(lines) : "<em>未设置默认值</em>";
}

async function renderProjectForm(projectId) {
  editingProjectId = projectId || "";
  const p = projects.find((x) => x.project_id === editingProjectId) || null;
  renderProjectList();
  if (projectFormTitle) projectFormTitle.textContent = p ? `编辑：${projectLabel(p)}` : "新建项目";
  if (projectNameEl) projectNameEl.value = p?.name || "";
  if (projectCodeEl) projectCodeEl.value = p?.code || "";
  if (projectDescEl) projectDescEl.value = p?.description || "";
  if (projectKbUrlEl) projectKbUrlEl.value = p?.kb_mcp_url || "";
  projectKbResult?.classList.add("hidden");
  projectKbTestBtn?.classList.toggle("hidden", !p);
  if (projectDefaultsEl) projectDefaultsEl.innerHTML = p ? describeProjectDefaults(p) : "<em>勾选下方选项，保存时把“需求准备”页当前的勾选设为默认值</em>";
  if (projectCaptureDefaultsEl) projectCaptureDefaultsEl.checked = !p;
  useProjectBtn?.classList.toggle("hidden", !p || p.project_id === currentProjectId);
  deleteProjectBtn?.classList.toggle("hidden", !p || p.project_id === DEFAULT_PROJECT_ID);
  projectDocsSection?.classList.toggle("hidden", !p);
  projectDesignsSection?.classList.toggle("hidden", !p);
  if (!p) return;
  const [docData, historyData] = await Promise.all([
    fetchJson(projectDocsUrl(p.project_id)).catch(() => ({ docs: [] })),
    fetchJson(`/api/design-history?project_id=${encodeURIComponent(p.project_id)}`).catch(() => ({ items: [] })),
  ]);
  const docs = docData.docs || [];
  if (projectDocsHint) projectDocsHint.textContent = `共 ${docs.length} 份`;
  if (projectDocsEl) projectDocsEl.innerHTML = renderDocRows(docs, "project", p.project_id);
  const items = historyData.items || [];
  if (projectDesignsEl) {
    projectDesignsEl.innerHTML = items.length
      ? `<table><thead><tr><th>标题</th><th>状态</th><th>用例</th><th>更新时间</th><th></th></tr></thead><tbody>${items
          .map((it) => `<tr><td>${esc(it.title || it.record_id)}</td><td>${esc(it.has_testcases ? "已生成测试用例" : "仅完成测试设计")}</td><td>${esc(it.testcase_count || 0)}</td><td>${esc(it.updated_at || "")}</td>
            <td><button class="ui-btn ui-btn-ghost ui-btn-sm" type="button" data-open-history="${esc(it.record_id)}">打开</button></td></tr>`)
          .join("")}</tbody></table>`
      : "<em>还没有测试设计</em>";
  }
}

async function saveProject() {
  const body = {
    name: (projectNameEl?.value || "").trim(),
    code: (projectCodeEl?.value || "").trim(),
    description: (projectDescEl?.value || "").trim(),
  };
  if (projectKbUrlEl) body.kb_mcp_url = projectKbUrlEl.value.trim();
  if (!body.name) throw new Error("请填写项目名称");
  if (projectCaptureDefaultsEl?.checked) {
    body.product_profile_selected = getSelectedProductProfile().selected;
    body.test_environment_ids = getSelectedTestEnvironments().selected_ids;
  }
  const isNew = !editingProjectId;
  const resp = await fetch(isNew ? "/api/projects" : `/api/projects/${encodeURIComponent(editingProjectId)}`, {
    method: isNew ? "POST" : "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await resp.text();
  if (!resp.ok) {
    let msg = text;
    try { msg = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(msg);
  }
  const saved = JSON.parse(text).project;
  await loadProjects();
  await renderProjectForm(saved.project_id);
  if (saved.project_id === currentProjectId) renderProjectSelect();
  setStatus(`项目已保存：${projectLabel(saved)}`);
  if (isNew && confirm(`已创建“${saved.name}”。现在切换到这个项目吗？`)) {
    setCurrentProject(saved.project_id);
    await renderProjectForm(saved.project_id);
  }
}

async function deleteProject() {
  const p = projects.find((x) => x.project_id === editingProjectId);
  if (!p) return;
  if (!confirm(`确定删除项目“${p.name}”？项目资料会一并删除。`)) return;
  const resp = await fetch(`/api/projects/${encodeURIComponent(p.project_id)}`, { method: "DELETE" });
  const text = await resp.text();
  if (!resp.ok) {
    let msg = text;
    try { msg = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(msg);
  }
  if (p.project_id === currentProjectId) setCurrentProject(DEFAULT_PROJECT_ID, { askReset: false });
  await loadProjects();
  await renderProjectForm("");
  setStatus(`项目已删除：${p.name}`);
}

async function moveHistoryToProject(recordId, projectId) {
  await postJson(`/api/design-history/${encodeURIComponent(recordId)}/project`, { project_id: projectId });
  await loadProjects().catch(() => {});
  await loadDesignHistory(designHistoryAllProjects?.checked ? recordId : "");
  const target = projects.find((p) => p.project_id === projectId);
  setStatus(`测试设计已移到项目：${projectLabel(target)}`);
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
      requirement_meta: requirementMeta(),
      rag_context: ragEl.value,
      product_profile: productProfile,
      test_environments: testEnvironments,
      project_id: currentProjectId,
    });
  } else {
    ensureHitlStream(stageState.hitl_job_id);
    hitlRequestInFlight = true;
    try {
      data = await postJson(`/api/hitl/requirements/${stageState.hitl_job_id}/next`, {
        open_question_answers: collectOpenQuestionAnswers(),
      });
    } finally {
      hitlRequestInFlight = false;
    }
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
  if (typeof clarifyOnSpecChanged === "function") clarifyOnSpecChanged();

  applyStageOutputs();
  renderOpenQuestions(data.open_questions || [], data.auto_confirmed || []);
  if ((data.open_questions || []).length) {
    pushSystemBotMessage(`测试需求评审 v${data.round} 已完成：${data.open_questions.length} 个关键问题需要你确认，另有 ${(data.auto_confirmed || []).length} 个问题 AI 已自行确认。`, { actionNeeded: true });
  } else {
    pushSystemBotMessage(`测试需求评审 v${data.round} 已完成。`);
  }
  setStatus(
    `测试需求评审完成：v${data.round}${data.is_final_round ? "（终稿）" : ""}` +
      (data.rag?.hits?.length ? `\n资料命中: ${data.rag.hits.length} 条片段（${[...new Set(data.rag.hits.map((h) => h.scope_label || h.scope))].join("、")}）` : "\n资料命中: 0") +
      (data.rag?.errors?.length ? `\n知识库异常:\n- ${data.rag.errors.join("\n- ")}` : "") +
      (data.warnings?.length ? `\n告警:\n- ${data.warnings.join("\n- ")}` : "")
  );
  persistCurrentState();
}

async function generateDesign() {
  if (!stageState.requirement_spec) throw new Error("请先完成测试需求评审（至少v1）");
  // 需求没定稿时二次确认“带待澄清继续”，否则后端拒绝生成
  const clarifyGate = typeof clarifyBeforeDesign === "function" ? await clarifyBeforeDesign() : {};
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  const data = await startStageJobAndWait("design", {
    ...clarifyGate,
    requirement_input: parseRequirements(requirementsEl.value),
    requirement_spec: stageState.requirement_spec,
    persona_reviews: stageState.persona_reviews,
    requirement_review_history: stageState.requirement_review_history || {},
    product_profile: productProfile,
    test_environments: testEnvironments,
    history_record_id: stageState.design_history_record_id || "",
    project_id: currentProjectId,
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
  setStatus("测试设计稿已生成，并已归档到历史目录。" + usageLine(data) + (data.warnings?.length ? `\n提示:\n- ${data.warnings.join("\n- ")}` : ""));
  persistCurrentState();
}

async function generateCases() {
  if (!stageState.test_design_spec) throw new Error("请先生成测试设计稿");
  const productProfile = getSelectedProductProfile();
  const testEnvironments = getSelectedTestEnvironments();
  const data = await startStageJobAndWait("testcases", {
    requirement_input: parseRequirements(requirementsEl.value),
    requirement_spec: stageState.requirement_spec,
    persona_reviews: stageState.persona_reviews,
    requirement_review_history: stageState.requirement_review_history || {},
    test_design_spec: stageState.test_design_spec,
    product_profile: productProfile,
    test_environments: testEnvironments,
    history_record_id: stageState.design_history_record_id || "",
    project_id: currentProjectId,
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
  setStatus(`测试用例稿已生成：${(data.test_case_spec?.testcases || []).length} 条 3GPP 风格用例。` + usageLine(data) + (data.warnings?.length ? `\n提示:\n- ${data.warnings.join("\n- ")}` : ""));
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
  refreshExecCasesControls();
  if (execCasesDiffCard && !data?.bundles) execCasesDiffCard.hidden = true;
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
    }${r === "amarisoft" || r === "protocol" ? renderReqConfigPreview(data.bundles[r]) : ""}<details class="raw-json"><summary>JSON</summary><pre class="ui-pre">${esc(JSON.stringify(data.bundles[r], null, 2))}</pre></details></details>`)
    .join("");
}

const REQ_CFG_STATUS = { applied: "已落地", patched: "已按需求值补入", missing: "未落地", not_applicable: "不适用", conflict: "与规范冲突" };

function renderReqConfigPreview(bundle) {
  const items = bundle?.cases || bundle?.items || [];
  const rows = [];
  items.forEach((it) => (it.requirement_configs || []).forEach((rc) => rows.push({ ...rc, case_id: it.case_id })));
  const lines = bundle?.source_requirement?.config_lines || [];
  const missLines = lines.filter((l) => l.status !== "covered" && l.status !== "other_route");
  if (!rows.length && !missLines.length) return "";
  const fmt = (v) => (typeof v === "object" && v !== null ? JSON.stringify(v) : `${v ?? ""}`);
  const table = rows.length
    ? `<table class="ui-table"><thead><tr><th>case</th><th>参数</th><th>需求取值</th><th>状态</th><th>落到字段</th><th>需求原文</th></tr></thead><tbody>${
        rows.map((r) => `<tr><td>${esc(r.case_id || "")}</td><td>${esc(r.name || "")}</td><td><code>${esc(fmt(r.value))}</code></td><td>${
          esc(REQ_CFG_STATUS[r.status] || r.status || "")}</td><td><code>${esc(r.applied_to || "")}</code></td><td>${esc(r.source_text || "")}${
          r.note ? `<br/><span class="feature-hint">${esc(r.note)}</span>` : ""}</td></tr>`).join("")
      }</tbody></table>`
    : "";
  const lineHtml = missLines.length
    ? `<p class="feature-hint">需求原文中以下配置行的取值未全部出现在本文件中，请确认是否遗漏：</p><ul>${
        missLines.map((l) => `<li>${esc(l.text)}（未找到：${esc((l.values || []).filter((v) => !(l.matched_values || []).includes(v)).join("、"))}）</li>`).join("")}</ul>`
    : "";
  return `<div class="req-config"><h5>需求写明的配置落地情况</h5>${table}${lineHtml}</div>`;
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

// ---------- 可执行用例：判断结果是否过期、重新生成后对比变化 ----------

function stableStringify(v) {
  if (Array.isArray(v)) return `[${v.map(stableStringify).join(",")}]`;
  if (v && typeof v === "object") {
    return `{${Object.keys(v).sort().filter((k) => v[k] !== undefined).map((k) => `${JSON.stringify(k)}:${stableStringify(v[k])}`).join(",")}}`;
  }
  return JSON.stringify(v ?? null);
}

function hashText(text) {
  // FNV-1a 32 位，只用来判断输入有没有变化
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

const EXEC_INPUT_LABELS = { testcases: "测试用例", requirements: "需求", product: "产品形态", bugs: "关联的 Bug" };

// 可执行用例只依赖这几样输入：同样的输入再生成一次，只是让大模型把措辞重写一遍
function execInputFingerprint() {
  return {
    testcases: hashText(stableStringify(stageState.test_case_spec || null)),
    requirements: hashText(stableStringify({ input: parseRequirements(requirementsEl?.value || ""), spec: stageState.requirement_spec || null })),
    product: hashText(stableStringify(getSelectedProductProfile().selected || {})),
    bugs: hashText(stableStringify([...(stageState.bug_ids || [])].map(String).sort())),
  };
}

function execCasesFreshness() {
  const data = stageState.executable_cases;
  if (!stageState.test_case_spec) return { state: data?.bundles ? "unknown" : "no_input", changed: [] };
  if (!data?.bundles) return { state: "none", changed: [] };
  const saved = data.input_fingerprint;
  if (!saved || typeof saved !== "object") return { state: "unknown", changed: [] };
  const now = execInputFingerprint();
  const changed = Object.keys(EXEC_INPUT_LABELS).filter((k) => saved[k] !== now[k]);
  return { state: changed.length ? "stale" : "fresh", changed };
}

let execGenBusy = false;

function formatGeneratedAt(iso) {
  return iso ? String(iso).replace("T", " ").slice(0, 16) : "";
}

function refreshExecCasesControls() {
  if (!genExecCasesBtn) return;
  const { state, changed } = execCasesFreshness();
  const data = stageState.executable_cases;
  const tcCount = (stageState.test_case_spec?.testcases || []).length;
  const draftOnly = Object.values(data?.draft_only || {}).reduce((a, b) => a + (Number(b) || 0), 0);
  const label = { none: "生成可执行用例", stale: "按最新输入重新生成", fresh: "重新生成", unknown: "重新生成", no_input: "生成可执行用例" }[state];
  const secondary = state === "fresh" || state === "unknown";
  genExecCasesBtn.classList.toggle("ui-btn-secondary", secondary);
  genExecCasesBtn.dataset.defaultText = label;
  if (!execGenBusy) {
    genExecCasesBtn.textContent = label;
    genExecCasesBtn.disabled = state === "no_input";
  }
  genExecCasesBtn.title = state === "no_input" ? "请先在“测试用例”页生成测试用例" : "";

  if (!execCasesFreshnessEl) return;
  const when = formatGeneratedAt(data?.generated_at);
  let html = "";
  let cls = "";
  if (state === "fresh") {
    cls = "is-fresh";
    html = `<strong>已是最新。</strong>这份结果基于当前的 ${tcCount} 条测试用例${when ? `，生成于 ${esc(when)}` : ""}。`
      + "输入没有变化，重新生成只会让大模型把各平台 case 的措辞重写一遍，用例数量和分流不会变，一般不需要再点。";
    if (draftOnly) html += `<br/>上次有 ${draftOnly} 条用例因大模型不可用，直接用了由测试用例映射的草稿；如果大模型现在可用，重新生成可以得到平台适配后的版本。`;
  } else if (state === "stale") {
    cls = "is-stale";
    html = `<strong>${esc(changed.map((k) => EXEC_INPUT_LABELS[k]).join("、"))}在上次生成后有变化</strong>，下面的可执行用例已过期，请点击右上角“按最新输入重新生成”。`;
  } else if (state === "unknown") {
    html = stageState.test_case_spec
      ? "这份可执行用例来自旧版本的记录，无法判断是否基于当前的测试用例。如果刚改过测试用例、需求或产品形态，请重新生成。"
      : "当前会话没有测试用例，这份可执行用例无法重新生成。";
  } else if (state === "no_input") {
    html = "请先在“测试用例”页生成测试用例，再生成可执行用例。";
  }
  // 输入变了以后，上一次的对比已不代表当前结果
  if (state !== "fresh" && execCasesDiffCard) execCasesDiffCard.hidden = true;
  execCasesFreshnessEl.className = `exec-freshness ${cls}`.trim();
  execCasesFreshnessEl.innerHTML = html;
  execCasesFreshnessEl.hidden = !html;
}

function execCaseTcId(route, c) {
  return String((route === "artemis" || route === "at_agent" ? c?.task?.case_code : (c?.trace?.tc_id || c?.source_tc_id)) || "");
}

function execCaseComparable(c) {
  const { id, case_id, ...rest } = c || {};  // 编号按顺序生成，不算内容变化
  return rest;
}

function execCaseChangedFields(a, b) {
  const fields = new Set();
  const walk = (x, y, prefix) => {
    Object.keys({ ...(x || {}), ...(y || {}) }).forEach((k) => {
      if (stableStringify(x?.[k]) === stableStringify(y?.[k])) return;
      if (k === "task" && !prefix) walk(x?.task, y?.task, "task.");
      else fields.add(prefix + k);
    });
  };
  walk(execCaseComparable(a), execCaseComparable(b), "");
  return [...fields];
}

function diffExecutableCases(prev, next) {
  const routes = Object.keys(EXEC_ROUTE_FILES);
  const casesOf = (data, r) => (data?.bundles?.[r]?.cases || data?.bundles?.[r]?.items || []);
  const counts = routes.map((r) => ({ route: r, before: casesOf(prev, r).length, after: casesOf(next, r).length }));
  const prevRoutes = prev?.routes || {};
  const nextRoutes = next?.routes || {};
  const added = Object.keys(nextRoutes).filter((t) => !(t in prevRoutes));
  const removed = Object.keys(prevRoutes).filter((t) => !(t in nextRoutes));
  const moved = Object.keys(nextRoutes).filter((t) => t in prevRoutes && prevRoutes[t] !== nextRoutes[t])
    .map((t) => ({ tc: t, from: prevRoutes[t], to: nextRoutes[t] }));
  const changed = [];
  routes.forEach((r) => {
    const group = (data) => {
      const m = {};
      casesOf(data, r).forEach((c) => (m[execCaseTcId(r, c)] = m[execCaseTcId(r, c)] || []).push(c));
      return m;
    };
    const a = group(prev);
    const b = group(next);
    Object.keys(b).forEach((tc) => {
      if (!a[tc]) return;
      const fields = new Set();
      const n = Math.max(a[tc].length, b[tc].length);
      for (let i = 0; i < n; i++) execCaseChangedFields(a[tc][i], b[tc][i]).forEach((f) => fields.add(f));
      if (a[tc].length !== b[tc].length) fields.add("case 条数");
      if (fields.size) changed.push({ tc, route: r, fields: [...fields] });
    });
  });
  const countsChanged = counts.some((c) => c.before !== c.after);
  return { counts, countsChanged, added, removed, moved, changed,
    identical: !countsChanged && !added.length && !removed.length && !moved.length && !changed.length };
}

function renderExecCasesDiff(prev, next) {
  if (!execCasesDiffCard || !execCasesDiffEl) return;
  if (!prev?.bundles || !next?.bundles) {
    execCasesDiffCard.hidden = true;
    return null;
  }
  const d = diffExecutableCases(prev, next);
  const labels = next.route_labels || {};
  const rl = (r) => esc(labels[r] || r);
  const total = d.counts.reduce((a, c) => a + c.after, 0);
  const parts = [];
  if (d.identical) {
    parts.push(`<p class="exec-diff-headline"><strong>与上次结果完全一致</strong>（共 ${total} 条可执行 case）。输入没有变化时，重新生成不会带来新内容。</p>`);
  } else {
    const head = [];
    if (!d.countsChanged && !d.added.length && !d.removed.length && !d.moved.length) head.push("用例数量和分流都没变");
    if (d.changed.length) head.push(`${d.changed.length} 条用例对应的 case 内容有改写`);
    parts.push(`<p class="exec-diff-headline"><strong>${esc(head.join("，") || "结果有变化")}</strong>${
      formatGeneratedAt(prev.generated_at) ? `（对比 ${esc(formatGeneratedAt(prev.generated_at))} 那次的结果）` : ""}。</p>`);
    if (d.countsChanged) {
      parts.push(`<table class="ui-table"><thead><tr><th>验收方案</th><th>上次</th><th>本次</th></tr></thead><tbody>${
        d.counts.filter((c) => c.before || c.after).map((c) => `<tr><td>${rl(c.route)}</td><td>${c.before}</td><td>${c.after}${
          c.after !== c.before ? `（${c.after > c.before ? "+" : ""}${c.after - c.before}）` : ""}</td></tr>`).join("")
      }</tbody></table>`);
    }
    const items = [];
    if (d.added.length) items.push(`新增用例：${esc(d.added.join("、"))}`);
    if (d.removed.length) items.push(`移除用例：${esc(d.removed.join("、"))}`);
    d.moved.forEach((m) => items.push(`${esc(m.tc)} 从 ${rl(m.from)} 改分流到 ${rl(m.to)}`));
    if (items.length) parts.push(`<ul class="exec-diff-list">${items.map((x) => `<li>${x}</li>`).join("")}</ul>`);
    if (d.changed.length) {
      parts.push(`<details><summary>查看内容改写明细（${d.changed.length} 条）</summary><table class="ui-table"><thead><tr><th>用例</th><th>验收方案</th><th>变化的字段</th></tr></thead><tbody>${
        d.changed.map((c) => `<tr><td>${esc(c.tc)}</td><td>${rl(c.route)}</td><td>${esc(c.fields.join("、"))}</td></tr>`).join("")
      }</tbody></table></details>`);
    }
  }
  execCasesDiffEl.innerHTML = parts.join("");
  execCasesDiffCard.hidden = false;
  return d;
}

async function generateExecCases() {
  if (!stageState.test_case_spec) throw new Error("请先生成测试用例稿");
  const previous = stageState.executable_cases?.bundles ? stageState.executable_cases : null;
  const fingerprint = execInputFingerprint();
  const data = await startStageJobAndWait("exec_cases", {
    requirement_input: parseRequirements(requirementsEl?.value || ""),
    requirement_spec: stageState.requirement_spec || {},
    test_case_spec: stageState.test_case_spec,
    product_profile: getSelectedProductProfile(),
    test_environments: getSelectedTestEnvironments(),
    bug_ids: stageState.bug_ids || [],
    history_record_id: stageState.design_history_record_id || "",
    input_fingerprint: fingerprint,
  });
  stageState.executable_cases = data.executable_cases || null;
  if (stageState.executable_cases && !stageState.executable_cases.input_fingerprint) stageState.executable_cases.input_fingerprint = fingerprint;
  latestStructured = latestStructured || {};
  latestStructured.executable_cases = stageState.executable_cases;
  renderExecutableCases(stageState.executable_cases);
  const diff = renderExecCasesDiff(previous, stageState.executable_cases);
  const s = stageState.executable_cases?.summary || {};
  const diffLine = !diff ? "" : diff.identical ? "\n与上次结果完全一致。"
    : `\n与上次相比：${diff.changed.length} 条用例的 case 内容有改写${diff.countsChanged || diff.moved.length || diff.added.length || diff.removed.length ? "，数量或分流有变化" : "，数量和分流没变"}（详见“本次重新生成的变化”）。`;
  setStatus(`可执行用例已${previous ? "重新" : ""}生成：Artemis ${s.artemis || 0}，AT Agent ${s.at_agent || 0}，Amarisoft ${s.amarisoft || 0}，协议流程 ${s.protocol || 0}` + diffLine + usageLine(data) +
    (data.warnings?.length ? `\n告警:\n- ${data.warnings.join("\n- ")}` : ""));
  runNote(previous ? "可执行用例已重新生成，变化见“可执行用例”页顶部。" : "可在“可执行用例”页按验收方案下载。");
  persistCurrentState();
}


async function generateAll() {
  const requirements = parseRequirements(requirementsEl.value);
  if (!requirements.length) throw new Error("请先填写需求描述");
  stageState.hitl_job_id = "";
  stageState.design_history_record_id = "";
  stageState.design_history_doc_url = "";
  stageState.test_design_spec = null;
  stageState.test_case_spec = null;
  stageState.executable_cases = null;
  closeHitlStream();
  latestStructured = latestStructured || {};
  const onStageResult = (stage, res) => {
    if (stage === "requirements") {
      stageState.round = 1;
      stageState.requirement_spec = res.requirement_spec;
      stageState.persona_reviews = res.persona_reviews;
      stageState.requirement_review_history = res.requirement_review_history;
      Object.assign(latestStructured, { requirement_spec: res.requirement_spec, persona_reviews: res.persona_reviews, requirement_review_history: res.requirement_review_history });
      renderOpenQuestions([], res.requirement_review_history?.rounds?.[0]?.auto_confirmed || []);
    if (typeof clarifyOnSpecChanged === "function") clarifyOnSpecChanged();
    } else if (stage === "design") {
      stageState.test_design_spec = res.test_design_spec;
      stageState.design_history_record_id = res.design_history?.record_id || stageState.design_history_record_id;
      stageState.design_history_doc_url = res.design_history?.document_url || stageState.design_history_doc_url;
      latestStructured.test_design_spec = res.test_design_spec;
    } else if (stage === "testcases") {
      stageState.test_case_spec = res.test_case_spec;
      latestStructured.test_case_spec = res.test_case_spec;
    } else if (stage === "exec_cases") {
      stageState.executable_cases = res.executable_cases;
      if (stageState.executable_cases && !stageState.executable_cases.input_fingerprint) {
        stageState.executable_cases.input_fingerprint = execInputFingerprint();
      }
      latestStructured.executable_cases = res.executable_cases;
    }
    applyStageOutputs();
    persistCurrentState();
  };
  const data = await startStageJobAndWait("auto", {
    requirement_input: requirements,
    rag_context: ragEl.value,
    product_profile: getSelectedProductProfile(),
    test_environments: getSelectedTestEnvironments(),
    bug_ids: stageState.bug_ids || [],
    project_id: currentProjectId,
  }, { onStageResult });
  // 事件流中途断开时，用最终结果补齐各阶段
  if (data.requirement_spec && !stageState.requirement_spec) onStageResult("requirements", data);
  if (data.test_design_spec) onStageResult("design", data);
  if (data.test_case_spec) onStageResult("testcases", data);
  if (data.executable_cases) onStageResult("exec_cases", data);
  if (stageState.design_history_record_id) await loadDesignHistory(stageState.design_history_record_id).catch(() => {});
  const s = stageState.executable_cases?.summary || {};
  const nTc = (stageState.test_case_spec?.testcases || []).length;
  const nRow = (stageState.test_design_spec?.integrated_matrix || []).length;
  const askedByAi = (data.auto_answered_user_questions || []).length;
  setStatus(`一键生成完成：${nRow} 个测试点，${nTc} 条用例；可执行用例 Artemis ${s.artemis || 0} / AT ${s.at_agent || 0} / Amarisoft ${s.amarisoft || 0} / 协议 ${s.protocol || 0}` +
    usageLine(data) + (askedByAi ? `\n有 ${askedByAi} 个原本需要你确认的问题已采用 AI 建议答案，可在“测试需求评审”页查看，必要时改答案后分步重跑。` : "") +
    (data.warnings?.length ? `\n提示:\n- ${data.warnings.slice(0, 12).join("\n- ")}` : ""));
  runNote(askedByAi
    ? `有 ${askedByAi} 个原本需要你确认的问题已采用 AI 建议答案，可在“测试需求评审”页查看，必要时改答案后分步重跑。`
    : "结果已就绪，点上方已完成的阶段可跳到对应页面；可执行用例页可按验收方案下载 JSON。", { actionNeeded: askedByAi > 0 });
  persistCurrentState();
}

function buildChatContext() {
  const ctx = {};
  const reqs = stageState.requirement_spec?.final_requirements || [];
  if (reqs.length) {
    ctx.requirements = reqs.slice(0, 20).map((r) => ({ req_id: r.req_id, title: r.title, priority: r.priority,
      acceptance: r.acceptance?.pass_fail, explicit_configs: (r.explicit_configs || []).map((c) => `${c.name}=${fmtVal(c.value)}`) }));
  }
  const answered = stageState.requirement_review_history?.answered_questions || [];
  if (answered.length) ctx.confirmed_answers = answered.slice(0, 20).map((q) => `${q.question} → ${q.answer}（${q.source || "用户"}）`);
  const rows = stageState.test_design_spec?.integrated_matrix || [];
  if (rows.length) {
    ctx.design_rows = rows.slice(0, 40).map((r) => ({ row_id: r.row_id, req_id: r.req_id, technique: r.technique, scenario: r.scenario,
      env: r.test_environment?.primary, rationale: r.test_environment?.rationale, key_configuration: r.key_configuration }));
    if ((stageState.test_design_spec.design_advice || []).length) ctx.design_advice = stageState.test_design_spec.design_advice;
  }
  const tcs = stageState.test_case_spec?.testcases || [];
  if (tcs.length) {
    ctx.testcases = tcs.slice(0, 40).map((t) => ({ tc_id: t.tc_id, title: t.title, technique: t.technique, env: t.test_environment?.primary,
      test_purpose: t.test_purpose, messages: (t.procedure || []).filter((p) => p.message).map((p) => `${p.direction} ${p.message}`),
      rows: t.trace?.source_refs, open_points: t.open_points }));
  }
  if (stageState.executable_cases?.summary) ctx.executable_summary = stageState.executable_cases.summary;
  const status = (statusEl?.textContent || "").slice(0, 1500);
  if (status) ctx.latest_status = status;
  const page = document.querySelector(".sheet-tab.active");
  if (page) ctx.current_page = page.textContent.replace(/^\s*\S\s*/, "").trim();
  return ctx;
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
  const labels = data.labels || {};

  // 按流水线顺序列出（服务端已排好），选项上标明是哪个环节用的模板
  const names = Object.keys(promptCache);
  promptSelect.innerHTML = "";
  names.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = labels[name] ? `${labels[name]}（${name}）` : name;
    promptSelect.appendChild(opt);
  });
  if (names.length) {
    promptSelect.value = names[0];
    promptEditor.value = promptCache[names[0]];
  } else {
    promptEditor.value = "";
  }
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
  if (id === "sheet5") refreshExecCasesControls();
  if (id === "sheetClarify" && typeof clarifyOnSheetShown === "function") clarifyOnSheetShown();
  if (id === "sheet9") {
    loadProjects()
      .then(() => renderProjectForm(editingProjectId || currentProjectId))
      .catch((e) => setStatus(`项目列表加载失败: ${e.message}`));
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

autoRunBtn?.addEventListener("click", async () => {
  if (hasSessionWork() && !confirm("一键生成会覆盖当前会话的评审、设计和用例结果，继续吗？")) return;
  setSingleButtonBusy(autoRunBtn, true, "一键生成中...");
  stageButtons.filter((b) => b !== autoRunBtn).forEach((b) => b && (b.disabled = true));
  try {
    setStatus("一键生成：需求评审 → 测试设计 → 测试用例 → 可执行用例 ...");
    await generateAll();
    switchSheetById("sheet5");
  } catch (e) {
    setStatus(`一键生成失败: ${e.message}`);
    if (!runFailedAlready()) pushSystemBotMessage(`一键生成失败：${e.message}`, { actionNeeded: true });
  } finally {
    setSingleButtonBusy(autoRunBtn, false);
    stageButtons.filter((b) => b !== autoRunBtn).forEach((b) => b && (b.disabled = false));
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

document.getElementById("goClarifyBtn")?.addEventListener("click", () => switchSheetById("sheetClarify"));

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
  const { state } = execCasesFreshness();
  if (state === "fresh" && !confirm("当前可执行用例已基于最新的测试用例、需求和产品形态生成。\n\n"
    + "输入没有变化，重新生成只会让大模型把各平台 case 的措辞重写一遍，用例数量和分流不会变，生成完会列出与上次的差异。\n\n确定要重新生成吗？")) return;
  if (state === "unknown" && !confirm("无法判断这份可执行用例是否基于当前的测试用例。重新生成会用当前的测试用例覆盖现有结果，生成完会列出与上次的差异。\n\n确定要重新生成吗？")) return;
  execGenBusy = true;
  setSingleButtonBusy(genExecCasesBtn, true, "生成中...");
  stageButtons.filter((b) => b !== genExecCasesBtn).forEach((b) => b && (b.disabled = true));
  try {
    setStatus("正在生成可执行用例 ...");
    await generateExecCases();
    switchSheetById("sheet5");
  } catch (e) {
    setStatus(`生成可执行用例失败: ${e.message}`);
  } finally {
    execGenBusy = false;
    setSingleButtonBusy(genExecCasesBtn, false);
    stageButtons.filter((b) => b !== genExecCasesBtn).forEach((b) => b && (b.disabled = false));
    refreshExecCasesControls();
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

document.getElementById("reqImportFile")?.addEventListener("change", async (ev) => {
  const file = ev.target.files?.[0];
  ev.target.value = "";
  if (!file) return;
  const box = document.getElementById("reqImportResult");
  if (box) box.innerHTML = "<em>正在读取需求清单…</em>";
  try {
    await importRequirementFile(file);
  } catch (err) {
    if (box) box.innerHTML = `<p class="feature-hint">导入失败：${esc(err?.message || String(err))}</p>`;
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

designHistoryAllProjects?.addEventListener("change", () => {
  loadDesignHistory().catch((e) => setStatus(`测试设计历史加载失败: ${e.message}`));
});

designHistoryMeta?.addEventListener("change", (ev) => {
  const sel = ev.target.closest("#designHistoryProjectSelect");
  if (!sel) return;
  moveHistoryToProject(sel.dataset.recordId, sel.value).catch((e) => setStatus(`移动测试设计失败: ${e.message}`));
});

projectSelect?.addEventListener("change", () => {
  setCurrentProject(projectSelect.value);
});

reqProjectSelect?.addEventListener("change", () => {
  setCurrentProject(reqProjectSelect.value);
});

reqProjectManageBtn?.addEventListener("click", () => switchSheetById("sheet9"));

projectListEl?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-project-id]");
  if (!btn) return;
  renderProjectForm(btn.getAttribute("data-project-id")).catch((e) => setStatus(`加载项目失败: ${e.message}`));
});

newProjectBtn?.addEventListener("click", () => {
  renderProjectForm("").catch(() => {});
  projectNameEl?.focus();
});

saveProjectBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(saveProjectBtn, true, "保存中...");
  try {
    await saveProject();
  } catch (e) {
    setStatus(`保存项目失败: ${e.message}`);
    alert(`保存项目失败：${e.message}`);
  } finally {
    setSingleButtonBusy(saveProjectBtn, false);
  }
});

useProjectBtn?.addEventListener("click", () => {
  if (editingProjectId && setCurrentProject(editingProjectId)) renderProjectForm(editingProjectId).catch(() => {});
});

deleteProjectBtn?.addEventListener("click", () => {
  deleteProject().catch((e) => {
    setStatus(`删除项目失败: ${e.message}`);
    alert(`删除项目失败：${e.message}`);
  });
});

uploadProjectDocBtn?.addEventListener("click", async () => {
  const files = Array.from(projectDocFileEl?.files || []);
  if (!editingProjectId || !files.length) {
    setStatus("请先选择项目和至少一个文件");
    return;
  }
  setSingleButtonBusy(uploadProjectDocBtn, true, "上传中...");
  try {
    const { ok, errors } = await uploadDocsTo(projectDocsUrl(editingProjectId), files);
    projectDocFileEl.value = "";
    await loadProjects();
    await renderProjectForm(editingProjectId);
    if (editingProjectId === currentProjectId) fetchRagDocs().catch(() => {});
    setStatus(`项目资料上传完成：成功 ${ok}` + (errors.length ? `，失败 ${errors.length}\n- ${errors.join("\n- ")}` : ""));
  } finally {
    setSingleButtonBusy(uploadProjectDocBtn, false);
  }
});

document.addEventListener("click", (ev) => {
  const del = ev.target.closest("[data-doc-delete]");
  if (del) {
    deleteDoc(del.dataset.docScope, del.dataset.docDelete, del.dataset.projectId)
      .then(() => { if (del.dataset.docScope === "project" && editingProjectId) return renderProjectForm(editingProjectId); })
      .catch((e) => setStatus(`删除资料失败: ${e.message}`));
    return;
  }
  const open = ev.target.closest("[data-open-history]");
  if (open) {
    switchSheetById("sheet8");
    loadDesignHistory(open.dataset.openHistory)
      .then(() => { designHistoryLoaded = true; })
      .catch((e) => setStatus(`测试设计历史加载失败: ${e.message}`));
  }
});

function showTestResult(el, ok, text) {
  if (!el) return;
  el.classList.remove("hidden");
  el.classList.toggle("ok", ok);
  el.classList.toggle("err", !ok);
  el.textContent = text;
}

function kbFormPayload(extra = {}) {
  return {
    mcp_url: (kbMcpUrlEl?.value || "").trim(),
    timeout: Number(kbTimeoutEl?.value) || null,
    max_query_chars: Number(kbMaxQueryEl?.value) || null,
    ...extra,
  };
}

// 配置了公共知识库后，公共资料统一放知识库，本地不再提供“存入公共资料”
function applyKbAvailability(data) {
  const publicOpt = ragTargetEl?.querySelector('option[value="public"]');
  const usePublicKb = !!data?.enabled;
  if (publicOpt) publicOpt.hidden = usePublicKb;
  if (usePublicKb && ragTargetEl) ragTargetEl.value = "project";
}

async function loadKbSettings() {
  const data = await fetchJson("/api/settings/kb");
  applyKbAvailability(data);
  if (kbMcpUrlEl) kbMcpUrlEl.value = data.mcp_url || "";
  if (kbTimeoutEl) kbTimeoutEl.value = data.timeout || 60;
  if (kbMaxQueryEl) kbMaxQueryEl.value = data.max_query_chars || 500;
  return data;
}

function describeKbTest(data) {
  const docs = (data.documents || []).slice(0, 5).join("、");
  return `连接成功（${data.latency_ms} ms）` + (docs ? `，引用来源：${docs}` : "，回答里没有列出引用来源");
}

async function testKb(projectId = "") {
  const query = (kbTestQueryEl?.value || "").trim() || "测试连接";
  return await postJson("/api/settings/kb/test", kbFormPayload({ query, project_id: projectId }));
}

kbSaveBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(kbSaveBtn, true, "保存中...");
  try {
    await postJson("/api/settings/kb", kbFormPayload());
    await loadKbSettings();
    showTestResult(kbTestResult, true, "知识库设置已保存");
  } catch (e) {
    showTestResult(kbTestResult, false, `保存失败：${e.message}`);
  } finally {
    setSingleButtonBusy(kbSaveBtn, false);
  }
});
kbTestBtn?.addEventListener("click", async () => {
  setSingleButtonBusy(kbTestBtn, true, "测试中...");
  try {
    showTestResult(kbTestResult, true, describeKbTest(await testKb()));
  } catch (e) {
    showTestResult(kbTestResult, false, `连接失败：${e.message}`);
  } finally {
    setSingleButtonBusy(kbTestBtn, false);
  }
});
projectKbTestBtn?.addEventListener("click", async () => {
  if (!editingProjectId) return;
  setSingleButtonBusy(projectKbTestBtn, true, "测试中...");
  try {
    // 用输入框里的地址测试（未保存也可以）；超时等参数沿用已保存的知识库设置
    const cfg = await fetchJson("/api/settings/kb");
    const data = await postJson("/api/settings/kb/test", {
      mcp_url: cfg.mcp_url || "",
      query: "测试连接",
      project_id: editingProjectId,
      project_mcp_url: (projectKbUrlEl?.value || "").trim(),
    });
    showTestResult(projectKbResult, true, describeKbTest(data));
  } catch (e) {
    showTestResult(projectKbResult, false, `连接失败：${e.message}`);
  } finally {
    setSingleButtonBusy(projectKbTestBtn, false);
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
    loadKbSettings().catch((e) => setStatus(`加载知识库设置失败: ${e.message}`)),
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
  if (llmMaxTokensEl) llmMaxTokensEl.value = data.max_tokens || 0;
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
    max_tokens: Math.max(0, Number(llmMaxTokensEl?.value) || 0),
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

goExecCasesBtn?.addEventListener("click", () => {
  const { state } = execCasesFreshness();
  switchSheetById("sheet5");
  // 已有结果且没过期（或无法判断）时只跳转查看，要不要重新生成由用户在页面上决定
  if (state === "none" || state === "stale") genExecCasesBtn?.click();
});

// init
initTheme();
initTabs();
renderTestTypeOptions();
renderTestEnvironmentOptions();
renderProductProfileOptions();
renderDesignHistoryDetail(null);
try { currentProjectId = localStorage.getItem(CURRENT_PROJECT_KEY) || DEFAULT_PROJECT_ID; } catch (_) {}
restoreLastResultUI(loadLastResult());
refreshExecCasesControls();
loadBugzillaSettings().catch(() => {});
loadLlmSettings().catch(() => {});
loadKbSettings().catch(() => {});
loadProjects()
  .catch((e) => setStatus(`加载项目列表失败: ${e.message}`))
  .finally(() => fetchRagDocs().catch((e) => setStatus(`加载RAG文档列表失败: ${e.message}`)));

window.addEventListener("beforeunload", () => {
  revokeDesignDocUrl();
  closeHitlStream();
  closeStageStream();
});
