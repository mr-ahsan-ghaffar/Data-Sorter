const state = {
  mode: "single",
  fileRef: null,
  filePath: null,
  filePaths: [],
  filename: null,
  columns: [],
  selectedOrder: [],
  currentJobId: null,
  pollTimer: null,
};

const modeSingleBtn = document.getElementById("modeSingleBtn");
const modeMultiBtn = document.getElementById("modeMultiBtn");
const singleFilePanel = document.getElementById("singleFilePanel");
const multiFilePanel = document.getElementById("multiFilePanel");
const multiFilePaths = document.getElementById("multiFilePaths");
const browseMultiBtn = document.getElementById("browseMultiBtn");
const loadMultiBtn = document.getElementById("loadMultiBtn");
const clearMultiBtn = document.getElementById("clearMultiBtn");
const multiFileList = document.getElementById("multiFileList");
const removeDuplicatesWrap = document.getElementById("removeDuplicatesWrap");
const multiDedupNote = document.getElementById("multiDedupNote");

const inputFilePath = document.getElementById("inputFilePath");
const loadFileBtn = document.getElementById("loadFileBtn");
const browseInputBtn = document.getElementById("browseInputBtn");
const browseOutputBtn = document.getElementById("browseOutputBtn");
const fileMeta = document.getElementById("fileMeta");
const loadedFileName = document.getElementById("loadedFileName");
const loadedFilePath = document.getElementById("loadedFilePath");
const loadedFileType = document.getElementById("loadedFileType");
const loadedFileSize = document.getElementById("loadedFileSize");
const loadedColumnCount = document.getElementById("loadedColumnCount");
const columnsPanel = document.getElementById("columnsPanel");
const optionsPanel = document.getElementById("optionsPanel");
const progressPanel = document.getElementById("progressPanel");
const resultPanel = document.getElementById("resultPanel");
const columnGrid = document.getElementById("columnGrid");
const orderSection = document.getElementById("orderSection");
const columnOrderList = document.getElementById("columnOrderList");
const orderEmpty = document.getElementById("orderEmpty");
const presetSelect = document.getElementById("presetSelect");
const selectAllBtn = document.getElementById("selectAllBtn");
const clearAllBtn = document.getElementById("clearAllBtn");
const outputDir = document.getElementById("outputDir");
const skipEmpty = document.getElementById("skipEmpty");
const removeDuplicates = document.getElementById("removeDuplicates");
const outputName = document.getElementById("outputName");
const processBtn = document.getElementById("processBtn");
const progressMessage = document.getElementById("progressMessage");
const progressFill = document.getElementById("progressFill");
const progressStatus = document.getElementById("progressStatus");
const progressInputRows = document.getElementById("progressInputRows");
const progressOutputRows = document.getElementById("progressOutputRows");
const progressDuplicates = document.getElementById("progressDuplicates");
const resultSummary = document.getElementById("resultSummary");
const savedPathBox = document.getElementById("savedPathBox");
const savedPath = document.getElementById("savedPath");
const downloadBtn = document.getElementById("downloadBtn");
const resetBtn = document.getElementById("resetBtn");
const toast = document.getElementById("toast");
const statusBanner = document.getElementById("statusBanner");

function showStatus(message, isError = true) {
  if (!statusBanner) return;
  statusBanner.textContent = message;
  statusBanner.classList.toggle("ok", !isError);
  statusBanner.classList.remove("hidden");
}

function hideStatus() {
  if (statusBanner) statusBanner.classList.add("hidden");
}

let dragSourceName = null;

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3500);
}

function setLoading(button, loading, label = "Processing...") {
  if (!button) return;
  button.disabled = loading;
  button.dataset.originalText ||= button.textContent;
  button.textContent = loading ? label : button.dataset.originalText;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  let data = {};
  try {
    data = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? "Invalid server response."
        : `Server error (${response.status}). Stop and restart start_server.bat, then try again.`
    );
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status}).`);
  }
  return data;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setInputMode(mode) {
  state.mode = mode;
  modeSingleBtn?.classList.toggle("active", mode === "single");
  modeMultiBtn?.classList.toggle("active", mode === "multi");
  singleFilePanel?.classList.toggle("hidden", mode !== "single");
  multiFilePanel?.classList.toggle("hidden", mode !== "multi");
  removeDuplicatesWrap?.classList.toggle("hidden", mode === "multi");
  multiDedupNote?.classList.toggle("hidden", mode !== "multi");
  hideStatus();
}

function parsePathLines(text) {
  return [...new Set(text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean))];
}

function renderMultiFileList(paths) {
  if (!multiFileList) return;
  multiFileList.innerHTML = "";
  if (!paths.length) {
    multiFileList.classList.add("hidden");
    return;
  }
  multiFileList.classList.remove("hidden");
  paths.forEach((path) => {
    const item = document.createElement("li");
    item.textContent = path;
    multiFileList.appendChild(item);
  });
}

function handleLoadedMultiFiles(data) {
  state.fileRef = null;
  state.filePath = null;
  state.filePaths = data.file_paths || [];
  state.filename = `${data.file_count} files`;
  state.columns = data.columns;
  state.selectedOrder = [];

  loadedFileName.textContent = `${data.file_count} files selected`;
  loadedFilePath.textContent = state.filePaths.join("\n");
  loadedFileSize.textContent = data.total_size_label || "Unknown";
  loadedColumnCount.textContent = String(data.column_count);
  outputDir.value = data.default_output_dir || outputDir.value;
  outputName.value = "merged_deduplicated.csv";

  multiFilePaths.value = state.filePaths.join("\n");
  renderMultiFileList(state.filePaths);
  renderColumns(data.columns);
  showWorkflowPanels();
  showStatus(`Loaded ${data.file_count} files for cross-file duplicate removal.`, false);
  showToast(`Loaded ${data.file_count} files.`);
}

function getColumnMeta(name) {
  return state.columns.find((column) => column.name === name);
}

async function loadMultiFilesFromTextarea() {
  const paths = parsePathLines(multiFilePaths.value);
  if (paths.length < 2) {
    showToast("Add at least 2 input file paths.", true);
    return;
  }

  setLoading(loadMultiBtn, true, "Loading...");
  try {
    const data = await fetchJson("/api/open-paths", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_paths: paths }),
    });
    handleLoadedMultiFiles(data);
  } catch (error) {
    showStatus(error.message);
    showToast(error.message, true);
  } finally {
    setLoading(loadMultiBtn, false);
  }
}

async function browseForMultipleFiles() {
  if (!browseMultiBtn) return;
  if (state.mode !== "multi") {
    setInputMode("multi");
  }
  hideStatus();
  showToast("A file picker window should open on your desktop (check behind this browser).");
  setLoading(browseMultiBtn, true, "Choose...");
  try {
    const data = await fetchJson("/api/browse-files", { method: "POST" });
    if (data.cancelled || !data.paths?.length) {
      showToast("File selection cancelled.");
      return;
    }
    const existing = parsePathLines(multiFilePaths.value);
    const merged = [...new Set([...existing, ...data.paths])];
    multiFilePaths.value = merged.join("\n");
    showStatus(`${merged.length} file path(s) ready. Click Load files to continue.`, false);
    if (merged.length >= 2) {
      await loadMultiFilesFromTextarea();
    } else {
      showToast("Select at least 2 files total, then click Load files.");
    }
  } catch (error) {
    showStatus(error.message);
    showToast(error.message, true);
  } finally {
    setLoading(browseMultiBtn, false);
  }
}

function syncSelectedOrderWithCheckboxes() {
  const checked = new Set(getCheckedColumnNames());
  state.selectedOrder = state.selectedOrder.filter((name) => checked.has(name));

  getCheckedColumnNames().forEach((name) => {
    if (!state.selectedOrder.includes(name)) {
      state.selectedOrder.push(name);
    }
  });
}

function getCheckedColumnNames() {
  return [...columnGrid.querySelectorAll('input[type="checkbox"]:checked')].map(
    (input) => input.value
  );
}

function getSelectedColumns() {
  syncSelectedOrderWithCheckboxes();
  return [...state.selectedOrder];
}

function renderColumns(columns, selectedNames = []) {
  columnGrid.innerHTML = "";
  const selected = new Set(selectedNames);

  columns.forEach((column) => {
    const card = document.createElement("label");
    card.className = `column-card${column.misaligned ? " misaligned" : ""}`;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = column.name;
    checkbox.checked = selected.has(column.name);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        if (!state.selectedOrder.includes(column.name)) {
          state.selectedOrder.push(column.name);
        }
      } else {
        state.selectedOrder = state.selectedOrder.filter((name) => name !== column.name);
      }
      renderOrderList();
    });

    const content = document.createElement("div");
    content.innerHTML = `
      <span class="column-index">#${column.index}</span>
      <span class="column-name">${escapeHtml(column.name)}</span>
      ${
        column.misaligned
          ? `<span class="column-warning">Header note: ${escapeHtml(column.misaligned_note)}</span>`
          : ""
      }
    `;

    card.appendChild(checkbox);
    card.appendChild(content);
    columnGrid.appendChild(card);
  });

  renderOrderList();
}

function moveColumn(name, action) {
  const index = state.selectedOrder.indexOf(name);
  if (index === -1) return;

  const nextOrder = [...state.selectedOrder];
  nextOrder.splice(index, 1);

  if (action === "start") {
    nextOrder.unshift(name);
  } else if (action === "end") {
    nextOrder.push(name);
  } else if (action === "up" && index > 0) {
    nextOrder.splice(index - 1, 0, name);
  } else if (action === "down" && index < state.selectedOrder.length - 1) {
    nextOrder.splice(index + 1, 0, name);
  } else {
    return;
  }

  state.selectedOrder = nextOrder;
  renderOrderList();
}

function renderOrderList() {
  syncSelectedOrderWithCheckboxes();

  columnOrderList.innerHTML = "";
  orderSection.classList.remove("hidden");

  if (!state.selectedOrder.length) {
    orderEmpty.classList.remove("hidden");
    return;
  }

  orderEmpty.classList.add("hidden");

  state.selectedOrder.forEach((name, index) => {
    const meta = getColumnMeta(name);
    const item = document.createElement("div");
    item.className = "order-item";
    item.draggable = true;
    item.dataset.columnName = name;

    item.innerHTML = `
      <div class="order-position">${index + 1}</div>
      <div class="order-label">
        <strong>${escapeHtml(name)}</strong>
        <span>${meta ? `Original column #${meta.index}` : "Selected column"} · drag to reorder</span>
      </div>
      <div class="order-actions">
        <span class="drag-handle" title="Drag to reorder">⋮⋮</span>
        <button type="button" class="icon-btn" data-action="start" ${index === 0 ? "disabled" : ""}>Start</button>
        <button type="button" class="icon-btn" data-action="up" ${index === 0 ? "disabled" : ""}>Up</button>
        <button type="button" class="icon-btn" data-action="down" ${index === state.selectedOrder.length - 1 ? "disabled" : ""}>Down</button>
        <button type="button" class="icon-btn" data-action="end" ${index === state.selectedOrder.length - 1 ? "disabled" : ""}>End</button>
      </div>
    `;

    item.addEventListener("dragstart", (event) => {
      dragSourceName = name;
      item.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", name);
    });

    item.addEventListener("dragend", () => {
      dragSourceName = null;
      item.classList.remove("dragging");
      columnOrderList.querySelectorAll(".order-item").forEach((node) => {
        node.classList.remove("drag-over");
      });
    });

    item.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      item.classList.add("drag-over");
    });

    item.addEventListener("dragleave", () => {
      item.classList.remove("drag-over");
    });

    item.addEventListener("drop", (event) => {
      event.preventDefault();
      item.classList.remove("drag-over");
      const sourceName = dragSourceName || event.dataTransfer.getData("text/plain");
      const targetName = name;
      if (!sourceName || sourceName === targetName) return;

      const sourceIndex = state.selectedOrder.indexOf(sourceName);
      const targetIndex = state.selectedOrder.indexOf(targetName);
      if (sourceIndex === -1 || targetIndex === -1) return;

      const nextOrder = [...state.selectedOrder];
      nextOrder.splice(sourceIndex, 1);
      nextOrder.splice(targetIndex, 0, sourceName);
      state.selectedOrder = nextOrder;
      renderOrderList();
    });

    item.querySelectorAll(".icon-btn").forEach((button) => {
      button.addEventListener("click", () => {
        moveColumn(name, button.dataset.action);
      });
    });

    columnOrderList.appendChild(item);
  });
}

function setAllColumns(checked) {
  columnGrid.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.checked = checked;
  });

  if (checked) {
    state.selectedOrder = state.columns.map((column) => column.name);
  } else {
    state.selectedOrder = [];
  }

  renderOrderList();
}

function applyPresetColumnSelection(columnNames) {
  const available = new Set(state.columns.map((column) => column.name));
  state.selectedOrder = columnNames.filter((name) => available.has(name));

  columnGrid.querySelectorAll('input[type="checkbox"]').forEach((input) => {
    input.checked = state.selectedOrder.includes(input.value);
  });

  renderOrderList();
}

function showWorkflowPanels() {
  fileMeta.classList.remove("hidden");
  columnsPanel.classList.remove("hidden");
  optionsPanel.classList.remove("hidden");
  progressPanel.classList.add("hidden");
  resultPanel.classList.add("hidden");
}

function handleLoadedFile(data) {
  state.fileRef = data.file_ref;
  state.filePath = data.file_path;
  state.filename = data.filename;
  state.columns = data.columns;
  state.selectedOrder = [];

  inputFilePath.value = data.file_path;
  loadedFileName.textContent = data.filename;
  loadedFilePath.textContent = data.file_path;
  loadedFileType.textContent = data.file_type || "Unknown";
  loadedFileSize.textContent = data.file_size_label || "Unknown";
  loadedColumnCount.textContent = String(data.column_count);
  outputDir.value = data.default_output_dir || "";
  outputName.value = `${data.filename.replace(/\.[^.]+$/, "")}_sorted.csv`;

  renderColumns(data.columns);
  showWorkflowPanels();
  showToast(`Loaded ${data.filename}`);
}

function updateProgressView(job) {
  progressPanel.classList.remove("hidden");
  resultPanel.classList.add("hidden");
  progressMessage.textContent = job.message || "Processing...";
  progressFill.style.width = `${job.progress_percent || 0}%`;
  progressStatus.textContent = job.status || "running";
  progressInputRows.textContent = Number(job.input_rows || 0).toLocaleString();
  progressOutputRows.textContent = Number(job.output_rows || 0).toLocaleString();
  progressDuplicates.textContent = Number(job.duplicates_removed || 0).toLocaleString();
}

function showCompletedResult(job) {
  const filesProcessed = job.files_processed || 1;
  resultSummary.innerHTML = `
    <div class="stat-card"><span class="label">Files processed</span><strong>${Number(filesProcessed).toLocaleString()}</strong></div>
    <div class="stat-card"><span class="label">Input rows</span><strong>${Number(job.input_rows || 0).toLocaleString()}</strong></div>
    <div class="stat-card"><span class="label">Output rows</span><strong>${Number(job.output_rows || 0).toLocaleString()}</strong></div>
    <div class="stat-card"><span class="label">Duplicates removed</span><strong>${Number(job.duplicates_removed || 0).toLocaleString()}</strong></div>
    <div class="stat-card"><span class="label">Columns kept</span><strong>${(job.kept_columns || []).length}</strong></div>
  `;

  savedPath.textContent = job.output_path || "";
  savedPathBox.classList.remove("hidden");

  if (state.currentJobId) {
    downloadBtn.href = `/api/jobs/${encodeURIComponent(state.currentJobId)}/download`;
    downloadBtn.classList.remove("hidden");
  }

  progressPanel.classList.add("hidden");
  resultPanel.classList.remove("hidden");
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function pollJob(jobId) {
  try {
    const job = await fetchJson(`/api/jobs/${jobId}`);
    updateProgressView(job);

    if (job.status === "completed") {
      stopPolling();
      setLoading(processBtn, false);
      showCompletedResult(job);
      showToast("File saved to disk.");
    } else if (job.status === "failed") {
      stopPolling();
      setLoading(processBtn, false);
      progressPanel.classList.add("hidden");
      showToast(job.error || "Processing failed.", true);
    }
  } catch (error) {
    stopPolling();
    setLoading(processBtn, false);
    showToast(error.message, true);
  }
}

async function browseForInputFile() {
  if (!browseInputBtn) {
    showStatus("Choose file button not found. Refresh the page with Ctrl+F5.");
    return;
  }
  hideStatus();
  showToast("A file picker window should open on your desktop (check behind this browser).");
  setLoading(browseInputBtn, true, "Choose...");
  try {
    const data = await fetchJson("/api/browse-file", { method: "POST" });
    if (data.cancelled) {
      showToast("File selection cancelled.");
      return;
    }
    inputFilePath.value = data.path;
    showStatus(`Selected: ${data.path}`, false);
    await loadFileFromPath();
  } catch (error) {
    showStatus(error.message);
    showToast(error.message, true);
  } finally {
    setLoading(browseInputBtn, false);
  }
}

async function browseForOutputDir() {
  if (!browseOutputBtn) {
    showStatus("Choose folder button not found. Refresh the page with Ctrl+F5.");
    return;
  }
  hideStatus();
  showToast("A folder picker window should open on your desktop (check behind this browser).");
  setLoading(browseOutputBtn, true, "Choose...");
  try {
    const data = await fetchJson("/api/browse-directory", { method: "POST" });
    if (data.cancelled) {
      showToast("Folder selection cancelled.");
      return;
    }
    outputDir.value = data.path;
    showStatus(`Output folder: ${data.path}`, false);
    showToast("Output folder selected.");
  } catch (error) {
    showStatus(error.message);
    showToast(error.message, true);
  } finally {
    setLoading(browseOutputBtn, false);
  }
}

async function loadFileFromPath() {
  const filePath = inputFilePath.value.trim();
  if (!filePath) {
    showToast("Enter the full path to an input file (CSV, TXT, or Excel).", true);
    return;
  }

  setLoading(loadFileBtn, true, "Loading...");
  try {
    const data = await fetchJson("/api/open-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: filePath }),
    });
    handleLoadedFile(data);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setLoading(loadFileBtn, false);
  }
}

async function loadPresets() {
  try {
    const data = await fetchJson("/api/presets");
    data.presets.forEach((preset) => {
      const option = document.createElement("option");
      option.value = JSON.stringify(preset.keep_columns);
      option.textContent = preset.name;
      presetSelect.appendChild(option);
    });
  } catch (error) {
    showToast(error.message, true);
  }
}

async function processCurrentFile() {
  const keepColumns = getSelectedColumns();
  const outputDirectory = outputDir.value.trim();
  const isMulti = state.mode === "multi";

  if (isMulti) {
    if (state.filePaths.length < 2) {
      showToast("Load at least 2 input files first.", true);
      return;
    }
  } else if (!state.fileRef) {
    showToast("Load an input file first.", true);
    return;
  }

  if (!keepColumns.length) {
    showToast("Select at least one column.", true);
    return;
  }
  if (!outputDirectory) {
    showToast("Enter an output directory.", true);
    return;
  }

  stopPolling();
  setLoading(processBtn, true, "Starting...");
  progressPanel.classList.remove("hidden");
  resultPanel.classList.add("hidden");
  savedPathBox.classList.add("hidden");
  downloadBtn.classList.add("hidden");
  updateProgressView({
    status: "queued",
    message: isMulti ? "Starting multi-file job..." : "Starting background job...",
    progress_percent: 0,
    input_rows: 0,
    output_rows: 0,
    duplicates_removed: 0,
  });

  const payload = {
    keep_columns: keepColumns,
    skip_empty: skipEmpty.checked,
    remove_duplicates: isMulti ? true : removeDuplicates.checked,
    output_dir: outputDirectory,
    output_name: outputName.value.trim() || "sorted_output.csv",
    multi_mode: isMulti,
  };

  if (isMulti) {
    payload.input_paths = state.filePaths;
  } else {
    payload.file_ref = state.fileRef;
  }

  try {
    const data = await fetchJson("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    state.currentJobId = data.job_id;
    state.pollTimer = window.setInterval(() => pollJob(data.job_id), 1500);
    await pollJob(data.job_id);
  } catch (error) {
    setLoading(processBtn, false);
    progressPanel.classList.add("hidden");
    showToast(error.message, true);
  }
}

function resetWorkflow() {
  stopPolling();
  state.fileRef = null;
  state.filePath = null;
  state.filePaths = [];
  state.filename = null;
  state.columns = [];
  state.selectedOrder = [];
  state.currentJobId = null;
  if (multiFilePaths) multiFilePaths.value = "";
  renderMultiFileList([]);
  columnGrid.innerHTML = "";
  columnOrderList.innerHTML = "";
  resultSummary.innerHTML = "";
  downloadBtn.classList.add("hidden");
  downloadBtn.href = "#";
  savedPathBox.classList.add("hidden");
  savedPath.textContent = "";
  fileMeta.classList.add("hidden");
  columnsPanel.classList.add("hidden");
  orderSection.classList.add("hidden");
  optionsPanel.classList.add("hidden");
  progressPanel.classList.add("hidden");
  resultPanel.classList.add("hidden");
  orderEmpty.classList.add("hidden");
  removeDuplicates.checked = false;
  skipEmpty.checked = true;
  presetSelect.value = "";
  setLoading(processBtn, false);
  setLoading(loadFileBtn, false);
  setLoading(loadMultiBtn, false);
  hideStatus();
}

modeSingleBtn?.addEventListener("click", () => setInputMode("single"));
modeMultiBtn?.addEventListener("click", () => setInputMode("multi"));
loadMultiBtn?.addEventListener("click", loadMultiFilesFromTextarea);
browseMultiBtn?.addEventListener("click", browseForMultipleFiles);
clearMultiBtn?.addEventListener("click", () => {
  multiFilePaths.value = "";
  state.filePaths = [];
  renderMultiFileList([]);
  hideStatus();
});
setInputMode("single");

loadFileBtn.addEventListener("click", loadFileFromPath);
if (browseInputBtn) browseInputBtn.addEventListener("click", browseForInputFile);
if (browseOutputBtn) browseOutputBtn.addEventListener("click", browseForOutputDir);
inputFilePath.addEventListener("keydown", (event) => {
  if (event.key === "Enter") loadFileFromPath();
});

selectAllBtn.addEventListener("click", () => setAllColumns(true));
clearAllBtn.addEventListener("click", () => setAllColumns(false));

presetSelect.addEventListener("change", () => {
  if (!presetSelect.value) return;
  const keepColumns = JSON.parse(presetSelect.value);
  applyPresetColumnSelection(keepColumns);
  showToast("Preset applied with preset column order.");
});

processBtn.addEventListener("click", processCurrentFile);
resetBtn.addEventListener("click", resetWorkflow);

loadPresets();
checkServerHealth();

async function checkServerHealth() {
  try {
    await fetchJson("/api/health");
    hideStatus();
  } catch {
    showStatus("Server is outdated or not running. Close any old server window, run start_server.bat, then press Ctrl+F5.");
    showToast("Restart start_server.bat", true);
  }
}
