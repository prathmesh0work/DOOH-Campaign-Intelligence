window.addEventListener('DOMContentLoaded', function() {

  var loadFromDbBtn = document.getElementById('loadFromDbBtn');
  var dropZone      = document.getElementById('dropZone');
  var fileInput     = document.getElementById('fileInput');
  var fileInfo      = document.getElementById('fileInfo');
  var fileNameEl    = document.getElementById('fileName');
  var fileSizeEl    = document.getElementById('fileSize');
  var removeBtn     = document.getElementById('removeBtn');
  var progressFill  = document.getElementById('progressFill');
  var progressLabel = document.getElementById('progressLabel');
  var msgEl         = document.getElementById('msg');
  var resetBtn      = document.getElementById('resetBtn');

  var savedResult = null;
  try {
    var saved = localStorage.getItem('doohDashboardData');
    if (saved) savedResult = JSON.parse(saved);
  } catch (e) {
    localStorage.removeItem('doohDashboardData'); 
  }

  if (savedResult) {
    document.getElementById('uploadScreen').classList.add('hidden');
    document.getElementById('dashboardScreen').classList.remove('hidden');
    renderDashboard(savedResult.data, savedResult.log, savedResult.cols, savedResult);
  }

  loadFromDbBtn.addEventListener('click', function() {
  showMsg('info', 'Loading data from database...');

  fetch('/api/load_from_db')
    .then(function(response) {
      return response.json();
    })
    .then(function(result) {
      if (!result.success) {
        showMsg('error', result.error || '✗ Could not load from database');
        return;
      }

      result.uploadedFileName = 'Loaded from Database';

      try {
        localStorage.setItem('doohDashboardData', JSON.stringify(result));
      } catch (e) {
        console.warn('Could not save dashboard state:', e);
      }

      document.getElementById('uploadScreen').classList.add('hidden');
      document.getElementById('dashboardScreen').classList.remove('hidden');

      renderDashboard(result.data, result.log, result.cols, result);
    })
    .catch(function(err) {
      showMsg('error', '✗ Backend error: ' + err.message);
    });
  });

  dropZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', function() {
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', function(e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    var file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  fileInput.addEventListener('change', function() {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  removeBtn.addEventListener('click', function() {
    resetUpload();
  });

  resetBtn.addEventListener('click', function() {
    document.getElementById('dashboardScreen').classList.add('hidden');
    document.getElementById('uploadScreen').classList.remove('hidden');
    document.documentElement.classList.remove('has-saved-dashboard');
    localStorage.removeItem('doohDashboardData');
    var fileNameLabel = document.getElementById('uploadedFileName');
    if (fileNameLabel) fileNameLabel.textContent = '';
    resetUpload();
  });

  function handleFile(file) {
    var ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx' && ext !== 'xls') {
      showMsg('error', '✗ Wrong format. Please upload a CSV, XLS, or XLSX file.');
      return;
    }

    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatBytes(file.size);
    fileInfo.classList.add('visible');
    msgEl.className = 'msg';

    setProgress(20, 'Reading file...');

    var formData = new FormData();
    formData.append('file', file);

    setProgress(50, 'Sending to Python backend...');

    fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
    .then(function(response) {
      return response.json();
    })
    .then(function(result) {
      if (!result.success) {
        showMsg('error', result.error || '✗ Backend error');
        setProgress(0, '');
        return;
      }

      setProgress(70, 'Processing data...');

      result.uploadedFileName = file.name;

      try {
        localStorage.setItem('doohDashboardData', JSON.stringify(result));
      } catch (e) {
        console.warn('Could not save dashboard state (dataset may be too large for localStorage):', e);
      }

      setTimeout(function() {
        try {
          setProgress(90, 'Building dashboard...');

          setTimeout(function() {
            try {
              setProgress(100, 'Done!');

              document.getElementById('uploadScreen').classList.add('hidden');
              document.getElementById('dashboardScreen').classList.remove('hidden');

              renderDashboard(result.data, result.log, result.cols, result);

            } catch(e) {
              showMsg('error', '✗ Dashboard error: ' + e.message);
              setProgress(0, '');
              document.getElementById('uploadScreen').classList.remove('hidden');
              document.getElementById('dashboardScreen').classList.add('hidden');
            }
          }, 400);

        } catch(e) {
          showMsg('error', '✗ Error: ' + e.message);
          setProgress(0, '');
        }
      }, 300);

    })
    .catch(function(err) {
      showMsg('error', '✗ Backend error: ' + err.message);
      setProgress(0, '');
    });
  }

  function resetUpload() {
    fileInput.value = '';
    fileInfo.classList.remove('visible');
    msgEl.className = 'msg';
    progressFill.style.width = '0%';
    progressLabel.textContent = '';
  }

  function setProgress(percent, label) {
    progressFill.style.width = percent + '%';
    progressLabel.textContent = label;
  }

  function showMsg(type, text) {
    msgEl.className = 'msg ' + type;
    msgEl.textContent = text;
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }

});
