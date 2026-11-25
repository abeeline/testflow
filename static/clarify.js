// 需求澄清与定稿页。数据都在 stageState.requirement_spec 里（clarifications / understanding / baseline），
// 后端接口无状态：每次带上当前 spec，拿回更新后的 spec 再保存会话。
(function () {
  const $ = (id) => document.getElementById(id);
  const els = {
    summary: $("clarifySummary"),
    table: $("clarifyTable"),
    result: $("clarifyResult"),
    changes: $("clarifyChanges"),
    impact: $("clarifyImpact"),
    cards: $("clarifyCards"),
    coverage: $("clarifyCoverage"),
    statusFilter: $("clarifyStatusFilter"),
    kindFilter: $("clarifyKindFilter"),
    search: $("clarifySearch"),
    answerBy: $("clarifyAnswerBy"),
    confirmer: $("clarifyConfirmer"),
    freezeNote: $("clarifyFreezeNote"),
    cardsTodo: $("clarifyCardsTodo"),
    badge: $("clarifyTabBadge"),
  };
  const BY_KEY = "testflow.clarify.by";
  let view = null; // 最近一次 /api/clarify/view 的结果
  let drafts = {}; // 未提交的回答：{CLR-001: {action, answer}}
  let confirmDrafts = {}; // 未提交的理解确认：{req_id: {confirmed, note}}

  try {
    const by = localStorage.getItem(BY_KEY) || "";
    if (els.answerBy) els.answerBy.value = by;
    if (els.confirmer) els.confirmer.value = by;
  } catch (_) {}

  function spec() {
    return stageState.requirement_spec;
  }

  function adopt(res) {
    if (!res?.requirement_spec) return;
    stageState.requirement_spec = res.requirement_spec;
    latestStructured = latestStructured || {};
    latestStructured.requirement_spec = res.requirement_spec;
    view = res;
    if (res.test_design_spec) stageState.test_design_spec = res.test_design_spec;
    if (res.test_case_spec) stageState.test_case_spec = res.test_case_spec;
    if (res.exec_cases) stageState.executable_cases = res.exec_cases;
    if (typeof applyStageOutputs === "function") applyStageOutputs();
    persistCurrentState();
    render();
  }

  async function load() {
    if (!spec()) {
      view = null;
      render();
      return;
    }
    const res = await postJson("/api/clarify/view", { requirement_spec: spec() });
    view = res;
    stageState.requirement_spec = res.requirement_spec;
    render();
  }

  function remember(by) {
    try {
      localStorage.setItem(BY_KEY, by);
    } catch (_) {}
  }

  // ---------- 渲染 ----------

  function render() {
    renderBadge();
    if (!view || !spec()) {
      els.summary.innerHTML = "<em>先完成测试需求评审，这里会列出需要澄清的问题。</em>";
      ["table", "changes", "impact", "cards", "coverage", "result"].forEach((k) => els[k] && (els[k].innerHTML = ""));
      return;
    }
    renderSummary();
    renderKindOptions();
    renderTable();
    renderChanges();
    renderCards();
    renderCoverage();
  }

  function renderBadge() {
    if (!els.badge) return;
    const g = view?.gate;
    if (!g || !spec()) {
      els.badge.classList.add("hidden");
      return;
    }
    els.badge.classList.remove("hidden");
    if (g.frozen) {
      els.badge.textContent = `v${g.baseline?.version || ""}`;
      els.badge.classList.add("is-ok");
      els.badge.title = "需求已定稿";
    } else {
      const n = g.blocking_open.length;
      els.badge.textContent = n ? String(n) : "未定稿";
      els.badge.classList.remove("is-ok");
      els.badge.title = n ? `${n} 条阻塞问题待回答` : "需求还没定稿";
    }
  }

  function renderSummary() {
    const g = view.gate;
    const c = g.counts || {};
    const stat = (n, label, cls = "") => `<span class="clarify-stat ${cls}"><strong>${n}</strong>${esc(label)}</span>`;
    const stats = [
      stat(g.total, "条澄清"),
      stat(c.resolved_by_spec || 0, "规范已定"),
      stat(c.resolved_by_owner || 0, "需求方已答"),
      stat(c.waived || 0, "已豁免"),
      stat(c.open || 0, "待回答", c.open ? "" : "is-good"),
      stat(g.blocking_open.length, "阻塞", g.blocking_open.length ? "is-bad" : "is-good"),
      stat(`${g.requirements - g.unconfirmed.length}/${g.requirements}`, "条需求理解已确认", g.unconfirmed.length ? "" : "is-good"),
    ].join("");
    let gate;
    if (g.frozen) {
      const b = g.baseline || {};
      gate = `<div class="clarify-gate is-frozen">已定稿：基线 v${esc(b.version)}，${esc(b.confirmer)} 于 ${esc(b.frozen_at)} 确认${
        b.allow_pending ? `（带待澄清定稿：${esc((b.pending_req_ids || []).join("、") || "理解未全部确认")}，这些需求的设计和用例会标为待澄清）` : ""
      }。可以生成测试设计。</div>`;
    } else if (g.stale) {
      gate = `<div class="clarify-gate is-open">基线 v${esc(g.baseline?.version)} 已过期：定稿后需求或澄清结论又改过，需要重新定稿。</div>`;
    } else if (g.ready_to_freeze) {
      gate = `<div class="clarify-gate is-open">阻塞问题已清零、理解已全部确认，可以定稿。</div>`;
    } else {
      gate = `<div class="clarify-gate is-open">还不能定稿：${g.blocking_open.length ? `${g.blocking_open.length} 条阻塞问题待回答` : ""}${
        g.blocking_open.length && g.unconfirmed.length ? "，" : ""
      }${g.unconfirmed.length ? `${g.unconfirmed.length} 条需求的理解未确认` : ""}。</div>`;
    }
    els.summary.innerHTML = `<div class="clarify-stats">${stats}</div>${gate}`;
  }

  function renderKindOptions() {
    const items = spec()?.clarifications?.items || [];
    const kinds = [...new Set(items.map((it) => it.kind))];
    const cur = els.kindFilter.value;
    const labels = view.kind_labels || {};
    els.kindFilter.innerHTML =
      `<option value="">全部类型</option>` + kinds.map((k) => `<option value="${esc(k)}">${esc(labels[k] || k)}（${items.filter((i) => i.kind === k).length}）</option>`).join("");
    els.kindFilter.value = kinds.includes(cur) ? cur : "";
  }

  function filteredItems() {
    const items = spec()?.clarifications?.items || [];
    const f = els.statusFilter.value;
    const kind = els.kindFilter.value;
    const q = (els.search.value || "").trim().toLowerCase();
    return items.filter((it) => {
      if (f === "todo" && it.status !== "open") return false;
      if (f === "blocking" && !(it.blocking && it.status === "open")) return false;
      if (!["todo", "blocking", "all"].includes(f) && it.status !== f) return false;
      if (kind && it.kind !== kind) return false;
      if (q) {
        const blob = `${it.id} ${it.req_id} ${it.field} ${it.question} ${it.evidence} ${it.suggestion} ${it.resolution}`.toLowerCase();
        if (!blob.includes(q)) return false;
      }
      return true;
    });
  }

  function renderTable() {
    const items = filteredItems();
    const labels = view.kind_labels || {};
    const stLabels = view.status_labels || {};
    if (!items.length) {
      els.table.innerHTML = `<p class="feature-hint">${els.statusFilter.value === "todo" ? "没有待回答的问题。" : "没有符合筛选条件的条目。"}</p>`;
      return;
    }
    const shown = items.slice(0, 200);
    els.table.innerHTML =
      shown
        .map((it) => {
          const d = drafts[it.id] || {};
          const v = it.verify || {};
          const verify = v.notes?.length
            ? `<div class="ci-verify ${v.level === "reject" ? "is-reject" : v.level === "corrected" ? "is-corrected" : ""}">规范核对：${esc(v.notes.join("；"))}</div>`
            : "";
          const resolution = it.resolution ? `<div class="ci-meta">结论：${esc(it.resolution)}${it.answered_by ? `（${esc(it.answered_by)}）` : ""}</div>` : "";
          const radio = (val, label, disabled = false) =>
            `<label><input type="radio" name="act-${esc(it.id)}" value="${val}" ${d.action === val ? "checked" : ""} ${disabled ? "disabled" : ""}/>${label}</label>`;
          const actions = `<div class="ci-actions">
                <input class="ui-input ci-answer" data-id="${esc(it.id)}" type="text" value="${esc(d.answer || "")}" placeholder="${
                  it.status === "open" ? "需求方回答：给出规范写法 / 具体取值 / 判据" : "如需改结论，填写新的回答"
                }" />
                ${radio("answer", "回答")}${radio("accept", "采纳建议", !it.suggestion)}${radio("waive", "豁免")}${it.status !== "open" ? radio("reopen", "重开") : ""}
              </div>`;
          return `<div class="clarify-item ${it.blocking && it.status === "open" ? "is-blocking" : ""}" data-id="${esc(it.id)}">
            <div class="ci-head"><strong>${esc(it.id)}</strong><span>${esc(it.req_id)}</span><span class="tag">${esc(labels[it.kind] || it.kind)}</span>
              ${it.blocking ? `<span class="prio prio-p0">阻塞</span>` : ""}<span class="st st-${esc(it.status)}">${esc(stLabels[it.status] || it.status)}</span>
              <span>${esc((it.raised_by || []).join(" / "))}</span></div>
            <div class="ci-q">${esc(it.question)}</div>
            ${it.evidence ? `<div class="ci-meta">依据：${esc(it.evidence)}</div>` : ""}
            ${it.suggestion ? `<div class="ci-meta">建议：${esc(it.suggestion)}</div>` : ""}
            ${it.source_text ? `<div class="ci-meta">需求原文：${esc(it.source_text)}</div>` : ""}
            ${resolution}${verify}${actions}
          </div>`;
        })
        .join("") + (items.length > shown.length ? `<p class="feature-hint">只显示前 ${shown.length} 条，共 ${items.length} 条，请用筛选缩小范围。</p>` : "");
  }

  function fmt(v) {
    if (v === null || v === undefined) return "";
    return typeof v === "string" ? v : JSON.stringify(v);
  }

  function renderChanges() {
    const changes = spec()?.clarifications?.changes || [];
    if (!changes.length) {
      els.changes.innerHTML = "<em>暂无改动</em>";
    } else {
      const rows = changes
        .slice(-300)
        .reverse()
        .map(
          (c) =>
            `<tr><td>${esc(c.req_id)}</td><td>${esc(c.clr_id)}</td><td>${esc(c.path)}</td><td><del>${esc(fmt(c.before))}</del></td><td><ins>${esc(fmt(c.after))}</ins></td><td>${esc(c.source || "")}</td></tr>`
        )
        .join("");
      els.changes.innerHTML = `<table class="clarify-diff"><thead><tr><th>需求</th><th>澄清</th><th>位置</th><th>改前</th><th>改后</th><th>依据</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
  }

  function renderImpact(imp) {
    if (!imp || !imp.req_ids?.length) {
      els.impact.innerHTML = "";
      return;
    }
    const arts = Object.entries(imp.by_artifact || {})
      .map(([k, ids]) => `<li>${esc(k)}：${ids.length} 个（${esc(ids.slice(0, 12).join("、"))}${ids.length > 12 ? " …" : ""}）已标为过期</li>`)
      .join("");
    els.impact.innerHTML = `<h4>影响分析</h4><p>受影响需求 ${imp.req_ids.length} 条：${esc(imp.req_ids.join("、"))}</p>${arts ? `<ul>${arts}</ul>` : ""}${
      imp.plan?.length ? `<p class="feature-hint">建议：${esc(imp.plan.join("；"))}</p>` : ""
    }`;
  }

  function renderCards() {
    const cards = view.cards || [];
    const todo = els.cardsTodo.checked;
    const list = cards.filter((c) => !todo || !(confirmDrafts[c.req_id]?.confirmed ?? c.confirmed));
    if (!list.length) {
      els.cards.innerHTML = `<p class="feature-hint">${cards.length ? "全部需求的理解都已确认。" : "暂无需求。"}</p>`;
      return;
    }
    els.cards.innerHTML = list
      .slice(0, 100)
      .map((c) => {
        const d = confirmDrafts[c.req_id] || {};
        const checked = d.confirmed ?? c.confirmed;
        const row = (k) => (c.parts[k]?.length ? `<dt>${k}</dt><dd>${esc(c.parts[k].join("；"))}</dd>` : `<dt>${k}</dt><dd><em>未写</em></dd>`);
        return `<div class="clarify-card ${checked ? "is-confirmed" : ""}" data-req="${esc(c.req_id)}">
          <div class="cc-head">${esc(c.req_id)} ${esc(c.title)} ${c.release ? `<span class="tag">${esc(c.release)}</span>` : ""}
            ${c.blocking_open.length ? `<span class="prio prio-p0">阻塞 ${c.blocking_open.length}</span>` : ""}
            ${c.gaps.length ? `<span class="prio prio-p1">缺${esc(c.gaps.join("/"))}</span>` : ""}</div>
          <dl>${["前提", "触发", "期望", "配置", "判据"].map(row).join("")}</dl>
          <div class="cc-actions">
            <label class="inline-check"><input type="checkbox" class="cc-confirm" ${checked ? "checked" : ""}/> 理解正确</label>
            <input class="ui-input cc-note" type="text" value="${esc(d.note ?? c.note ?? "")}" placeholder="理解不对时写明哪里不对" />
          </div>
        </div>`;
      })
      .join("") + (list.length > 100 ? `<p class="feature-hint">只显示前 100 条，共 ${list.length} 条。</p>` : "");
  }

  function renderCoverage() {
    const cov = view.coverage || [];
    els.coverage.innerHTML = `<table><thead><tr><th>规范 / 检查</th><th>说明</th></tr></thead><tbody>${cov
      .map((c) => `<tr><td>${esc(c.spec)}${c.builtin ? " <span class='tag'>内置</span>" : ""}</td><td>${esc(c.description || "")}</td></tr>`)
      .join("")}</tbody></table>`;
  }

  // ---------- 交互 ----------

  els.table?.addEventListener("input", (ev) => {
    const inp = ev.target.closest(".ci-answer");
    if (!inp) return;
    const id = inp.getAttribute("data-id");
    drafts[id] = drafts[id] || {};
    drafts[id].answer = inp.value;
    if (inp.value.trim() && !drafts[id].action) {
      drafts[id].action = "answer";
      const r = els.table.querySelector(`input[name="act-${CSS.escape(id)}"][value="answer"]`);
      if (r) r.checked = true;
    }
  });
  els.table?.addEventListener("change", (ev) => {
    const r = ev.target;
    if (r.type !== "radio") return;
    const id = r.name.replace(/^act-/, "");
    drafts[id] = drafts[id] || {};
    drafts[id].action = r.value;
  });
  els.cards?.addEventListener("change", (ev) => {
    const card = ev.target.closest(".clarify-card");
    if (!card) return;
    const rid = card.getAttribute("data-req");
    confirmDrafts[rid] = confirmDrafts[rid] || {};
    if (ev.target.classList.contains("cc-confirm")) confirmDrafts[rid].confirmed = ev.target.checked;
    if (ev.target.classList.contains("cc-note")) confirmDrafts[rid].note = ev.target.value;
  });
  [els.statusFilter, els.kindFilter].forEach((el) => el?.addEventListener("change", () => view && renderTable()));
  els.search?.addEventListener("input", () => view && renderTable());
  els.cardsTodo?.addEventListener("change", () => view && renderCards());

  $("clarifyConfirmVisibleBtn")?.addEventListener("click", () => {
    const visible = [...els.cards.querySelectorAll(".clarify-card")].map((c) => c.getAttribute("data-req"));
    if (!visible.length) return;
    if (!confirm(`确认这 ${visible.length} 条需求的理解都正确？请确保每条都看过。`)) return;
    visible.forEach((rid) => {
      confirmDrafts[rid] = { ...(confirmDrafts[rid] || {}), confirmed: true };
    });
    submit().catch((e) => setStatus(`提交失败: ${e.message}`));
  });

  async function submit() {
    if (!spec()) throw new Error("请先完成测试需求评审");
    const by = (els.answerBy.value || "").trim();
    const answers = Object.entries(drafts)
      .filter(([, d]) => d.action && (d.action !== "answer" || (d.answer || "").trim()))
      .map(([id, d]) => ({ id, action: d.action, answer: d.answer || "", by }));
    const hasConfirm = Object.keys(confirmDrafts).length > 0;
    if (!answers.length && !hasConfirm) {
      setStatus("没有要提交的回答或确认。");
      return;
    }
    if (!by) throw new Error("请填写回答人");
    remember(by);
    const res = await postJson("/api/clarify/apply", {
      requirement_spec: spec(),
      answers,
      confirmations: confirmDrafts,
      by,
      test_design_spec: stageState.test_design_spec || null,
      test_case_spec: stageState.test_case_spec || null,
      exec_cases: stageState.executable_cases || null,
    });
    drafts = {};
    confirmDrafts = {};
    adopt(res);
    const r = res.result || {};
    const lines = [];
    if (r.applied?.length) lines.push(`已处理 ${r.applied.length} 条${r.applied.filter((a) => a.level === "corrected").length ? `（其中 ${r.applied.filter((a) => a.level === "corrected").length} 条按规范改正了位置）` : ""}`);
    if (r.rejected?.length) lines.push(`退回 ${r.rejected.length} 条：` + r.rejected.map((x) => `${x.id} ${x.reason}`).join("；"));
    if (r.skipped?.length) lines.push(`跳过 ${r.skipped.length} 条：` + r.skipped.map((x) => `${x.id} ${x.reason}`).join("；"));
    if (r.changes?.length) lines.push(`写回需求 ${r.changes.length} 处`);
    els.result.innerHTML = lines.length ? `<p>${lines.map(esc).join("<br/>")}</p>` : "";
    renderImpact(res.impact);
    setStatus(`需求澄清已提交。${res.requirement_spec?.clarifications?.summary || ""}`);
  }

  $("clarifyApplyBtn")?.addEventListener("click", async (ev) => {
    const btn = ev.currentTarget;
    setSingleButtonBusy(btn, true, "核对中...");
    try {
      await submit();
    } catch (e) {
      setStatus(`提交失败: ${e.message}`);
      els.result.innerHTML = `<p class="feature-hint">${esc(e.message)}</p>`;
    } finally {
      setSingleButtonBusy(btn, false);
    }
  });

  $("clarifyRefreshBtn")?.addEventListener("click", () => load().catch((e) => setStatus(`刷新失败: ${e.message}`)));

  $("clarifyExportBtn")?.addEventListener("click", async () => {
    try {
      if (!spec()) throw new Error("请先完成测试需求评审");
      const resp = await fetch("/api/clarify/export.xlsx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirement_spec: spec() }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "需求澄清单.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setStatus(`导出失败: ${e.message}`);
    }
  });

  $("clarifyImportBtn")?.addEventListener("click", () => $("clarifyImportFile")?.click());
  $("clarifyImportFile")?.addEventListener("change", async (ev) => {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file) return;
    try {
      const content_base64 = await readFileBase64(file);
      const res = await postJson("/api/clarify/import", { filename: file.name, content_base64 });
      const answers = res.answers || [];
      if (!answers.length) {
        setStatus("回填表里没有找到回答（按“编号”列对回，填写“需求方回答 / 处理方式”）。");
        return;
      }
      const known = new Set((spec()?.clarifications?.items || []).map((i) => i.id));
      let n = 0;
      answers.forEach((a) => {
        if (!known.has(a.id)) return;
        drafts[a.id] = { action: a.action || "answer", answer: a.answer || "" };
        if (a.by && !els.answerBy.value) els.answerBy.value = a.by;
        n += 1;
      });
      els.statusFilter.value = "all";
      renderTable();
      setStatus(`已从 ${file.name} 读入 ${n} 条回答${answers.length > n ? `（${answers.length - n} 条编号对不上，已忽略）` : ""}。检查后点“提交回答并核对”。`);
    } catch (e) {
      setStatus(`导入失败: ${e.message}`);
    }
  });

  $("clarifySpecTableBtn")?.addEventListener("click", () => $("clarifySpecTableFile")?.click());
  $("clarifySpecTableFile")?.addEventListener("change", async (ev) => {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file) return;
    try {
      const content_base64 = await readFileBase64(file);
      const res = await postJson("/api/clarify/spec-table", { filename: file.name, content_base64 });
      if (view) view.coverage = res.coverage;
      renderCoverage();
      setStatus(`已加载规范表 ${res.saved}（${res.spec || "未写规范名"}，${res.entries} 项）。下一轮需求评审起生效。`);
    } catch (e) {
      setStatus(`规范表上传失败: ${e.message}`);
    }
  });

  async function freeze(allowPending) {
    const confirmer = (els.confirmer.value || els.answerBy.value || "").trim();
    if (!confirmer) throw new Error("请填写定稿确认人");
    remember(confirmer);
    const res = await postJson("/api/clarify/freeze", {
      requirement_spec: spec(),
      confirmer,
      note: els.freezeNote.value || "",
      allow_pending: !!allowPending,
    });
    adopt(res);
    setStatus(`需求已定稿：基线 v${res.gate?.baseline?.version}。`);
  }

  $("clarifyFreezeBtn")?.addEventListener("click", async (ev) => {
    const btn = ev.currentTarget;
    try {
      if (Object.keys(drafts).length || Object.keys(confirmDrafts).length) {
        if (!confirm("还有没提交的回答或确认，先提交再定稿？")) return;
        await submit();
      }
      if (!view) await load();
      const g = view?.gate;
      let allow = false;
      if (g && !g.ready_to_freeze) {
        allow = confirm(
          `还有 ${g.blocking_open.length} 条阻塞问题待回答、${g.unconfirmed.length} 条需求的理解未确认。\n\n` +
            "仍要带着待澄清定稿吗？这些需求的测试设计和用例会标为“待澄清”，可执行用例不输出。"
        );
        if (!allow) return;
      }
      setSingleButtonBusy(btn, true, "定稿中...");
      await freeze(allow);
    } catch (e) {
      setStatus(`定稿失败: ${e.message}`);
    } finally {
      setSingleButtonBusy(btn, false);
    }
  });

  // 给 app.js 用：生成测试设计前检查是否定稿；没定稿时二次确认“带待澄清继续”
  window.clarifyBeforeDesign = async function () {
    if (!spec()) return { allow_pending_clarification: false };
    const res = await postJson("/api/clarify/view", { requirement_spec: spec() });
    view = res;
    stageState.requirement_spec = res.requirement_spec;
    render();
    const g = res.gate;
    if (g.design_allowed) return { allow_pending_clarification: false };
    const why = g.stale ? "需求定稿后又改过，基线已过期" : "需求还没定稿";
    const ok = confirm(
      `${why}：阻塞问题 ${g.blocking_open.length} 条、理解未确认 ${g.unconfirmed.length} 条。\n\n` +
        "建议先在“需求澄清与定稿”页处理并定稿。\n仍要带待澄清继续生成测试设计吗？（这些需求的设计和用例会标为待澄清）"
    );
    if (!ok) {
      switchSheetById("sheetClarify");
      throw new Error("已取消：请先完成需求澄清与定稿");
    }
    return { allow_pending_clarification: true };
  };

  window.clarifyOnSheetShown = function () {
    load().catch((e) => setStatus(`需求澄清加载失败: ${e.message}`));
  };

  // 需求稿变了（新一轮评审、载入历史）：清掉未提交的草稿并刷新
  window.clarifyOnSpecChanged = function () {
    drafts = {};
    confirmDrafts = {};
    view = null;
    if (document.getElementById("sheetClarify")?.classList.contains("active")) window.clarifyOnSheetShown();
    else if (spec()) load().catch(() => {});
    else render();
  };

  if (spec()) load().catch(() => {});
})();
