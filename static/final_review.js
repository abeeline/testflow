// 评审修订终稿：只作用于最终生成物（用例稿生成后归档的设计记录）。
// 评审意见 → 后端任务（理解意见 → 改写受影响用例 → IE 闸门 / 追溯锁定 / 新增字段溯源）→ 逐条看改前改后 → 采纳成新版本，可撤销。
// 提案保存在服务端记录目录里，这里只保存提案的展示数据和勾选状态（stageState.revision_proposal）。
(function () {
  const $ = (id) => document.getElementById(id);
  const els = {
    card: $("finalReviewCard"),
    input: $("finalReviewInput"),
    reviewer: $("finalReviewer"),
    btn: $("finalReviewBtn"),
    result: $("finalReviewResult"),
    history: $("finalReviewHistory"),
    version: $("finalVersionTag"),
  };
  if (!els.card) return;
  const REVIEWER_KEY = "testflow.finalReview.reviewer";
  const DRAFT_KEY = "testflow.finalReview.draft";
  const DECISION = { revise: "修改用例", add: "新增用例", remove: "删除用例", reject: "不采纳", requirement_change: "需改需求", no_change: "无需修改" };
  const OP = { update: "修改", add: "新增", remove: "删除" };
  const STATUS = { ok: "可直接采纳", warn: "需要确认", blocked: "未通过核对", failed: "改写失败", noop: "没有变化" };
  let busy = false;
  let recordMeta = { revisions: [], version: 1, recordId: "" };

  try {
    els.reviewer.value = localStorage.getItem(REVIEWER_KEY) || "";
    els.input.value = localStorage.getItem(DRAFT_KEY) || "";
  } catch (_) {}
  els.reviewer.addEventListener("change", () => { try { localStorage.setItem(REVIEWER_KEY, els.reviewer.value.trim()); } catch (_) {} });
  els.input.addEventListener("input", () => { try { localStorage.setItem(DRAFT_KEY, els.input.value); } catch (_) {} });

  // 默认勾选：通过核对、没有无出处新增字段、没有结构问题的修改。其余要人看过再勾。
  function defaultChecked(ch) {
    const g = ch.gate || {};
    if (ch.status === "ok") return true;
    if (ch.status === "warn") return !(g.unbacked || []).length && !(g.issues || []).length && !(g.conflicts || []).length;
    return false;
  }
  function selectable(ch) {
    if (ch.status === "failed" || ch.status === "noop") return false;
    if (ch.op === "remove" && (ch.gate?.lost_coverage || []).length) return false;
    return true;
  }

  function gateLines(ch) {
    const g = ch.gate || {};
    const out = [];
    (g.lost_coverage || []).forEach((r) => out.push(["bad", `删除后需求 ${r} 没有任何用例覆盖，不能删`]));
    (g.ie_errors || []).forEach((x) => out.push(["bad", `IE 不符合 TS 38.331：${x}（采纳后该用例标为待澄清）`]));
    if ((g.unbacked || []).length) out.push(["warn", `新增字段在评审意见、需求和终稿其他用例里都找不到出处：${g.unbacked.join("、")}。确认确实需要再勾选`]);
    (g.conflicts || []).forEach((x) => out.push(["bad", `改写改动了需求写明的取值（${x}）。终稿修订不改需求取值，要改请走“需求澄清与定稿”；采纳后用例里会同时留着需求值，标为待确认`]));
    (g.issues || []).forEach((x) => out.push(["warn", `结构检查：${x}`]));
    (g.locked || []).forEach((x) => out.push(["", x]));
    (g.patched || []).forEach((x) => out.push(["", `需求写明的配置被改写丢了，已补回：${x}`]));
    (g.ie_fixed || []).forEach((x) => out.push(["", `IE 路径已按 ASN.1 自动改正：${x}`]));
    if (g.repaired) out.push(["", "首次改写没通过核对，已带着错误让模型再改了一次"]);
    if (ch.error) out.push(["bad", ch.error]);
    (ch.notes || []).forEach((n) => out.push(["", `改写说明${n.field ? `（${n.field}）` : ""}：${n.what || ""}${n.basis ? `；依据：${n.basis}` : ""}`]));
    return out;
  }

  function diffTable(diff) {
    if (!(diff || []).length) return "";
    const cell = (v, cls) => (v ? `<td class="${cls}">${esc(v)}</td>` : `<td class="empty">—</td>`);
    return `<table class="ui-table fr-diff"><thead><tr><th>字段</th><th>改前</th><th>改后</th></tr></thead><tbody>${
      diff.map((d) => `<tr><th>${esc(d.field)}</th>${cell(d.before, "before")}${cell(d.after, "after")}</tr>`).join("")}</tbody></table>`;
  }

  function renderProposal() {
    const prop = stageState.revision_proposal;
    if (!prop || prop.record_id !== stageState.design_history_record_id) {
      els.result.innerHTML = "";
      return;
    }
    if (!prop.checked) {
      prop.checked = {};
      (prop.changes || []).forEach((ch) => { if (selectable(ch)) prop.checked[ch.change_id] = defaultChecked(ch); });
    }
    const comments = prop.comments || [];
    const changes = (prop.changes || []).filter((c) => c.status !== "noop");
    const counts = {};
    comments.forEach((c) => { counts[c.decision] = (counts[c.decision] || 0) + 1; });
    const head = Object.entries(counts).map(([k, n]) => `${DECISION[k] || k} ${n}`).join(" · ");
    const changeLink = (id) => `<a href="#fr-${esc(id)}">${esc(id)}</a>`;
    const cRows = comments.map((c) => `<tr><td>${esc(c.comment_id)}</td><td>${c.target ? `<span class="tag">${esc(c.target)}</span> ` : ""}${esc(c.text)}${
      c.understanding ? `<div class="feature-hint">AI 理解：${esc(c.understanding)}</div>` : ""}</td>
      <td><span class="fr-decision d-${esc(c.decision)}">${esc(DECISION[c.decision] || c.decision)}</span></td>
      <td>${(c.change_ids || []).map(changeLink).join("、") || (c.outcome ? `<span class="warn-text">${esc(c.outcome)}</span>` : "—")}</td>
      <td>${esc(c.reason || "")}${c.decision === "requirement_change" ? `<div><a href="#" data-fr-go-clarify="1">去需求澄清与定稿 →</a></div>` : ""}</td></tr>`).join("");
    const chHtml = changes.map((ch) => {
      const canPick = selectable(ch);
      const lines = gateLines(ch);
      return `<details class="fr-change s-${esc(ch.status)}" id="fr-${esc(ch.change_id)}" ${ch.status === "ok" && changes.length > 6 ? "" : "open"}>
        <summary>
          <label class="fr-check" onclick="event.stopPropagation()"><input type="checkbox" data-fr-pick="${esc(ch.change_id)}" ${canPick ? "" : "disabled"} ${prop.checked[ch.change_id] ? "checked" : ""}/>${esc(ch.change_id)}</label>
          <span class="tag">${esc(OP[ch.op] || ch.op)}</span><strong>${esc(ch.tc_id)}</strong><span>${esc(ch.title || "")}</span>
          <span class="fr-status s-${esc(ch.status)}">${esc(STATUS[ch.status] || ch.status)}</span>
          <span class="feature-hint">意见 ${esc((ch.comment_ids || []).join("、"))} · ${(ch.diff || []).length} 处字段变化</span>
        </summary>
        <div class="fr-body">
          ${lines.length ? `<ul class="fr-gate">${lines.map(([cls, t]) => `<li class="${cls}">${esc(t)}</li>`).join("")}</ul>` : ""}
          ${ch.op === "add" && ch.row ? `<p class="feature-hint">新测试点 ${esc(ch.row.row_id)} · ${esc(ch.row.req_id)} · ${esc(ch.row.technique || "")} · ${esc(ch.row.scenario || "")}</p>` : ""}
          ${diffTable(ch.diff)}
        </div></details>`;
    }).join("");
    const nPicked = Object.values(prop.checked).filter(Boolean).length;
    const next = (recordMeta.version || prop.version || 1) + 1;
    els.result.innerHTML = `
      <p class="fr-headline"><strong>修订稿已生成</strong>：${comments.length} 条意见（${esc(head)}），${changes.length} 处修改待你确认。${
        prop.reviewer ? `评审人 ${esc(prop.reviewer)}，` : ""}生成于 ${esc(prop.created_at || "")}。</p>
      <table class="ui-table fr-comments"><thead><tr><th>意见</th><th>内容</th><th>处理</th><th>对应修改</th><th>理由 / 说明</th></tr></thead><tbody>${cRows}</tbody></table>
      ${chHtml || `<p class="feature-hint">没有需要改动的用例。</p>`}
      ${changes.length ? `<div class="fr-footer">
        <input id="frNote" class="ui-input" type="text" placeholder="修订说明（可选，写进修订记录）" />
        <button class="ui-btn" type="button" data-fr-accept="1" ${nPicked ? "" : "disabled"}>采纳选中的 ${nPicked} 处修改，生成终稿 v${next}</button>
        <button class="ui-btn ui-btn-ghost" type="button" data-fr-discard="1">放弃这份修订</button>
      </div>` : `<div class="fr-footer"><button class="ui-btn ui-btn-ghost" type="button" data-fr-discard="1">关闭</button></div>`}`;
  }

  function renderHistory() {
    const revs = recordMeta.revisions || [];
    els.version.textContent = `v${recordMeta.version || 1}`;
    if (!revs.length) {
      els.history.innerHTML = "";
      return;
    }
    const doc = stageState.design_history_doc_url ? `<a href="${esc(stageState.design_history_doc_url)}#doc-revisions" target="_blank" rel="noopener noreferrer">在测试设计文档里查看 ↗</a>` : "";
    els.history.innerHTML = `<div class="card-head"><h4>修订记录</h4>${doc}</div><ol>
      <li>v1 · 用例稿生成</li>
      ${revs.map((r, i) => `<li>v${esc(r.version)} · ${esc(r.at || "")}${r.reviewer ? ` · ${esc(r.reviewer)}` : ""} · ${(r.comments || []).length} 条意见，采纳 ${(r.changes || []).length} 处修改${
        (r.skipped || []).length ? `，未采纳 ${r.skipped.length} 处` : ""}${r.note ? ` · ${esc(r.note)}` : ""}${
        i === revs.length - 1 ? ` <button class="ui-btn ui-btn-ghost ui-btn-sm" type="button" data-fr-revert="1">撤销这一版</button>` : ""}</li>`).join("")}
    </ol>`;
  }

  async function refreshRecordMeta() {
    const id = stageState.design_history_record_id;
    if (!id) {
      recordMeta = { revisions: [], version: 1, recordId: "" };
      return;
    }
    try {
      const rec = await fetchJson(`/api/design-history/${encodeURIComponent(id)}`);
      recordMeta = { revisions: rec.final_revisions || [], version: rec.summary?.final_version || 1, recordId: id };
    } catch (_) {
      recordMeta = { revisions: [], version: 1, recordId: id };
    }
  }

  function render() {
    const ready = !!(stageState.test_case_spec?.testcases || []).length && !!stageState.design_history_record_id;
    els.card.hidden = !ready;
    if (!ready) return;
    renderProposal();
    renderHistory();
  }

  window.finalReviewRender = function () {
    render();
    if (stageState.design_history_record_id && recordMeta.recordId !== stageState.design_history_record_id) {
      refreshRecordMeta().then(render);
    }
  };

  window.finalReviewAddComment = function (tcId) {
    const line = `[${tcId}] `;
    const v = els.input.value;
    els.input.value = v && !v.endsWith("\n") ? `${v}\n${line}` : `${v}${line}`;
    els.card.scrollIntoView({ behavior: "smooth", block: "center" });
    els.input.focus();
    els.input.setSelectionRange(els.input.value.length, els.input.value.length);
  };

  function setBusy(on, text) {
    busy = on;
    els.btn.disabled = on;
    els.btn.textContent = on ? (text || "处理中…") : "按意见生成修订稿";
    els.result.querySelectorAll("button").forEach((b) => { b.disabled = on || (b.dataset.frAccept && !Object.values(stageState.revision_proposal?.checked || {}).some(Boolean)); });
  }

  async function generate() {
    if (busy) return;
    const text = els.input.value.trim();
    if (!text) {
      setStatus("请先填写评审意见，每行一条");
      els.input.focus();
      return;
    }
    if (stageState.revision_proposal && !confirm("还有一份没处理的修订稿，重新生成会替换它。继续？")) return;
    setBusy(true, "生成修订稿中…");
    try {
      setStatus("正在按评审意见生成修订稿 ...");
      const data = await startStageJobAndWait("revise", {
        history_record_id: stageState.design_history_record_id,
        review_comments: text,
        reviewer: els.reviewer.value.trim(),
        project_id: typeof currentProjectId !== "undefined" ? currentProjectId : "",
      }, { title: "评审修订终稿" });
      stageState.revision_proposal = data.revision_proposal || null;
      const p = stageState.revision_proposal || {};
      const n = (p.changes || []).filter((c) => c.status !== "noop").length;
      setStatus(`修订稿已生成：${(p.comments || []).length} 条意见，${n} 处修改待确认。` + (data.llm_usage_text ? `\n${data.llm_usage_text}` : ""));
      persistCurrentState();
      render();
      els.result.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      setStatus(`生成修订稿失败: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  function applyNewSpecs(data) {
    stageState.test_design_spec = data.test_design_spec;
    stageState.test_case_spec = data.test_case_spec;
    if (data.design_history?.document_url) stageState.design_history_doc_url = data.design_history.document_url;
    if (typeof latestStructured !== "undefined" && latestStructured) {
      latestStructured.test_design_spec = data.test_design_spec;
      latestStructured.test_case_spec = data.test_case_spec;
    }
    recordMeta.recordId = "";  // 重新拉修订记录
    applyStageOutputs();
  }

  async function accept() {
    const prop = stageState.revision_proposal;
    if (!prop || busy) return;
    const ids = Object.entries(prop.checked || {}).filter(([, v]) => v).map(([k]) => k);
    if (!ids.length) return;
    const risky = (prop.changes || []).filter((c) => ids.includes(c.change_id) && (c.status === "blocked" || (c.gate?.unbacked || []).length));
    if (risky.length && !confirm(`选中的修改里有 ${risky.length} 处未通过核对或带无出处的新增字段（${risky.map((c) => c.change_id).join("、")}）。\n采纳后 IE 有错的用例会标为待澄清。确定采纳？`)) return;
    setBusy(true, "写回终稿中…");
    try {
      const data = await postJson("/api/final-review/accept", {
        record_id: prop.record_id, proposal_id: prop.proposal_id, accepted: ids,
        reviewer: els.reviewer.value.trim() || prop.reviewer || "", note: $("frNote")?.value.trim() || "",
      });
      stageState.revision_proposal = null;
      applyNewSpecs(data);
      try { localStorage.removeItem(DRAFT_KEY); } catch (_) {}
      els.input.value = "";
      setStatus(`终稿已更新到 v${data.version}：采纳 ${(data.revision?.changes || []).length} 处修改。测试设计文档已同步更新；可执行用例需要重新生成。`);
      persistCurrentState();
      if (typeof loadDesignHistory === "function") loadDesignHistory(stageState.design_history_record_id).catch(() => {});
    } catch (e) {
      setStatus(`采纳修订失败: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function revert() {
    if (busy || !confirm(`撤销 v${recordMeta.version}，终稿回到上一版？`)) return;
    setBusy(true);
    try {
      const data = await postJson("/api/final-review/revert", { record_id: stageState.design_history_record_id });
      stageState.revision_proposal = null;
      applyNewSpecs(data);
      setStatus(`已撤销，终稿回到 v${data.version}`);
      persistCurrentState();
    } catch (e) {
      setStatus(`撤销失败: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  els.btn.addEventListener("click", generate);
  els.card.addEventListener("change", (ev) => {
    const id = ev.target?.dataset?.frPick;
    if (!id || !stageState.revision_proposal) return;
    stageState.revision_proposal.checked[id] = ev.target.checked;
    persistCurrentState();
    const n = Object.values(stageState.revision_proposal.checked).filter(Boolean).length;
    const btn = els.result.querySelector("[data-fr-accept]");
    if (btn) {
      btn.disabled = !n;
      btn.textContent = `采纳选中的 ${n} 处修改，生成终稿 v${(recordMeta.version || 1) + 1}`;
    }
  });
  els.card.addEventListener("click", (ev) => {
    const t = ev.target;
    if (t.closest("[data-fr-accept]")) accept();
    else if (t.closest("[data-fr-discard]")) {
      stageState.revision_proposal = null;
      persistCurrentState();
      render();
    } else if (t.closest("[data-fr-revert]")) revert();
    else if (t.closest("[data-fr-go-clarify]")) {
      ev.preventDefault();
      switchSheetById("sheetClarify");
    }
  });
  // app.js 恢复上次会话时本文件还没加载，这里补一次
  window.finalReviewRender();
})();
