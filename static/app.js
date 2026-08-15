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
    alert("Only .pdf and .docx files are supported.");
    return;
  }
  state.file = file;
  fileNameEl.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
  analyzeBtn.disabled = false;
}

// ---------- Analyze ----------

analyzeBtn.addEventListener("click", async () => {
  if (!state.file) return;
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
    alert("Error: " + e.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Resume";
  }
});

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

function scoreRowHtml(score) {
  const valueHtml =
    score.status === "computed"
      ? `<span class="score-value">${score.value}/100</span>`
      : `<span class="score-value na">not yet implemented</span>`;
  return `<div class="score-row"><span>${score.label}</span>${valueHtml}</div>`;
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
  $("#scores-block").innerHTML = order.map((key) => scoreRowHtml(scores[key])).join("");
}

function renderNotImplemented(notes) {
  const el = $("#not-implemented-notice");
  if (!notes || !notes.length) {
    el.style.display = "none";
    return;
  }
  el.style.display = "block";
  el.innerHTML =
    "<strong>Scope note:</strong> This build implements deterministic parsing &amp; ATS structural analysis (Phases 1&ndash;5) only. Not yet implemented: " +
    notes.join(" ");
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

// Tabs
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-priority").style.display = btn.dataset.tab === "priority" ? "block" : "none";
    $("#tab-all").style.display = btn.dataset.tab === "all" ? "block" : "none";
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
