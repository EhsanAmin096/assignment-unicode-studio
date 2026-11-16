// Unicode Assignment Transformer & PDF Studio - Client App
let state = {
  files: [],
  activeFileId: null,
  rules: [],
  weeklyCount: parseInt(localStorage.getItem('weekly_unicode_count') || '0', 10),
  activeTab: 'diff',
  highlightEnabled: true,
  isProcessing: false
};

// Initial default rules
const CORE_6_RULES = [
  { find: "l", replace: "\u04CF", unicode: "U+04CF", name: "Cyrillic Palochka", enabled: true },
  { find: "k", replace: "\u03BA", unicode: "U+03BA", name: "Greek Kappa", enabled: true },
  { find: "d", replace: "\u0501", unicode: "U+0501", name: "Cyrillic Komi De", enabled: true },
  { find: "e", replace: "\u0435", unicode: "U+0435", name: "Cyrillic Ie", enabled: true },
  { find: "p", replace: "\u0440", unicode: "U+0440", name: "Cyrillic Er", enabled: true },
  { find: "q", replace: "\u0566", unicode: "U+0566", name: "Armenian Za", enabled: true }
];

const EXTENDED_RULES = [
  { find: "a", replace: "\u0430", unicode: "U+0430", name: "Cyrillic a", enabled: false },
  { find: "c", replace: "\u0441", unicode: "U+0441", name: "Cyrillic es", enabled: false },
  { find: "o", replace: "\u043E", unicode: "U+043E", name: "Cyrillic o", enabled: false },
  { find: "s", replace: "\u0455", unicode: "U+0455", name: "Cyrillic dze", enabled: false },
  { find: "y", replace: "\u0443", unicode: "U+0443", name: "Cyrillic u", enabled: false },
  { find: "x", replace: "\u0445", unicode: "U+0445", name: "Cyrillic ha", enabled: false },
  { find: "i", replace: "\u0456", unicode: "U+0456", name: "Cyrillic i", enabled: false },
  { find: "j", replace: "\u0458", unicode: "U+0458", name: "Cyrillic je", enabled: false }
];

state.rules = JSON.parse(JSON.stringify([...CORE_6_RULES, ...EXTENDED_RULES]));

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  initEventListeners();
  renderRulesTable();
  updateWeeklyBadge();
  
  // Auto-load sample file if queue is empty
  loadSampleAssignment(true);
});

function initEventListeners() {
  // File Drop Zone
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      dropZone.classList.add('border-indigo-500', 'bg-indigo-950/40');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      dropZone.classList.remove('border-indigo-500', 'bg-indigo-950/40');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) handleFileUpload(files);
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files);
    }
  });

  document.getElementById('clearQueueBtn').addEventListener('click', clearQueue);
  document.getElementById('loadSampleBtn').addEventListener('click', () => loadSampleAssignment(false));

  // Presets
  document.getElementById('presetDefault6Btn').addEventListener('click', () => {
    state.rules.forEach((r, idx) => {
      r.enabled = idx < 6;
    });
    renderRulesTable();
    triggerLivePreview();
    showToast('Activated Default 6 (l, k, d, e, p, q)');
  });

  document.getElementById('presetExtendedBtn').addEventListener('click', () => {
    state.rules.forEach(r => { r.enabled = true; });
    renderRulesTable();
    triggerLivePreview();
    showToast('Enabled extended replacement set');
  });

  document.getElementById('presetNoneBtn').addEventListener('click', () => {
    state.rules.forEach(r => { r.enabled = false; });
    renderRulesTable();
    triggerLivePreview();
    showToast('All replacements unchecked');
  });

  // Custom rule add
  document.getElementById('addCustomRuleBtn').addEventListener('click', addCustomRule);
  document.getElementById('customReplaceInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addCustomRule();
  });

  // Scope & Scope Select Change
  document.getElementById('coverScopeSelect').addEventListener('change', triggerLivePreview);
  document.getElementById('removePageNumbersToggle').addEventListener('change', triggerLivePreview);
  document.getElementById('skipUrlsToggle').addEventListener('change', triggerLivePreview);
  document.getElementById('skipHeadingsToggle').addEventListener('change', triggerLivePreview);
  document.getElementById('applyPreviewBtn').addEventListener('click', triggerLivePreview);

  // Tabs
  document.getElementById('tabDiffView').addEventListener('click', () => switchTab('diff'));
  document.getElementById('tabPdfView').addEventListener('click', () => switchTab('pdf'));
  document.getElementById('tabRawView').addEventListener('click', () => switchTab('raw'));

  // Highlight toggle
  document.getElementById('highlightToggle').addEventListener('change', (e) => {
    state.highlightEnabled = e.target.checked;
    renderDiffView(state.currentPreviewData);
  });

  // Download buttons
  document.getElementById('downloadPdfBtn').addEventListener('click', downloadCurrentPdf);
  document.getElementById('downloadDocxBtn').addEventListener('click', downloadCurrentDocx);
  document.getElementById('batchZipBtn').addEventListener('click', batchProcessAll);
  document.getElementById('copyTextBtn').addEventListener('click', copyCleanText);

  // Weekly counter reset
  document.getElementById('resetWeeklyBtn').addEventListener('click', () => {
    state.weeklyCount = 0;
    localStorage.setItem('weekly_unicode_count', '0');
    updateWeeklyBadge();
    showToast('Weekly counter reset');
  });
}

// --- Upload Handler ---
async function handleFileUpload(fileList) {
  const formData = new FormData();
  let validCount = 0;
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    if (file.name.toLowerCase().endsWith('.docx')) {
      formData.append('files', file);
      validCount++;
    }
  }

  if (validCount === 0) {
    showToast('Please select valid .docx files', 'error');
    return;
  }

  showToast(`Uploading ${validCount} file(s)...`);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.uploaded && data.uploaded.length > 0) {
      data.uploaded.forEach(item => {
        state.files.push({
          file_id: item.file_id,
          name: item.name,
          size: item.size,
          status: 'ready'
        });
      });
      state.activeFileId = data.uploaded[0].file_id;
      renderQueueList();
      triggerLivePreview();
      showToast(`✓ Loaded ${validCount} assignment(s) successfully`);
    }
  } catch (err) {
    console.error(err);
    showToast('Upload failed: ' + err.message, 'error');
  }
}

// --- Load Sample File ---
async function loadSampleAssignment(silent = false) {
  try {
    const res = await fetch('/api/load-sample', { method: 'POST' });
    const data = await res.json();
    if (data.file_id) {
      state.files.push({
        file_id: data.file_id,
        name: data.name,
        size: data.size,
        status: 'ready'
      });
      state.activeFileId = data.file_id;
      renderQueueList();
      triggerLivePreview();
      if (!silent) showToast('Unit 1 Assignment sample loaded!');
    }
  } catch (err) {
    console.error('Failed to load sample:', err);
  }
}

function clearQueue() {
  state.files = [];
  state.activeFileId = null;
  state.currentPreviewData = null;
  renderQueueList();
  document.getElementById('diffViewContainer').innerHTML = `
    <div class="text-slate-500 italic text-center py-20">
      Queue cleared. Drop .docx files or click <strong class="text-indigo-400">"Load Unit 1 Sample (.docx)"</strong>.
    </div>
  `;
  document.getElementById('pdfViewContainer').innerHTML = '';
  document.getElementById('rawViewContainer').innerHTML = '';
  document.getElementById('statsFileName').textContent = '—';
  document.getElementById('statsWordCount').textContent = '0';
  document.getElementById('statsTotalRepl').textContent = '0';
  document.getElementById('charCountsBadges').innerHTML = '';
  renderRulesTable();
}

function renderQueueList() {
  const container = document.getElementById('fileQueueList');
  const countBadge = document.getElementById('queueCountBadge');
  countBadge.textContent = `${state.files.length} file${state.files.length === 1 ? '' : 's'} loaded`;

  if (state.files.length === 0) {
    container.innerHTML = `<div class="text-slate-500 text-xs text-center py-4 italic">No files in queue.</div>`;
    return;
  }

  container.innerHTML = '';
  state.files.forEach((file) => {
    const isActive = file.file_id === state.activeFileId;
    const item = document.createElement('div');
    item.className = `px-2.5 py-1.5 rounded-lg flex items-center justify-between gap-2 cursor-pointer text-xs transition ${
      isActive ? 'bg-indigo-600/30 border border-indigo-500/50 text-white font-medium' : 'hover:bg-slate-800/60 text-slate-300'
    }`;
    const kbSize = (file.size / 1024).toFixed(1);
    item.innerHTML = `
      <div class="flex items-center gap-2 truncate">
        <i data-lucide="${isActive ? 'file-check-2' : 'file-text'}" class="w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-400'} shrink-0"></i>
        <span class="truncate" title="${file.name}">${file.name}</span>
      </div>
      <span class="text-[10px] text-slate-400 shrink-0 font-mono">${kbSize} KB</span>
    `;
    item.addEventListener('click', () => {
      state.activeFileId = file.file_id;
      renderQueueList();
      triggerLivePreview();
    });
    container.appendChild(item);
  });
  if (window.lucide) lucide.createIcons();
}

// --- Rules Table ---
function renderRulesTable(countsMap = {}) {
  const tbody = document.getElementById('rulesTableBody');
  tbody.innerHTML = '';

  state.rules.forEach((r, idx) => {
    const count = countsMap[r.find] !== undefined ? countsMap[r.find] : 0;
    const countDisplay = r.enabled ? count.toLocaleString() : '—';
    const countClass = r.enabled && count > 0 ? 'text-emerald-400 font-bold' : 'text-slate-500';

    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition';
    tr.innerHTML = `
      <td class="py-1.5 pr-1">
        <label class="switch-label" style="width:32px;height:18px;">
          <input type="checkbox" class="rule-chk" data-idx="${idx}" ${r.enabled ? 'checked' : ''} />
          <span class="switch-slider"></span>
        </label>
      </td>
      <td class="py-1.5"><span class="px-1.5 py-0.5 rounded bg-[#050811] border border-slate-700 text-slate-200 font-bold">${r.find}</span></td>
      <td class="py-1.5 text-slate-500">→</td>
      <td class="py-1.5"><span class="px-1.5 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/40 text-amber-300 font-bold">${r.replace}</span></td>
      <td class="py-1.5 text-[10px] text-slate-400 font-mono">${r.unicode}</td>
      <td class="py-1.5 text-right font-mono ${countClass}">${countDisplay}</td>
      <td class="py-1.5 text-right">
        ${idx >= CORE_6_RULES.length ? `<button type="button" class="del-rule text-slate-500 hover:text-rose-400 px-1" data-idx="${idx}">✕</button>` : ''}
      </td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('.rule-chk').forEach(input => {
    input.addEventListener('change', function() {
      const idx = parseInt(this.dataset.idx, 10);
      state.rules[idx].enabled = this.checked;
      triggerLivePreview();
    });
  });

  tbody.querySelectorAll('.del-rule').forEach(btn => {
    btn.addEventListener('click', function() {
      const idx = parseInt(this.dataset.idx, 10);
      state.rules.splice(idx, 1);
      renderRulesTable();
      triggerLivePreview();
      showToast('Custom rule removed');
    });
  });
}

function addCustomRule() {
  const fInput = document.getElementById('customFindInput');
  const rInput = document.getElementById('customReplaceInput');
  const find = fInput.value.trim();
  const replace = rInput.value.trim();

  if (!find || !replace) {
    showToast('Enter both find and replace characters', 'error');
    return;
  }

  const hexCode = 'U+' + replace.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0');
  state.rules.push({
    find: find,
    replace: replace,
    unicode: hexCode,
    name: 'Custom',
    enabled: true
  });

  fInput.value = '';
  rInput.value = '';
  renderRulesTable();
  triggerLivePreview();
  showToast(`Added custom rule: ${find} → ${replace} (${hexCode})`);
}

// --- Live Preview Execution ---
async function triggerLivePreview() {
  if (!state.activeFileId) return;

  const activeFile = state.files.find(f => f.file_id === state.activeFileId);
  if (!activeFile) return;

  const payload = {
    file_id: state.activeFileId,
    rules: state.rules,
    cover_mode: document.getElementById('coverScopeSelect').value,
    skip_urls: document.getElementById('skipUrlsToggle').checked,
    skip_headings: document.getElementById('skipHeadingsToggle').checked,
    remove_page_numbers: document.getElementById('removePageNumbersToggle').checked,
    custom_marker: document.getElementById('customMarkerInput').value.trim() || null
  };

  const statusBadge = document.getElementById('statusBadge');
  statusBadge.innerHTML = `<span class="inline-block animate-spin mr-1">⌛</span> Updating Preview...`;

  try {
    const res = await fetch('/api/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      state.currentPreviewData = data.preview;
      renderPreview(data.preview, activeFile.name);
      statusBadge.textContent = `✓ ${data.preview.stats.total_replacements.toLocaleString()} Unicode Replacements Applied`;
    }
  } catch (err) {
    console.error(err);
    statusBadge.textContent = 'Preview error';
    showToast('Preview error: ' + err.message, 'error');
  }
}

function renderPreview(previewData, fileName) {
  const stats = previewData.stats;
  
  // Update footer statistics
  document.getElementById('statsFileName').textContent = fileName;
  document.getElementById('statsWordCount').textContent = stats.total_words.toLocaleString();
  document.getElementById('statsTotalRepl').textContent = stats.total_replacements.toLocaleString();
  
  const coverLabels = {
    remove_cover: 'Only Introduction & Below (No Cover/TOC)',
    keep_untouched: 'Kept Cover Sheet (Body Only)',
    entire_doc: 'Entire Document Transformed'
  };
  document.getElementById('statsCoverMode').textContent = coverLabels[stats.cover_mode] || 'Kept';

  // Render per-character badges in footer
  const badgeContainer = document.getElementById('charCountsBadges');
  badgeContainer.innerHTML = '';
  for (const [char, count] of Object.entries(stats.counts)) {
    if (count > 0) {
      const span = document.createElement('span');
      span.className = 'px-1.5 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/40 text-[11px] font-mono text-amber-300';
      span.textContent = `${char}: ${count.toLocaleString()}`;
      badgeContainer.appendChild(span);
    }
  }

  // Update rule counts in left table
  renderRulesTable(stats.counts);

  // Render active tab views
  renderDiffView(previewData);
  renderPdfView(previewData);
  renderRawView(previewData);
}

function renderDiffView(previewData) {
  const container = document.getElementById('diffViewContainer');
  if (!previewData || !previewData.paragraphs || previewData.paragraphs.length === 0) {
    container.innerHTML = '<div class="text-slate-500 italic text-center py-10">No content available.</div>';
    return;
  }

  const replacedChars = new Set(Object.keys(previewData.active_replaces || {}));
  let html = '';

  previewData.paragraphs.forEach(pText => {
    let pContent = '';
    for (let i = 0; i < pText.length; i++) {
      const ch = pText[i];
      if (state.highlightEnabled && replacedChars.has(ch)) {
        pContent += `<span class="hl-char">${ch}</span>`;
      } else {
        pContent += escapeHtml(ch);
      }
    }
    
    // Distinguish headings
    if (/^(Introduction|Task\s*\d+|Conclusion|Bibliography)\s*:?/i.test(pText)) {
      html += `<div class="font-bold text-sm text-indigo-300 border-b border-slate-800 pb-1 mt-3 mb-1.5">${pContent}</div>`;
    } else {
      html += `<p class="leading-relaxed mb-2.5">${pContent}</p>`;
    }
  });

  container.innerHTML = html;
}

function renderPdfView(previewData) {
  const container = document.getElementById('pdfViewContainer');
  if (!previewData || !previewData.page_images || previewData.page_images.length === 0) {
    container.innerHTML = '<div class="text-slate-500 italic text-center py-10">Generating real layout PDF preview...</div>';
    return;
  }

  let html = `<div class="text-center text-xs text-slate-400 mb-2">Showing authentic vector PDF render with 100% original tables, logos, fonts &amp; margins intact (${previewData.num_pages} total pages):</div>`;
  previewData.page_images.forEach((imgData, idx) => {
    html += `
      <div class="flex flex-col items-center bg-[#070a12] p-2 rounded-xl shadow-lg border border-slate-800 max-w-[700px] w-full">
        <div class="text-[11px] text-slate-400 font-medium mb-1.5 flex items-center justify-between w-full px-2">
          <span>Page ${idx + 1} of ${previewData.num_pages}</span>
          <span class="text-emerald-400 font-semibold">100% Original Word Layout</span>
        </div>
        <img src="${imgData}" class="w-full h-auto rounded shadow-md border border-slate-700 bg-white" alt="PDF Page ${idx + 1}" />
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderRawView(previewData) {
  const container = document.getElementById('rawViewContainer');
  if (!previewData || !previewData.paragraphs) {
    container.textContent = '';
    return;
  }
  container.textContent = previewData.paragraphs.join('\n\n');
}

function switchTab(tabName) {
  state.activeTab = tabName;
  const diffBtn = document.getElementById('tabDiffView');
  const pdfBtn = document.getElementById('tabPdfView');
  const rawBtn = document.getElementById('tabRawView');

  const diffCont = document.getElementById('diffViewContainer');
  const pdfCont = document.getElementById('pdfViewContainer');
  const rawCont = document.getElementById('rawViewContainer');

  [diffBtn, pdfBtn, rawBtn].forEach(b => {
    b.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition flex items-center gap-1.5';
  });

  [diffCont, pdfCont, rawCont].forEach(c => c.classList.add('hidden'));

  if (tabName === 'diff') {
    diffBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition flex items-center gap-1.5';
    diffCont.classList.remove('hidden');
  } else if (tabName === 'pdf') {
    pdfBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition flex items-center gap-1.5';
    pdfCont.classList.remove('hidden');
  } else if (tabName === 'raw') {
    rawBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white transition flex items-center gap-1.5';
    rawCont.classList.remove('hidden');
  }
}

// --- Downloads ---
async function downloadCurrentPdf() {
  if (!state.activeFileId) {
    showToast('No active file loaded', 'error');
    return;
  }

  showToast('Generating pixel-perfect Selectable PDF...');
  const payload = {
    file_id: state.activeFileId,
    rules: state.rules,
    cover_mode: document.getElementById('coverScopeSelect').value,
    skip_urls: document.getElementById('skipUrlsToggle').checked,
    skip_headings: document.getElementById('skipHeadingsToggle').checked,
    remove_page_numbers: document.getElementById('removePageNumbersToggle').checked,
    custom_marker: document.getElementById('customMarkerInput').value.trim() || null
  };

  try {
    const res = await fetch('/api/process-single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success' && data.pdf_available) {
      incrementWeeklyCounter(1);
      window.location.href = `/api/download-file/${state.activeFileId}/pdf`;
      showToast('✓ PDF download started!');
    } else {
      showToast('PDF creation failed', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('Download error: ' + err.message, 'error');
  }
}

async function downloadCurrentDocx() {
  if (!state.activeFileId) {
    showToast('No active file loaded', 'error');
    return;
  }

  const payload = {
    file_id: state.activeFileId,
    rules: state.rules,
    cover_mode: document.getElementById('coverScopeSelect').value,
    skip_urls: document.getElementById('skipUrlsToggle').checked,
    skip_headings: document.getElementById('skipHeadingsToggle').checked,
    remove_page_numbers: document.getElementById('removePageNumbersToggle').checked,
    custom_marker: document.getElementById('customMarkerInput').value.trim() || null
  };

  try {
    const res = await fetch('/api/process-single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      window.location.href = `/api/download-file/${state.activeFileId}/docx`;
      showToast('✓ .DOCX download started!');
    }
  } catch (err) {
    console.error(err);
    showToast('Download error: ' + err.message, 'error');
  }
}

// --- Batch Process All to ZIP ---
async function batchProcessAll() {
  if (state.files.length === 0) {
    showToast('No files in queue to process', 'error');
    return;
  }

  const progressCard = document.getElementById('batchProgressCard');
  const progressBar = document.getElementById('batchProgressBar');
  const progressStatus = document.getElementById('batchProgressStatus');
  const progressPercent = document.getElementById('batchProgressPercent');

  progressCard.classList.remove('hidden');
  progressBar.style.width = '20%';
  progressPercent.textContent = '20%';
  progressStatus.textContent = `Batch processing ${state.files.length} assignment(s)...`;

  const payload = {
    file_ids: state.files.map(f => f.file_id),
    rules: state.rules,
    cover_mode: document.getElementById('coverScopeSelect').value,
    skip_urls: document.getElementById('skipUrlsToggle').checked,
    skip_headings: document.getElementById('skipHeadingsToggle').checked,
    remove_page_numbers: document.getElementById('removePageNumbersToggle').checked,
    custom_marker: document.getElementById('customMarkerInput').value.trim() || null,
    include_docx: true
  };

  try {
    progressBar.style.width = '60%';
    progressPercent.textContent = '60%';

    const res = await fetch('/api/batch-process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.status === 'success') {
      progressBar.style.width = '100%';
      progressPercent.textContent = '100%';
      progressStatus.textContent = `✓ Successfully converted ${data.processed_count} assignment(s)!`;

      incrementWeeklyCounter(data.processed_count);
      window.location.href = data.download_url;
      showToast(`✓ Batch ZIP ready! Downloaded ${data.processed_count} files`);

      setTimeout(() => {
        progressCard.classList.add('hidden');
      }, 5000);
    }
  } catch (err) {
    console.error(err);
    progressCard.classList.add('hidden');
    showToast('Batch error: ' + err.message, 'error');
  }
}

function copyCleanText() {
  if (!state.currentPreviewData || !state.currentPreviewData.paragraphs) {
    showToast('No text available to copy', 'error');
    return;
  }
  const text = state.currentPreviewData.paragraphs.join('\n\n');
  navigator.clipboard.writeText(text).then(() => {
    showToast('✓ Assignment text copied to clipboard!');
  }).catch(err => {
    showToast('Clipboard copy failed: ' + err.message, 'error');
  });
}

// --- Weekly Counter Helpers ---
function incrementWeeklyCounter(amount = 1) {
  state.weeklyCount += amount;
  localStorage.setItem('weekly_unicode_count', state.weeklyCount.toString());
  updateWeeklyBadge();
}

function updateWeeklyBadge() {
  const lbl = document.getElementById('weeklyCounterLabel');
  const bar = document.getElementById('weeklyProgressBar');
  lbl.textContent = `${state.weeklyCount} / 100 PDFs`;
  const pct = Math.min(100, (state.weeklyCount / 100) * 100);
  bar.style.width = `${pct}%`;
}

// --- Utility Helpers ---
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toastMsg');
  const toastInner = document.getElementById('toastInner');

  toastMsg.textContent = msg;
  if (type === 'error') {
    toastInner.className = 'bg-rose-600 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg border border-rose-400/40 flex items-center gap-2';
  } else {
    toastInner.className = 'bg-indigo-600 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-lg border border-indigo-400/40 flex items-center gap-2';
  }

  toast.classList.remove('opacity-0', 'translate-y-3');
  toast.classList.add('opacity-100', 'translate-y-0');

  setTimeout(() => {
    toast.classList.remove('opacity-100', 'translate-y-0');
    toast.classList.add('opacity-0', 'translate-y-3');
  }, 3500);
}
