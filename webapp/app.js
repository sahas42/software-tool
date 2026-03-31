/* === Compliance Checker — App Logic (v2) === */

const $ = (id) => document.getElementById(id);

// ===================== DOM refs =====================
const form = $('audit-form');
const submitBtn = $('submit-btn');

// Rules file
const rulesDropZone = $('rules-drop-zone');
const rulesFileInput = $('rules-file');
const rulesBrowseBtn = $('rules-browse-btn');
const rulesFileSelected = $('rules-file-selected');
const rulesChipName = $('rules-chip-name');
const rulesFileRemove = $('rules-file-remove');

// Source tabs
const srcTabs = document.querySelectorAll('.src-tab');
const tabPanels = document.querySelectorAll('.tab-panel');

// GitHub
const cobaseUrl = $('codebase-url');

// ZIP
const zipDropZone = $('zip-drop-zone');
const zipFileInput = $('codebase-zip');
const zipBrowseBtn = $('zip-browse-btn');
const zipFileSelected = $('zip-file-selected');
const zipChipName = $('zip-chip-name');
const zipFileRemove = $('zip-file-remove');

// Files
const filesDropZone = $('files-drop-zone');
const filesInput = $('codebase-files');
const filesBrowseBtn = $('files-browse-btn');
const filesList = $('files-list');

// Folder
const folderDropZone = $('folder-drop-zone');
const folderInput = $('codebase-folder');
const folderBrowseBtn = $('folder-browse-btn');
const folderList = $('folder-list');

// API key
const apiKeyInput = $('api-key');
const toggleKey = $('toggle-key');

// Regions
const checkerCard = $('checker');
const loadingSection = $('loading-section');
const reportSection = $('report-section');
const globalError = $('global-error');
const errorText = $('error-text');
const retryBtn = $('retry-btn');
const newAuditBtn = $('new-audit-btn');
const downloadJsonBtn = $('download-json-btn');

const lSteps = [$('lStep1'), $('lStep2'), $('lStep3'), $('lStep4')];

let selectedRulesFile = null;
let selectedZipFile = null;
let selectedFiles = [];  // for multi-file
let activeTab = 'github';
let lastReport = null;
let loadingTimer = null;

// ===================== SOURCE TABS =====================
srcTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    srcTabs.forEach(t => t.classList.remove('active'));
    tabPanels.forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    activeTab = tab.dataset.tab;
    $(`panel-${activeTab}`).classList.add('active');
    clearAllErrors();
  });
});

// ===================== PIPELINE + EMBED MODEL =====================
const embedModelOptions = $('embed-model-options');

function updateEmbedVisibility() {
  const pipelineRadios = document.getElementsByName('pipeline_type');
  let selectedPipeline = 'vanilla';
  for (const r of pipelineRadios) {
    if (r.checked) selectedPipeline = r.value;
  }
  embedModelOptions.style.display = selectedPipeline === 'advanced' ? 'block' : 'none';
}

// Attach listener to each pipeline radio button
document.getElementsByName('pipeline_type').forEach(r => {
  r.addEventListener('change', updateEmbedVisibility);
});


// ===================== RULES FILE =====================
rulesBrowseBtn.addEventListener('click', () => rulesFileInput.click());
rulesDropZone.addEventListener('click', (e) => { if (e.target !== rulesBrowseBtn) rulesFileInput.click(); });
rulesFileInput.addEventListener('change', () => { if (rulesFileInput.files[0]) setRulesFile(rulesFileInput.files[0]); });
setupDrop(rulesDropZone, (file) => setRulesFile(file));

function setRulesFile(file) {
  selectedRulesFile = file;
  rulesChipName.textContent = file.name;
  rulesDropZone.style.display = 'none';
  rulesFileSelected.style.display = 'block';
  clearError('rules-error');
}
rulesFileRemove.addEventListener('click', () => {
  selectedRulesFile = null;
  rulesFileInput.value = '';
  rulesFileSelected.style.display = 'none';
  rulesDropZone.style.display = 'flex';
});

// ===================== ZIP =====================
zipBrowseBtn.addEventListener('click', () => zipFileInput.click());
zipDropZone.addEventListener('click', (e) => { if (e.target !== zipBrowseBtn) zipFileInput.click(); });
zipFileInput.addEventListener('change', () => { if (zipFileInput.files[0]) setZipFile(zipFileInput.files[0]); });
setupDrop(zipDropZone, (file) => { if (file.name.endsWith('.zip')) setZipFile(file); else setError('zip-error', 'Please drop a .zip file.'); });

function setZipFile(file) {
  selectedZipFile = file;
  zipChipName.textContent = `${file.name} (${formatBytes(file.size)})`;
  zipDropZone.style.display = 'none';
  zipFileSelected.style.display = 'block';
  clearError('zip-error');
}
zipFileRemove.addEventListener('click', () => {
  selectedZipFile = null;
  zipFileInput.value = '';
  zipFileSelected.style.display = 'none';
  zipDropZone.style.display = 'flex';
});

// ===================== FILES =====================
filesBrowseBtn.addEventListener('click', () => filesInput.click());
filesDropZone.addEventListener('click', (e) => { if (e.target !== filesBrowseBtn) filesInput.click(); });
filesInput.addEventListener('change', () => { if (filesInput.files.length) renderMultiFiles(Array.from(filesInput.files), 'files'); });
setupDropMulti(filesDropZone, (files) => renderMultiFiles(files, 'files'));

// ===================== FOLDER =====================
folderBrowseBtn.addEventListener('click', () => folderInput.click());
folderDropZone.addEventListener('click', (e) => { if (e.target !== folderBrowseBtn) folderInput.click(); });
folderInput.addEventListener('change', () => { if (folderInput.files.length) renderMultiFiles(Array.from(folderInput.files), 'folder'); });
setupDropMulti(folderDropZone, (files) => renderMultiFiles(files, 'folder'));

function renderMultiFiles(files, type) {
  if (!files.length) return;
  selectedFiles = files;
  const container = type === 'files' ? filesList : folderList;
  const dropZone = type === 'files' ? filesDropZone : folderDropZone;
  container.innerHTML = '';
  dropZone.style.display = 'none';

  const countChip = document.createElement('div');
  countChip.className = 'multi-count';
  countChip.textContent = `${files.length} file${files.length !== 1 ? 's' : ''} selected`;
  container.appendChild(countChip);

  // Show up to 8 chips then summarise
  files.slice(0, 8).forEach(f => {
    const chip = document.createElement('div');
    chip.className = 'multi-chip';
    chip.innerHTML = `<span class="multi-chip-name">${escapeHtml(f.name)}</span>`;
    container.appendChild(chip);
  });
  if (files.length > 8) {
    const more = document.createElement('div');
    more.className = 'multi-chip';
    more.textContent = `+${files.length - 8} more…`;
    container.appendChild(more);
  }

  // add clear button
  const clearBtn = document.createElement('button');
  clearBtn.type = 'button'; clearBtn.className = 'drop-browse'; clearBtn.textContent = 'Clear';
  clearBtn.style.cssText = 'margin-left:8px;font-size:12px;';
  clearBtn.addEventListener('click', () => {
    selectedFiles = [];
    container.innerHTML = '';
    container.style.display = 'none';
    dropZone.style.display = 'flex';
    if (type === 'files') filesInput.value = '';
    else folderInput.value = '';
  });
  container.appendChild(clearBtn);
  container.style.display = 'flex';
  clearError(type === 'files' ? 'files-error' : 'folder-error');
}

// ===================== DROP HELPERS =====================
function setupDrop(zone, cb) {
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) cb(file);
  });
}
function setupDropMulti(zone, cb) {
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files);
    if (files.length) cb(files);
  });
}

// ===================== API KEY TOGGLE =====================
toggleKey.addEventListener('click', () => {
  const isPw = apiKeyInput.type === 'password';
  apiKeyInput.type = isPw ? 'text' : 'password';
  toggleKey.querySelector('.eye-icon').style.opacity = isPw ? '0.4' : '1';
});

// ===================== ERRORS =====================
function clearError(id) { const el = $(id); if (el) el.textContent = ''; }
function setError(id, msg) { const el = $(id); if (el) el.textContent = msg; }
function clearAllErrors() { ['rules-error', 'url-error', 'zip-error', 'files-error', 'folder-error', 'key-error', 'codebase-error'].forEach(clearError); }

// ===================== VALIDATION =====================
function validate() {
  let valid = true;
  clearAllErrors();

  if (!selectedRulesFile) { setError('rules-error', 'Please upload a rules file (.yaml or .pdf)'); valid = false; }

  if (activeTab === 'github') {
    const url = cobaseUrl.value.trim();
    if (!url) { setError('url-error', 'GitHub repository URL is required.'); valid = false; }
    else if (!/^https?:\/\/(www\.)?github\.com\/.+/.test(url)) { setError('url-error', 'Please enter a valid GitHub URL.'); valid = false; }
  } else if (activeTab === 'zip') {
    if (!selectedZipFile) { setError('zip-error', 'Please upload a ZIP archive.'); valid = false; }
  } else if (activeTab === 'files') {
    if (!selectedFiles.length) { setError('files-error', 'Please select at least one source file.'); valid = false; }
  } else if (activeTab === 'folder') {
    if (!selectedFiles.length) { setError('folder-error', 'Please select a folder.'); valid = false; }
  }

  const key = apiKeyInput.value.trim();
  if (!key || key.length < 20) { setError('key-error', 'Please enter a valid Gemini API key.'); valid = false; }

  return valid;
}

// ===================== LOADING STEPS =====================
let stepIdx = 0;
const STEP_DURATIONS = [1200, 1000, 6000, 800];

function startLoadingSteps() {
  stepIdx = 0;
  lSteps.forEach(s => s.classList.remove('active', 'done'));
  lSteps[0].classList.add('active');
  advanceStep();
}
function advanceStep() {
  if (stepIdx >= lSteps.length - 1) return;
  loadingTimer = setTimeout(() => {
    lSteps[stepIdx].classList.remove('active');
    lSteps[stepIdx].classList.add('done');
    stepIdx++;
    lSteps[stepIdx].classList.add('active');
    advanceStep();
  }, STEP_DURATIONS[stepIdx]);
}
function finishLoadingSteps() {
  if (loadingTimer) clearTimeout(loadingTimer);
  lSteps.forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
}

// ===================== UI STATE =====================
function showLoading() {
  checkerCard.style.display = 'none';
  reportSection.style.display = 'none';
  globalError.style.display = 'none';
  loadingSection.style.display = 'flex';
  startLoadingSteps();
}
function showReport() {
  finishLoadingSteps();
  setTimeout(() => {
    loadingSection.style.display = 'none';
    reportSection.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, 500);
}
function showErrorState(msg) {
  finishLoadingSteps();
  loadingSection.style.display = 'none';
  checkerCard.style.display = 'none';
  globalError.style.display = 'block';
  errorText.textContent = msg;
}
function resetToForm() {
  reportSection.style.display = 'none';
  globalError.style.display = 'none';
  loadingSection.style.display = 'none';
  checkerCard.style.display = 'block';
  submitBtn.disabled = false;
  submitBtn.querySelector('.submit-btn-text').textContent = 'Run Compliance Audit';
}

// ===================== REPORT RENDER =====================
function renderReport(data) {
  lastReport = data;
  const isCompliant = data.is_compliant;
  const violations = data.violations || [];

  const banner = $('verdict-banner');
  banner.className = 'verdict-banner ' + (isCompliant ? 'compliant' : 'non-compliant');
  $('verdict-icon').textContent = isCompliant ? '✅' : '❌';
  $('verdict-label').textContent = isCompliant ? 'COMPLIANT' : 'NON-COMPLIANT';
  $('verdict-sub').textContent = isCompliant
    ? 'No violations found. The codebase follows all dataset usage rules.'
    : `${violations.length} violation${violations.length !== 1 ? 's' : ''} found in the codebase.`;

  const high = violations.filter(v => v.severity === 'high').length;
  const medium = violations.filter(v => v.severity === 'medium').length;
  const low = violations.filter(v => v.severity === 'low').length;
  $('stats-row').innerHTML = `
    <div class="stat-chip"><div class="stat-value stat-neutral">${violations.length}</div><div class="stat-label">Total</div></div>
    <div class="stat-chip"><div class="stat-value stat-high">${high}</div><div class="stat-label">High</div></div>
    <div class="stat-chip"><div class="stat-value stat-medium">${medium}</div><div class="stat-label">Medium</div></div>
    <div class="stat-chip"><div class="stat-value stat-low">${low}</div><div class="stat-label">Low</div></div>
  `;

  $('report-summary-block').innerHTML = `<strong>AI Analysis Summary</strong>${escapeHtml(data.summary || 'No summary provided.')}`;

  const container = $('violations-container');
  container.innerHTML = '';
  if (violations.length === 0) {
    container.innerHTML = `<div style="text-align:center;padding:44px;background:var(--bg-glass);border:1px solid var(--border);border-radius:var(--radius-md);"><div style="font-size:38px;margin-bottom:14px;">🎉</div><div style="font-size:15px;font-weight:600;color:var(--compliant);margin-bottom:7px;">All Clear!</div><div style="font-size:13px;color:var(--text-secondary);">No violations were detected in the codebase.</div></div>`;
  } else {
    violations.forEach((v, i) => {
      const sev = (v.severity || 'low').toLowerCase();
      const card = document.createElement('div');
      card.className = 'violation-card';
      card.innerHTML = `
        <div class="violation-header">
          <span class="violation-number">#${String(i + 1).padStart(2, '0')}</span>
          <span class="violation-rule">${escapeHtml(v.violated_rule)}</span>
          <span class="severity-badge severity-${sev}">${sev}</span>
        </div>
        <div class="violation-body">
          <div class="violation-field"><div class="vfield-label">File &amp; Location</div><div class="vfield-value"><span class="file-location"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h6l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/></svg>${escapeHtml(v.file)} · lines ${escapeHtml(v.line_range)}</span></div></div>
          <div class="violation-field"><div class="vfield-label">Code Snippet</div><div class="vfield-value mono">${escapeHtml(v.code_snippet)}</div></div>
          <div class="violation-field"><div class="vfield-label">Explanation</div><div class="vfield-value">${escapeHtml(v.explanation)}</div></div>
        </div>`;
      container.appendChild(card);
    });
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

// ===================== FORM SUBMIT =====================
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validate()) return;

  submitBtn.disabled = true;
  submitBtn.querySelector('.submit-btn-text').textContent = 'Analyzing...';

  const formData = new FormData();
  formData.append('rules_file', selectedRulesFile);
  formData.append('api_key', apiKeyInput.value.trim());
  formData.append('codebase_type', activeTab);

  const pipelineRadios = document.getElementsByName('pipeline_type');
  let selectedPipeline = 'vanilla';
  for (const r of pipelineRadios) {
    if (r.checked) selectedPipeline = r.value;
  }
  formData.append('pipeline_type', selectedPipeline);

  // Only send embed_model when Advanced RAG is active
  if (selectedPipeline === 'advanced') {
    const embedRadios = document.getElementsByName('embed_model');
    let selectedEmbed = 'jina'; // default
    for (const r of embedRadios) {
      if (r.checked) selectedEmbed = r.value;
    }
    formData.append('embed_model', selectedEmbed);
  }

  if (activeTab === 'github') {
    formData.append('codebase_url', cobaseUrl.value.trim());
  } else if (activeTab === 'zip') {
    formData.append('codebase_zip', selectedZipFile);
  } else if (activeTab === 'files' || activeTab === 'folder') {
    selectedFiles.forEach(f => formData.append('codebase_files', f));
  }

  showLoading();

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) {
      showErrorState(data.error || `Server error (${res.status}). Please try again.`);
    } else {
      renderReport(data);
      showReport();
    }
  } catch (err) {
    showErrorState('Network error: Could not reach the server. Make sure Flask is running on port 5001.');
  }
});

// ===================== BUTTONS =====================
newAuditBtn.addEventListener('click', resetToForm);
retryBtn.addEventListener('click', resetToForm);
downloadJsonBtn.addEventListener('click', () => {
  if (!lastReport) return;
  const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'compliance_report.json'; a.click();
  URL.revokeObjectURL(url);
});
