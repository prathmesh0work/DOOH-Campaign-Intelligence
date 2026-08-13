var allData = [];
var chartInstances = {};
var minDate = '';
var maxDate = '';

var CURRENCIES = {
  INR: { symbol: '₹', rate: 1 },
  USD: { symbol: '$', rate: null },
  EUR: { symbol: '€', rate: null },
  GBP: { symbol: '£', rate: null },
  AED: { symbol: 'AED ', rate: null }
};
var currentCurrency = 'INR';

function fetchFxRates(callback) {
  fetch('https://api.frankfurter.app/latest?from=INR&to=USD,EUR,GBP,AED')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      Object.keys(data.rates || {}).forEach(function (code) {
        if (CURRENCIES[code]) CURRENCIES[code].rate = data.rates[code];
      });
      if (callback) callback();
    })
    .catch(function (err) {
      console.warn('FX rate fetch failed, staying in INR', err);
    });
}

function convert(amountInInr) {
  var c = CURRENCIES[currentCurrency];
  if (!c || !c.rate) return amountInInr; 
  return amountInInr * c.rate;
}

function currencySymbol() {
  return CURRENCIES[currentCurrency].symbol;
}

function setupCurrencySelector() {
  var sel = document.getElementById('currencySelect');
  if (!sel || sel.dataset.wired) return;
  sel.dataset.wired = 'true';
  sel.addEventListener('change', function () {
    currentCurrency = sel.value;
    onFilterChange(); 
  });
}

function renderDashboard(data, log, cols, fullResult) {
  allData = data;

  try {
    populateFilters(data);
    onFilterChange();
    showCleanLog(log);
    showFileName(fullResult);
    renderScreenTable(fullResult);
    renderDiscrepancyTable(fullResult);
    renderAnomalyTable(fullResult);
    setupDownloadButton();
    setupCurrencySelector();
    setupComparisonToggle();
    fetchFxRates(function () { onFilterChange(); }); 
  } catch(e) {
    console.error('Dashboard render error:', e);
  }
}

function showFileName(fullResult) {
  var el = document.getElementById('uploadedFileName');
  if (!el) return;
  el.textContent = (fullResult && fullResult.uploadedFileName) ? '📁 ' + fullResult.uploadedFileName : '';
}

function setupDownloadButton() {
  var btn = document.getElementById('downloadReportBtn');
  if (!btn || btn.dataset.wired) return; 
  btn.dataset.wired = 'true';
  btn.addEventListener('click', function() {
    window.print();
  });
}

var allScreens = [];
var screenShowOccupancy = false;

function renderScreenTable(fullResult) {
  var section = document.getElementById('screenSection');
  if (!section) return;

  if (!fullResult || !fullResult.has_screen_data || !fullResult.screens || fullResult.screens.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = '';
  allScreens = fullResult.screens;
  screenShowOccupancy = !!fullResult.has_occupancy_data;

  var searchBox = document.getElementById('screenSearch');
  if (searchBox && !searchBox.dataset.wired) {
    searchBox.dataset.wired = 'true';
    searchBox.value = '';
    searchBox.addEventListener('input', function() {
      var query = searchBox.value.trim().toLowerCase();
      var filtered = !query ? allScreens : allScreens.filter(function(s) {
        return s.screen_id.toLowerCase().indexOf(query) !== -1 ||
               s.city.toLowerCase().indexOf(query) !== -1;
      });
      renderScreenRows(filtered);
    });
  }

  renderScreenRows(allScreens);
}

function renderScreenRows(screens) {
  var showOccupancy = screenShowOccupancy;
  var table = document.getElementById('tableScreens');
  var occupancyHeader = showOccupancy ? '<th>Occupancy</th>' : '';

  if (!screens.length) {
    table.innerHTML =
      '<thead><tr>' +
      '<th>Screen ID</th><th>City</th><th>Revenue</th><th>ROI</th><th>CTR</th><th>Campaigns</th><th>Active Days</th>' +
      occupancyHeader +
      '</tr></thead><tbody><tr><td colspan="8">No screens match your search.</td></tr></tbody>';
    return;
  }

  var rows = screens.map(function(s) {
    var occupancyCell = showOccupancy
      ? '<td>' + s.occupancy_percent.toFixed(1) + '%</td>'
      : '';
    return '<tr>' +
      '<td>' + s.screen_id + '</td>' +
      '<td>' + s.city + '</td>' +
      '<td>' + currencySymbol() + fmtNum(convert(s.revenue)) + '</td>' +
      '<td>' + s.roi.toFixed(1) + '%</td>' +
      '<td>' + s.ctr.toFixed(3) + '%</td>' +
      '<td>' + s.campaign_count + '</td>' +
      '<td>' + s.active_days + '</td>' +
      occupancyCell +
      '</tr>';
  }).join('');

  table.innerHTML =
    '<thead><tr>' +
    '<th>Screen ID</th><th>City</th><th>Revenue</th><th>ROI</th><th>CTR</th><th>Campaigns</th><th>Active Days</th>' +
    occupancyHeader +
    '</tr></thead><tbody>' + rows + '</tbody>';
}

function renderDiscrepancyTable(fullResult) {
  var section = document.getElementById('discrepancySection');
  if (!section) return;

  if (!fullResult || !fullResult.has_discrepancy_data || !fullResult.discrepancies || fullResult.discrepancies.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = '';

  var rows = fullResult.discrepancies.map(function(d) {
    return '<tr>' +
      '<td>' + d.screen_id + '</td>' +
      '<td>' + d.campaign + '</td>' +
      '<td>' + d.city + '</td>' +
      '<td>' + d.date + '</td>' +
      '<td>' + d.hours_committed + '</td>' +
      '<td>' + d.hours_delivered + '</td>' +
      '<td style="color:#dc2626;font-weight:600;">' + d.gap_percent + '%</td>' +
      '</tr>';
  }).join('');

  var table = document.getElementById('tableDiscrepancies');
  table.innerHTML =
    '<thead><tr>' +
    '<th>Screen ID</th><th>Campaign</th><th>City</th><th>Date</th>' +
    '<th>Hours Committed</th><th>Hours Delivered</th><th>Under-delivery</th>' +
    '</tr></thead><tbody>' + rows + '</tbody>';
}

function renderAnomalyTable(fullResult) {
  var section = document.getElementById('anomalySection');
  if (!section) return;

  if (!fullResult || !fullResult.anomalies || fullResult.anomalies.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = '';

  var rows = fullResult.anomalies.map(function(a) {
    return '<tr>' +
      '<td>' + a.screen_id + '</td>' +
      '<td>' + a.city + '</td>' +
      '<td>' + a.date + '</td>' +
      '<td>' + fmtNum(a.impressions) + '</td>' +
      '<td>' + fmtNum(a.screen_average) + '</td>' +
      '<td style="color:#dc2626;font-weight:600;">-' + a.drop_percent + '%</td>' +
      '</tr>';
  }).join('');

  var table = document.getElementById('tableAnomalies');
  table.innerHTML =
    '<thead><tr>' +
    '<th>Screen ID</th><th>City</th><th>Date</th>' +
    '<th>Impressions</th><th>Screen\'s Usual Average</th><th>Drop</th>' +
    '</tr></thead><tbody>' + rows + '</tbody>';
}

function populateFilters(data) {
  var cities = uniqueSorted(data, 'City');
  var industries = uniqueSorted(data, 'Industry');
  var campaigns = uniqueSorted(data, 'Campaign_Name');

  fillDropdown('filterCity', cities);
  fillDropdown('filterIndustry', industries);
  fillDropdown('filterCampaign', campaigns);

  var dates = data.map(function(r) { return r.Date; }).filter(Boolean).sort();
  if (dates.length) {
    minDate = dates[0];
    maxDate = dates[dates.length - 1];
    var fromEl = document.getElementById('filterDateFrom');
    var toEl = document.getElementById('filterDateTo');

    fromEl.min = minDate;
    fromEl.max = maxDate;
    toEl.min = minDate;
    toEl.max = maxDate;

    fromEl.value = minDate;
    toEl.value = maxDate;

    var hintEl = document.getElementById('dateRangeHint');
  if (hintEl) {
    hintEl.textContent = 'Data available: ' + minDate + ' to ' + maxDate;
  }
  }

  ['filterCity','filterIndustry','filterCampaign','filterDateFrom','filterDateTo'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) {
      el.removeEventListener('change', onFilterChange);
      el.addEventListener('change', onFilterChange);
    }
  });

  var resetBtn = document.getElementById('filterReset');
  if (resetBtn) {
    resetBtn.removeEventListener('click', function() {});
    resetBtn.addEventListener('click', function() {
      document.getElementById('filterCity').value = '';
      document.getElementById('filterIndustry').value = '';
      document.getElementById('filterCampaign').value = '';
      if (dates.length) {
        document.getElementById('filterDateFrom').value = dates[0];
        document.getElementById('filterDateTo').value = dates[dates.length - 1];
      }
      onFilterChange();
    });
  }
}

function onFilterChange() {
  var city = document.getElementById('filterCity').value;
  var industry = document.getElementById('filterIndustry').value;
  var campaign = document.getElementById('filterCampaign').value;

  var fromEl = document.getElementById('filterDateFrom');
  var toEl = document.getElementById('filterDateTo');
  var from = fromEl.value;
  var to = toEl.value;

  toEl.min = from || minDate;
  fromEl.max = to || maxDate;

  var byNonDateFilters = allData.filter(function(r) {
    if (city && r.City !== city) return false;
    if (industry && r.Industry !== industry) return false;
    if (campaign && r.Campaign_Name !== campaign) return false;
    return true;
  });

  var filtered = byNonDateFilters.filter(function(r) {
    if (from && r.Date < from) return false;
    if (to && r.Date > to) return false;
    return true;
  });

  renderAll(filtered, byNonDateFilters, from, to);
}

function fillDropdown(id, options) {
  var sel = document.getElementById(id);
  if (!sel) return;
  
  while (sel.options.length > 1) {
    sel.remove(1);
  }

  options.forEach(function(v) {
    var o = document.createElement('option');
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  });
}

function renderAll(data, unfilteredByDate, from, to) {
  var noDataEl = document.getElementById('noDataMessage');
  if (noDataEl) {
    if (!data || data.length === 0) {
      noDataEl.classList.remove('hidden');
    } else {
      noDataEl.classList.add('hidden');
    }
  }

  renderKPIs(data);
  renderCharts(data);
  renderTables(data);
  renderInsights(data);
  renderComparison(unfilteredByDate || data, from, to);
}

function renderKPIs(data) {
  if (!data || data.length === 0) {
    document.getElementById('kpiRevenue').textContent = '—';
    document.getElementById('kpiImpressions').textContent = '—';
    document.getElementById('kpiClicks').textContent = '—';
    document.getElementById('kpiAdSpend').textContent = '—';
    document.getElementById('kpiRoi').textContent = '—%';
    document.getElementById('kpiCtr').textContent = '—%';
    document.getElementById('kpiCpc').textContent = currencySymbol() + '—';
    document.getElementById('kpiCpm').textContent = currencySymbol() + '—';
    return;
  }

  var revenue = sumCol(data, 'revenue');
  var impressions = sumCol(data, 'Impressions');
  var clicks = sumCol(data, 'Clicks');
  var spend = sumCol(data, 'ad_spend');
  var roi = avgCol(data, 'roi_percent');
  var ctr = avgCol(data, 'ctr');
  var cpc = avgCol(data, 'cpc');
  var cpm = avgCol(data, 'cpm');

  setText('kpiRevenue', currencySymbol() + fmtNum(convert(revenue)));
  setText('kpiImpressions', fmtNum(impressions));
  setText('kpiClicks', fmtNum(clicks));
  setText('kpiAdSpend', currencySymbol() + fmtNum(convert(spend)));
  setText('kpiRoi', roi.toFixed(1) + '%');
  setText('kpiCtr', ctr.toFixed(3) + '%');
  setText('kpiCpc', currencySymbol() + convert(cpc).toFixed(2));
  setText('kpiCpm', currencySymbol() + convert(cpm).toFixed(2));
}

function renderCharts(data) {
  var chartIds = ['chartRevTime', 'chartImpTime', 'chartIndustry', 'chartCity', 'chartRoi'];

  if (!data || data.length === 0) {
    chartIds.forEach(function(id) { destroyChart(id); });
    return;
  }

  var byDate = groupBy(data, 'Date');
  var dates = Object.keys(byDate).sort();
  var revByDate = dates.map(function(d) { return convert(sumCol(byDate[d], 'revenue')); });
  var impByDate = dates.map(function(d) { return sumCol(byDate[d], 'Impressions'); });

  drawLine('chartRevTime', dates, revByDate, '#3b82f6', 'Revenue', true);
  drawLine('chartImpTime', dates, impByDate, '#6366f1', 'Impressions', false);

  var byIndustry = groupBy(data, 'Industry');
  var industries = Object.keys(byIndustry).sort(function(a, b) {
    return sumCol(byIndustry[b], 'revenue') - sumCol(byIndustry[a], 'revenue');
  });
  var revByIndustry = industries.map(function(i) { return convert(sumCol(byIndustry[i], 'revenue')); });
  drawBar('chartIndustry', industries, revByIndustry, '#3b82f6');

  var byCity = groupBy(data, 'City');
  var cities = Object.keys(byCity).sort(function(a, b) {
    return sumCol(byCity[b], 'revenue') - sumCol(byCity[a], 'revenue');
  });
  var revByCity = cities.map(function(c) { return convert(sumCol(byCity[c], 'revenue')); });
  drawBar('chartCity', cities, revByCity, '#6366f1');

  var byCampaign = groupBy(data, 'Campaign_Name');
  var campaignList = Object.keys(byCampaign).map(function(name) {
    return {
      name: name.length > 22 ? name.slice(0, 22) + '…' : name,
      roi: avgCol(byCampaign[name], 'roi_percent'),
      rev: convert(sumCol(byCampaign[name], 'revenue'))
    };
  });
  campaignList.sort(function(a, b) { return b.roi - a.roi; });
  var top10 = campaignList.slice(0, 10);

  var chartTitle = document.getElementById('chartRoiTitle');
  if (chartTitle) {
    chartTitle.textContent = campaignList.length > 10 ? 'Top 10 Campaigns by ROI' : 'Campaigns by ROI';
  }

  drawDualBar('chartRoi', top10.map(function(c) { return c.name; }), top10.map(function(c) { return c.roi; }), top10.map(function(c) { return c.rev; }));
}

function drawLine(id, labels, values, color, label, isCurrency) {
  destroyChart(id);
  var canvas = document.getElementById(id);
  if (!canvas) return;

  chartInstances[id] = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: values,
        borderColor: color,
        backgroundColor: color + '22',
        fill: true,
        tension: 0.4,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 10 } } },
        y: { ticks: { font: { size: 10 }, callback: function(v) { return (isCurrency ? currencySymbol() : '') + fmtNum(v); } } }
      }
    }
  });
}

function drawBar(id, labels, values, color) {
  destroyChart(id);
  var canvas = document.getElementById(id);
  if (!canvas) return;

  chartInstances[id] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: color,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { size: 9 } } },
        y: { ticks: { font: { size: 10 }, callback: function(v) { return currencySymbol() + fmtNum(v); } } }
      }
    }
  });
}

function drawDualBar(id, labels, roiValues, revValues) {
  destroyChart(id);
  var canvas = document.getElementById(id);
  if (!canvas) return;

  chartInstances[id] = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'ROI %',
          data: roiValues,
          backgroundColor: '#475569',
          borderRadius: 4,
          yAxisID: 'y'
        },
        {
          label: 'Revenue',
          data: revValues,
          backgroundColor: '#3b82f6',
          borderRadius: 4,
          yAxisID: 'y2'
        }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'top', labels: { font: { size: 10 } } } },
      scales: {
        x: { ticks: { font: { size: 9 } } },
        y: { position: 'left', ticks: { font: { size: 10 } } },
        y2: {
          position: 'right',
          ticks: { font: { size: 10 }, callback: function(v) { return currencySymbol() + fmtNum(v); } },
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}

function destroyChart(id) {
  if (chartInstances[id]) {
    chartInstances[id].destroy();
    delete chartInstances[id];
  }
}

var MIN_CAMPAIGNS_TO_SPLIT = 10; 

function renderTables(data) {
  var bottomBox = document.getElementById('bottomTableBox');
  var topTitle = document.getElementById('tableTopTitle');
  var tableRow = document.getElementById('tableRow');

  if (!data || data.length === 0) {
    document.getElementById('tableTop').innerHTML = '<tr><td>No data</td></tr>';
    document.getElementById('tableBottom').innerHTML = '<tr><td>No data</td></tr>';
    if (bottomBox) bottomBox.style.display = '';
    if (tableRow) tableRow.style.gridTemplateColumns = '';
    return;
  }

  var byCampaign = groupBy(data, 'Campaign_Name');

  var rows = Object.keys(byCampaign).map(function(name) {
    var r = byCampaign[name];
    return {
      name: name,
      revenue: sumCol(r, 'revenue'),
      ad_spend: sumCol(r, 'ad_spend'),
      roi: avgCol(r, 'roi_percent'),
      ctr: avgCol(r, 'ctr'),
      impressions: sumCol(r, 'Impressions')
    };
  });

  rows.sort(function(a, b) { return b.roi - a.roi; });

  var cols = ['Campaign', 'Revenue', 'Ad Spend', 'ROI %', 'CTR %', 'Impressions'];

  if (rows.length < MIN_CAMPAIGNS_TO_SPLIT) {
    buildTable('tableTop', rows, cols);
    document.getElementById('tableBottom').innerHTML = '';
    if (bottomBox) bottomBox.style.display = 'none';
    if (topTitle) topTitle.textContent = '📊 Campaigns Ranked by ROI';
    if (tableRow) tableRow.style.gridTemplateColumns = '1fr';
  } else {
    buildTable('tableTop', rows.slice(0, 5), cols);
    buildTable('tableBottom', rows.slice(-5).reverse(), cols);
    if (bottomBox) bottomBox.style.display = '';
    if (topTitle) topTitle.textContent = '▲ Top 5 Campaigns by ROI';
    if (tableRow) tableRow.style.gridTemplateColumns = '';
  }
}

function buildTable(id, rows, cols) {
  var t = document.getElementById(id);
  if (!t) return;

  var html = '<thead><tr>';
  cols.forEach(function(c) { html += '<th>' + c + '</th>'; });
  html += '</tr></thead><tbody>';

  rows.forEach(function(r) {
    html += '<tr>';
    html += '<td>' + r.name + '</td>';
    html += '<td>' + currencySymbol() + fmtNum(convert(r.revenue)) + '</td>';
    html += '<td>' + currencySymbol() + fmtNum(convert(r.ad_spend)) + '</td>';
    html += '<td>' + r.roi.toFixed(2) + '</td>';
    html += '<td>' + r.ctr.toFixed(3) + '</td>';
    html += '<td>' + fmtNum(r.impressions) + '</td>';
    html += '</tr>';
  });

  html += '</tbody>';
  t.innerHTML = html;
}

function renderInsights(data) {
  var grid = document.getElementById('insightsGrid');
  if (!grid) return;
  grid.innerHTML = '';

  if (!data || !data.length) return;

  var byCity = groupBy(data, 'City');
  var byIndustry = groupBy(data, 'Industry');
  var byCampaign = groupBy(data, 'Campaign_Name');

  var topCity = topBy(byCity, function(rows) { return sumCol(rows, 'revenue'); });
  var topIndustry = topBy(byIndustry, function(rows) { return sumCol(rows, 'revenue'); });
  var topRoi = topBy(byCampaign, function(rows) { return avgCol(rows, 'roi_percent'); });
  var botRoi = botBy(byCampaign, function(rows) { return avgCol(rows, 'roi_percent'); });
  var topCtr = topBy(byCampaign, function(rows) { return avgCol(rows, 'ctr'); });

  var totalRev = sumCol(data, 'revenue');
  var totalSpend = sumCol(data, 'ad_spend');
  var overallRoi = totalSpend > 0 ? (((totalRev - totalSpend) / totalSpend) * 100).toFixed(1) : 0;

  var insights = [
    { label: 'Top City', text: topCity.key + ' generated the highest revenue of ' + currencySymbol() + fmtNum(convert(topCity.val)) + '.' },
    { label: 'Top Industry', text: topIndustry.key + ' leads all industries with ' + currencySymbol() + fmtNum(convert(topIndustry.val)) + ' revenue.' },
    { label: 'Best ROI Campaign', text: '"' + topRoi.key + '" has the best ROI at ' + topRoi.val.toFixed(1) + '%.' },
    { label: 'Lowest ROI', text: '"' + botRoi.key + '" has the lowest ROI at ' + botRoi.val.toFixed(1) + '% — review spend.' },
    { label: 'Best CTR Campaign', text: '"' + topCtr.key + '" drives the highest CTR at ' + topCtr.val.toFixed(3) + '%.' },
    { label: 'Overall ROI', text: 'Portfolio ROI across all campaigns: ' + overallRoi + '%.' }
  ];

  insights.forEach(function(i) {
    var card = document.createElement('div');
    card.className = 'insight-card';
    card.innerHTML = '<strong>' + i.label + '</strong> ' + i.text;
    grid.appendChild(card);
  });
}


function pad2(n) { return n < 10 ? '0' + n : '' + n; }

function addDays(dateStr, days) {
  var d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() + days);
  return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
}

function daysBetween(startStr, endStr) {
  var d1 = new Date(startStr + 'T00:00:00');
  var d2 = new Date(endStr + 'T00:00:00');
  return Math.round((d2 - d1) / 86400000);
}

function filterByRange(data, start, end) {
  return data.filter(function(r) { return r.Date && r.Date >= start && r.Date <= end; });
}

function renderComparison(baseData, from, to) {
  var grid = document.getElementById('comparisonGrid');
  var labelEl = document.getElementById('comparisonRangeLabel');
  if (!grid) return; 

  if (!baseData || !baseData.length) {
    grid.innerHTML = '';
    if (labelEl) labelEl.textContent = '';
    return;
  }

  var allDates = baseData.map(function(r) { return r.Date; }).filter(Boolean).sort();
  if (!allDates.length) { grid.innerHTML = ''; return; }

  var curStart = from || allDates[0];
  var curEnd = to || allDates[allDates.length - 1];

  var periodLength = daysBetween(curStart, curEnd) + 1;
  var prevEnd = addDays(curStart, -1);
  var prevStart = addDays(prevEnd, -(periodLength - 1));

  var curData = filterByRange(baseData, curStart, curEnd);
  var prevData = filterByRange(baseData, prevStart, prevEnd);

  if (labelEl) {
    labelEl.textContent = curStart + ' to ' + curEnd + '  vs  ' + prevStart + ' to ' + prevEnd + ' (equal-length prior period)';
  }

  if (!prevData.length) {
    grid.innerHTML = '<div class="compare-empty">No data available before ' + curStart +
      ' — narrow the date filter to a range with history before it to see a comparison.</div>';
    return;
  }

  var metrics = [
    { key: 'revenue', label: 'Revenue', currency: true },
    { key: 'ad_spend', label: 'Ad Spend', currency: true },
    { key: 'Impressions', label: 'Impressions', currency: false },
    { key: 'Clicks', label: 'Clicks', currency: false }
  ];

  var html = '';
  metrics.forEach(function(m) {
    var curVal = sumCol(curData, m.key);
    var prevVal = sumCol(prevData, m.key);
    var change = prevVal > 0 ? ((curVal - prevVal) / prevVal * 100) : (curVal > 0 ? 100 : 0);
    var up = change >= 0;
    var curDisplay = m.currency ? currencySymbol() + fmtNum(convert(curVal)) : fmtNum(curVal);
    var prevDisplay = m.currency ? currencySymbol() + fmtNum(convert(prevVal)) : fmtNum(prevVal);

    html += '<div class="compare-card">' +
      '<div class="compare-label">' + m.label + '</div>' +
      '<div class="compare-current">' + curDisplay + '</div>' +
      '<div class="compare-change ' + (up ? 'up' : 'down') + '">' + (up ? '▲' : '▼') + ' ' + Math.abs(change).toFixed(1) + '%</div>' +
      '<div class="compare-prev">vs ' + prevDisplay + ' prior period</div>' +
      '</div>';
  });

  grid.innerHTML = html;
}

function setupComparisonToggle() {
  var weekBtn = document.getElementById('compareWeekBtn');
  var monthBtn = document.getElementById('compareMonthBtn');
  if (!weekBtn || !monthBtn || weekBtn.dataset.wired) return;
  weekBtn.dataset.wired = 'true';

  weekBtn.addEventListener('click', function() {
    weekBtn.classList.add('active');
    monthBtn.classList.remove('active');
    applyQuickDateRange(7);
  });
  monthBtn.addEventListener('click', function() {
    monthBtn.classList.add('active');
    weekBtn.classList.remove('active');
    applyQuickDateRange(30);
  });
}

function applyQuickDateRange(trailingDays) {
  var city = document.getElementById('filterCity').value;
  var industry = document.getElementById('filterIndustry').value;
  var campaign = document.getElementById('filterCampaign').value;

  var byNonDateFilters = allData.filter(function(r) {
    if (city && r.City !== city) return false;
    if (industry && r.Industry !== industry) return false;
    if (campaign && r.Campaign_Name !== campaign) return false;
    return true;
  });

  var dates = byNonDateFilters.map(function(r) { return r.Date; }).filter(Boolean).sort();
  if (!dates.length) return;

  var latest = dates[dates.length - 1];
  var start = addDays(latest, -(trailingDays - 1));

  document.getElementById('filterDateFrom').value = start;
  document.getElementById('filterDateTo').value = latest;
  onFilterChange();
}

function showCleanLog(log) {
  var el = document.getElementById('cleanLog');
  if (!el) return;

  var html = '<span><span class="tag">Total Rows</span>' + (log.total_rows || 0) + '</span>' +
    '<span><span class="tag">Empty Rows Removed</span>' + (log.empty_rows_removed || 0) + '</span>' +
    '<span><span class="tag">Duplicates Removed</span>' + (log.duplicate_rows_removed || 0) + '</span>' +
    '<span><span class="tag">Missing/Invalid Values Fixed</span>' + (log.missing_values_fixed || 0) + '</span>' +
    '<span><span class="tag">Invalid Dates</span>' + (log.invalid_dates || 0) + '</span>' +
    '<span><span class="tag">Rows Saved to DB</span>' + (log.row_save_to_database || 0) + '</span>' +
    '<span><span class="tag">Final Rows</span>' + (log.final_rows || log.total_rows || 0) + '</span>';

  if (log.column_map) {
    html += '<br/><span style="margin-top:0.5rem;font-weight:600;color:#1e293b">Detected Columns: </span>';
    for (var f in log.column_map) {
      html += '<span><span class="tag">' + f + '</span>' + (log.column_map[f] || 'NOT FOUND') + '</span>';
    }
  }

  if (log.warnings && log.warnings.length) {
    html += '<br/><span style="color:#b45309;font-weight:600">Warnings: </span>';
    log.warnings.forEach(function(w) {
      html += '<span style="color:#b45309">' + w + '</span> ';
    });
  }

  el.innerHTML = html;
}

function sumCol(arr, key) {
  return arr.reduce(function(total, row) { return total + (row[key] || 0); }, 0);
}

function avgCol(arr, key) {
  if (!arr.length) return 0;
  return sumCol(arr, key) / arr.length;
}

function groupBy(arr, key) {
  return arr.reduce(function(acc, row) {
    var k = row[key] || 'Unknown';
    if (!acc[k]) acc[k] = [];
    acc[k].push(row);
    return acc;
  }, {});
}

function uniqueSorted(arr, key) {
  var seen = {};
  arr.forEach(function(r) { if (r[key]) seen[r[key]] = true; });
  return Object.keys(seen).sort();
}

function topBy(groups, metricFn) {
  var topKey = '', topVal = -Infinity;
  Object.keys(groups).forEach(function(k) {
    var v = metricFn(groups[k]);
    if (v > topVal) { topVal = v; topKey = k; }
  });
  return { key: topKey, val: topVal };
}

function botBy(groups, metricFn) {
  var botKey = '', botVal = Infinity;
  Object.keys(groups).forEach(function(k) {
    var v = metricFn(groups[k]);
    if (v < botVal) { botVal = v; botKey = k; }
  });
  return { key: botKey, val: botVal };
}

function setText(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}

function fmtNum(n) {
  n = Number(n);
  if (isNaN(n)) return '0';

  if (currentCurrency === 'INR') {
    if (n >= 10000000) return (n / 10000000).toFixed(1) + 'Cr';
    if (n >= 100000) return (n / 100000).toFixed(1) + 'L';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toFixed(1);
  }

  if (n >= 1000000000) return (n / 1000000000).toFixed(1) + 'B';
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toFixed(1);
}
