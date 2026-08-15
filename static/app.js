// ATS Resume Intelligence -- GUI logic (vanilla JS, no build step).
// Renders from the AnalysisResult JSON contract defined in app/models.py.

const state = {
  file: null,
  result: null,
};

const $ = (sel) => document.querySelector(sel);

// ---------- Upload / dropzone ----------

const dropzone = $("#dropzone");
const fileInput = $("#file-input");
const fileNameEl = $("#file-name");
const analyzeBtn = $("#analyze-btn");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

function setFile(file) {
  const okExt = /\.(pdf|docx)$/i.test(file.name);
  if (!okExt) {
    showUploadError("Only .pdf and .docx files are supported.");
    return;
  }
  state.file = file;
  fileNameEl.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
  analyzeBtn.disabled = false;
}

// ---------- Analyze ----------

analyzeBtn.addEventListener("click", async () => {
  if (!state.file) return;
  clearUploadError();
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";

  const form = new FormData();
  form.append("file", state.file);
  form.append("industry", $("#industry").value);
  form.append("career_path", $("#career_path").value);
  form.append("target_role", $("#target_role").value);
  form.append("seniority", $("#seniority").value);
  form.append("target_company", $("#target_company").value);
  form.append("background_notes", $("#background_notes").value);
  form.append("job_description", $("#job_description").value);

  try {
    const resp = await fetch("/api/analyze", { method: "POST", body: form });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Analysis failed.");
    }
    const result = await resp.json();
    render(result); // render() sets state.result itself
  } catch (e) {
    // A dead/unreachable server surfaces here as "Failed to fetch" --
    // give that case its own clearer message rather than the raw browser string.
    const isNetworkError = e instanceof TypeError;
    const message = isNetworkError
      ? "Could not reach the server. Is the FastAPI app still running (uvicorn app.main:app)?"
      : e.message;
    showUploadError("Analysis failed: " + message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Resume";
  }
});

// Inline error banner -- deliberately NOT alert(): some browsers/embedded
// webviews suppress native dialogs entirely, which made a dead server look
// like "the button does nothing" instead of a visible error.
function showUploadError(message) {
  let banner = document.getElementById("upload-error");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "upload-error";
    banner.className = "upload-error";
    dropzone.insertAdjacentElement("afterend", banner);
  }
  banner.textContent = message;
  banner.style.display = "block";
}

function clearUploadError() {
  const banner = document.getElementById("upload-error");
  if (banner) banner.style.display = "none";
}

// ---------- Rendering ----------

function render(result) {
  state.result = result;

  $("#viewer-empty").style.display = "none";
  $("#viewer-content").style.display = "block";
  $("#right-empty").style.display = "none";
  $("#right-content").style.display = "block";
  $("#export-btn").style.display = "inline-block";
  $("#export-btn").onclick = () => {
    window.location = `/api/export/${result.document.file_id}/json`;
  };

  renderViewer(result);
  renderScores(result.scores);
  renderNotImplemented(result.not_yet_implemented);
  renderPriorityLists(result);
  renderAllFindings(result.findings);
  renderKeywordCoverage(result.keyword_coverage);
  renderJDMatch(result.jd_match);
}

function renderViewer(result) {
  const container = $("#viewer-content");
  container.innerHTML = "";

  if (result.document.file_type === "pdf") {
    result.document.pages.forEach((page) => {
      const wrap = document.createElement("div");
      wrap.className = "page-wrap";

      const img = document.createElement("img");
      img.src = `/api/pages/${result.document.file_id}/${page.image_path}`;
      wrap.appendChild(img);

      const overlays = result.overlays[String(page.page_number)] || [];
      img.addEventListener("load", () => {
        overlays.forEach((box) => {
          const div = document.createElement("div");
          div.className = `overlay-box ${box.severity}`;
          div.style.left = `${box.x0 * 100}%`;
          div.style.top = `${box.y0 * 100}%`;
          div.style.width = `${(box.x1 - box.x0) * 100}%`;
          div.style.height = `${(box.y1 - box.y0) * 100}%`;
          div.title = "Click for details";
          div.addEventListener("click", () => openDetail(box.finding_id));
          wrap.appendChild(div);
        });
      });

      container.appendChild(wrap);
    });
  } else {
    const docxDiv = document.createElement("div");
    docxDiv.id = "docx-view";
    docxDiv.innerHTML = result.document.docx_html || "<p><em>No renderable content.</em></p>";
    container.appendChild(docxDiv);
  }
}

function checkRowHtml(c) {
  const sourceHtml = c.source
    ? `<span class="check-source" title="${escapeHtml(c.source.claim || "")}">Level ${escapeHtml(c.source.confidence)}${c.source.url ? ` · <a href="${c.source.url}" target="_blank" rel="noopener">source</a>` : ""}</span>`
    : "";
  return `<div class="check-row ${c.passed ? "pass" : "fail"}">
    <span class="check-icon">${c.passed ? "✓" : "✗"}</span>
    <span class="check-body"><span class="check-name">${escapeHtml(c.name)}</span><span class="check-detail">${escapeHtml(c.detail)}</span></span>
    ${sourceHtml}
  </div>`;
}

function scoreRowHtml(key, score) {
  const valueHtml =
    score.status === "computed"
      ? `<span class="score-value">${score.value}/100</span>`
      : `<span class="score-value na">${score.status === "llm_error" ? "error" : "not configured"}</span>`;
  const hasChecks = score.checks && score.checks.length > 0;
  const caret = hasChecks ? `<span class="score-caret">▸</span>` : "";
  const header = `<div class="score-row${hasChecks ? " expandable" : ""}" data-score-key="${key}">${caret}<span>${escapeHtml(score.label)}</span>${valueHtml}</div>`;
  const explanation = score.explanation
    ? `<div class="score-explanation">${escapeHtml(score.explanation)}</div>`
    : "";
  const checksHtml = hasChecks ? score.checks.map(checkRowHtml).join("") : "";
  const body = `<div class="score-checklist" id="checklist-${key}" style="display:none;">${explanation}${checksHtml}</div>`;
  return header + body;
}

function renderScores(scores) {
  const order = [
    "ats_parsing_reliability",
    "ats_structural_compatibility",
    "target_role_alignment",
    "aerospace_keyword_coverage",
    "program_management_positioning",
    "recruiter_readability",
    "executive_seniority_signal",
    "overall_resume_strength",
  ];
  $("#scores-block").innerHTML = order.map((key) => scoreRowHtml(key, scores[key])).join("");
  $("#scores-block").querySelectorAll(".score-row.expandable").forEach((row) => {
    row.addEventListener("click", () => {
      const key = row.dataset.scoreKey;
      const body = document.getElementById(`checklist-${key}`);
      const isOpen = body.style.display !== "none";
      body.style.display = isOpen ? "none" : "block";
      row.classList.toggle("open", !isOpen);
    });
  });
}

function renderNotImplemented(notes) {
  const el = $("#not-implemented-notice");
  if (!notes || !notes.length) {
    el.style.display = "none";
    return;
  }
  el.style.display = "block";
  el.innerHTML =
    "<strong>Not yet available:</strong><ul>" + notes.map((n) => `<li>${escapeHtml(n)}</li>`).join("") + "</ul>";
}

function findingRowHtml(f) {
  return `<div class="finding-row ${f.severity}" data-id="${f.id}">
    <div class="ftitle">${escapeHtml(f.title)}</div>
    <div class="fclass">${escapeHtml(f.classification)} &middot; ${escapeHtml(f.category)}</div>
  </div>`;
}

function attachRowHandlers(container) {
  container.querySelectorAll(".finding-row").forEach((row) => {
    row.addEventListener("click", () => openDetail(row.dataset.id));
  });
}

function renderPriorityLists(result) {
  const byId = Object.fromEntries(result.findings.map((f) => [f.id, f]));

  const fillList = (elId, ids) => {
    const el = $(elId);
    if (!ids.length) {
      el.innerHTML = `<div class="empty-note">Nothing here. That's expected on most reviews.</div>`;
      return;
    }
    el.innerHTML = ids.map((id) => findingRowHtml(byId[id])).join("");
    attachRowHandlers(el);
  };

  fillList("#list-must-fix", result.must_fix);
  fillList("#list-strong", result.strongly_recommended);
  fillList("#list-polish", result.optional_polish);
}

function renderAllFindings(findings) {
  const el = $("#list-all");
  if (!findings.length) {
    el.innerHTML = `<div class="empty-note">No findings at all -- clean structural pass.</div>`;
    return;
  }
  el.innerHTML = findings.map(findingRowHtml).join("");
  attachRowHandlers(el);
}

function renderKeywordCoverage(coverage) {
  const el = $("#keyword-coverage-block");
  if (!coverage) {
    el.innerHTML = `<div class="empty-note">No keyword coverage data.</div>`;
    return;
  }
  const enrichmentNote = coverage.llm_enrichment_ran
    ? `<div class="notice">Includes an LLM semantic-enrichment pass (near-miss matches beyond the dictionary).</div>`
    : `<div class="notice">Dictionary matching only. Set ANTHROPIC_API_KEY to additionally catch semantic near-misses.</div>`;

  const categoriesHtml = coverage.categories
    .map((c) => `<div class="kw-category-row"><span>${escapeHtml(c.label)}</span><span>${c.matched_terms}/${c.total_terms} (${Math.round(c.coverage_ratio * 100)}%)</span></div>`)
    .join("");

  const matchedChips = coverage.matched
    .map((m) => `<span class="kw-chip ${m.via === "llm_semantic" ? "llm" : ""}" title="${escapeHtml(m.matched_form)} · ${escapeHtml(m.category_label)}">${escapeHtml(m.term)}</span>`)
    .join("") || `<span class="empty-note">No terms matched.</span>`;

  const missingChips = coverage.notable_missing
    .slice(0, 15)
    .map((t) => `<span class="kw-chip missing">${escapeHtml(t)}</span>`)
    .join("") || `<span class="empty-note">None.</span>`;

  el.innerHTML = `
    ${enrichmentNote}
    <h3 class="kw-heading">Coverage by category</h3>
    ${categoriesHtml}
    <h3 class="kw-heading">Matched terms (${coverage.matched.length})</h3>
    <div class="kw-chip-row">${matchedChips}</div>
    <h3 class="kw-heading">Notable missing terms (relevant categories)</h3>
    <div class="kw-chip-row">${missingChips}</div>
  `;
}

function renderJDMatch(jdMatch) {
  const el = $("#jd-match-block");
  if (!jdMatch) {
    el.innerHTML = `<div class="empty-note">Paste a job description before analyzing to see a Requirement Coverage Matrix here.</div>`;
    return;
  }
  if (jdMatch.status !== "computed") {
    el.innerHTML = `<div class="notice">${escapeHtml(jdMatch.status)}: ${escapeHtml(jdMatch.explanation || "")}</div>`;
    return;
  }
  const rows = jdMatch.requirements
    .map(
      (r) => `<div class="jd-row jd-${r.resume_coverage}">
        <div class="jd-req"><strong>${escapeHtml(r.requirement)}</strong> <span class="jd-importance">${escapeHtml(r.jd_importance)}</span></div>
        <div class="jd-coverage-tag">${escapeHtml(r.resume_coverage.replace("_", " "))}</div>
        ${r.evidence ? `<div class="jd-evidence">"${escapeHtml(r.evidence)}"</div>` : ""}
        ${r.recommendation ? `<div class="jd-recommendation">${escapeHtml(r.recommendation)}</div>` : ""}
      </div>`
    )
    .join("");
  el.innerHTML = `
    <div class="notice">${escapeHtml(jdMatch.overall_fit_note)}</div>
    ${rows || `<div class="empty-note">No requirements extracted.</div>`}
  `;
}

// Tabs
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-priority").style.display = btn.dataset.tab === "priority" ? "block" : "none";
    $("#tab-all").style.display = btn.dataset.tab === "all" ? "block" : "none";
    $("#tab-keywords").style.display = btn.dataset.tab === "keywords" ? "block" : "none";
    $("#tab-jd").style.display = btn.dataset.tab === "jd" ? "block" : "none";
  });
});

// ---------- Detail drawer ----------

function openDetail(findingId) {
  const f = state.result.findings.find((x) => x.id === findingId);
  if (!f) return;

  document.querySelectorAll(".overlay-box").forEach((b) => b.classList.remove("selected"));
  document.querySelectorAll(`.overlay-box`).forEach((b) => {
    // best-effort re-select if this box corresponds to the finding
  });

  const sourcesHtml = (f.sources || [])
    .map((s) => `<div>&bull; ${escapeHtml(s.source)} (confidence ${s.confidence})${s.url ? ` &mdash; <a href="${s.url}" target="_blank" rel="noopener">link</a>` : ""}</div>`)
    .join("") || "<div class='empty-note'>No external source recorded for this finding.</div>";

  const card = $("#detail-card");
  card.innerHTML = `
    <button id="detail-close">&times;</button>
    <span class="detail-tag ${f.severity}">${escapeHtml(f.severity.toUpperCase())}</span>
    <span class="detail-tag ${f.severity}">${escapeHtml(f.classification)}</span>
    <h3>${escapeHtml(f.title)}</h3>

    <div class="detail-field"><div class="dl-label">Description</div>${escapeHtml(f.description)}</div>
    <div class="detail-field"><div class="dl-label">Why it matters</div>${escapeHtml(f.why_it_matters)}</div>
    <div class="detail-field"><div class="dl-label">ATS Evidence</div>${escapeHtml(f.ats_evidence)}</div>
    ${f.recruiter_impact ? `<div class="detail-field"><div class="dl-label">Recruiter Impact</div>${escapeHtml(f.recruiter_impact)}</div>` : ""}
    ${f.recommended_change ? `<div class="detail-field"><div class="dl-label">Recommended Change</div>${escapeHtml(f.recommended_change)}</div>` : ""}
    <div class="detail-field"><div class="dl-label">Confidence</div>Level ${escapeHtml(f.confidence)}</div>
    <div class="detail-field"><div class="dl-label">Source(s)</div>${sourcesHtml}</div>
  `;
  $("#detail-close").addEventListener("click", closeDetail);
  $("#detail-overlay").classList.add("open");
}

function closeDetail() {
  $("#detail-overlay").classList.remove("open");
}

$("#detail-overlay").addEventListener("click", (e) => {
  if (e.target.id === "detail-overlay") closeDetail();
});

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
