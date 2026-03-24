document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const filePreview = document.getElementById('filePreview');
  const fileName = document.getElementById('selectedFileName');
  const fileSize = document.getElementById('selectedFileSize');
  const fileRemove = document.getElementById('fileRemove');
  const uploadBtn = document.getElementById('uploadBtn');
  const uploadForm = document.getElementById('uploadForm');

  if (!dropZone || !fileInput) return;

  // Click to browse
  dropZone.addEventListener('click', () => fileInput.click());

  // Drag events
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
  });

  fileRemove?.addEventListener('click', (e) => {
    e.stopPropagation();
    clearFile();
  });

  uploadForm?.addEventListener('submit', () => {
    const btnText = uploadBtn.querySelector('.btn-text');
    const btnLoading = uploadBtn.querySelector('.btn-loading');
    if (btnText) btnText.style.display = 'none';
    if (btnLoading) btnLoading.style.display = 'flex';
    uploadBtn.disabled = true;
  });

  function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls'].includes(ext)) {
      alert('Only .xlsx and .xls files are supported.');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      alert('File exceeds 50 MB limit.');
      return;
    }

    // Transfer to real input
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;

    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = formatBytes(file.size);

    dropZone.style.display = 'none';
    if (filePreview) filePreview.style.display = 'flex';
    if (uploadBtn) uploadBtn.disabled = false;
  }

  function clearFile() {
    fileInput.value = '';
    dropZone.style.display = 'flex';
    if (filePreview) filePreview.style.display = 'none';
    if (uploadBtn) uploadBtn.disabled = true;
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
});
