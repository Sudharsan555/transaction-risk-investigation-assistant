/**
 * Frontend logic for Transaction Risk Investigation Assistant (PS06)
 */

let state = {
  customers: [],
  activeCustomerId: null,
  activeAnalysisResult: null,
  activeTransactions: [],
  filterMode: 'ALL', // 'ALL' | 'FLAGGED' | 'CLEAN'
  searchTerm: '',
  txnSearchTerm: '',
  showOnlyFlaggedTxns: false,
  isRawView: false,
  testFixtures: []
};

// DOM Elements
const el = {
  modelStatusText: document.getElementById('modelStatusText'),
  reportModelBadge: document.getElementById('reportModelBadge'),
  customerSearchInput: document.getElementById('customerSearchInput'),
  customerListContainer: document.getElementById('customerListContainer'),
  tabFilterAll: document.getElementById('tabFilterAll'),
  tabFilterFlagged: document.getElementById('tabFilterFlagged'),
  tabFilterClean: document.getElementById('tabFilterClean'),
  countAll: document.getElementById('countAll'),
  countFlagged: document.getElementById('countFlagged'),
  countClean: document.getElementById('countClean'),
  statTotalCount: document.getElementById('statTotalCount'),
  statFlaggedCount: document.getElementById('statFlaggedCount'),
  statCleanCount: document.getElementById('statCleanCount'),
  
  // Banner
  customerAvatar: document.getElementById('customerAvatar'),
  customerName: document.getElementById('customerName'),
  customerAccountType: document.getElementById('customerAccountType'),
  customerAccountNumber: document.getElementById('customerAccountNumber'),
  customerTxnCount: document.getElementById('customerTxnCount'),
  customerVerdictBadge: document.getElementById('customerVerdictBadge'),
  verdictIcon: document.getElementById('verdictIcon'),
  verdictText: document.getElementById('verdictText'),
  customerRiskScore: document.getElementById('customerRiskScore'),

  // Baseline metrics
  metricAvgSpend: document.getElementById('metricAvgSpend'),
  metricStdDev: document.getElementById('metricStdDev'),
  metricMaxNormal: document.getElementById('metricMaxNormal'),
  metricActiveHours: document.getElementById('metricActiveHours'),
  metricKnownPayees: document.getElementById('metricKnownPayees'),
  metricChannels: document.getElementById('metricChannels'),

  // Report
  reportLoadingState: document.getElementById('reportLoadingState'),
  reportContent: document.getElementById('reportContent'),
  reportRawJson: document.getElementById('reportRawJson'),
  btnCopyReport: document.getElementById('btnCopyReport'),
  btnToggleRawView: document.getElementById('btnToggleRawView'),

  // Transaction Ledger
  ledgerBadgeInfo: document.getElementById('ledgerBadgeInfo'),
  txnTableSearch: document.getElementById('txnTableSearch'),
  chkOnlyFlagged: document.getElementById('chkOnlyFlagged'),
  txnTableBody: document.getElementById('txnTableBody'),

  // Sandbox
  btnOpenSandbox: document.getElementById('btnOpenSandbox'),
  sandboxModal: document.getElementById('sandboxModal'),
  btnCloseSandbox: document.getElementById('btnCloseSandbox'),
  btnCancelSandbox: document.getElementById('btnCancelSandbox'),
  btnRunSandboxAnalysis: document.getElementById('btnRunSandboxAnalysis'),
  sandboxPayloadText: document.getElementById('sandboxPayloadText'),
  tabBenchmarks: document.getElementById('tabBenchmarks'),
  tabCustomJson: document.getElementById('tabCustomJson'),
  viewBenchmarks: document.getElementById('viewBenchmarks'),
  viewCustomJson: document.getElementById('viewCustomJson'),
  benchmarkGridContainer: document.getElementById('benchmarkGridContainer') || document.getElementById('benchmarkGrid'),
  uploadDropZone: document.getElementById('uploadDropZone'),
  sandboxFileInput: document.getElementById('sandboxFileInput'),
  btnFormatJson: document.getElementById('btnFormatJson'),
  btnLoadDefaultTemplate: document.getElementById('btnLoadDefaultTemplate'),
  
  toastMsg: document.getElementById('toastMsg')
};

// Initialize Application
async function initApp() {
  setupEventListeners();
  await checkHealth();
  await fetchCustomers();
  await fetchTestFixtures();

  // Auto-select first customer if available
  if (state.customers.length > 0) {
    selectCustomer(state.customers[0].customer_id);
  }
}

// Event Listeners
function setupEventListeners() {
  // Sidebar Search
  el.customerSearchInput.addEventListener('input', (e) => {
    state.searchTerm = e.target.value.toLowerCase();
    renderCustomerList();
  });

  // Filter Tabs
  el.tabFilterAll.addEventListener('click', () => setFilter('ALL'));
  el.tabFilterFlagged.addEventListener('click', () => setFilter('FLAGGED'));
  el.tabFilterClean.addEventListener('click', () => setFilter('CLEAN'));

  // Transaction Ledger Search & Filter
  el.txnTableSearch.addEventListener('input', (e) => {
    state.txnSearchTerm = e.target.value.toLowerCase();
    renderTransactionTable();
  });

  el.chkOnlyFlagged.addEventListener('change', (e) => {
    state.showOnlyFlaggedTxns = e.target.checked;
    renderTransactionTable();
  });

  // Report Actions
  el.btnCopyReport.addEventListener('click', copyReportToClipboard);
  el.btnToggleRawView.addEventListener('click', toggleRawView);

  // Sandbox Modal
  el.btnOpenSandbox.addEventListener('click', openSandboxModal);
  el.btnCloseSandbox.addEventListener('click', closeSandboxModal);
  el.btnCancelSandbox.addEventListener('click', closeSandboxModal);
  el.btnRunSandboxAnalysis.addEventListener('click', runSandboxAnalysis);

  // Tabs inside modal
  if (el.tabBenchmarks && el.tabCustomJson) {
    el.tabBenchmarks.addEventListener('click', () => switchSandboxTab('BENCHMARKS'));
    el.tabCustomJson.addEventListener('click', () => switchSandboxTab('CUSTOM'));
  }

  // Format JSON
  if (el.btnFormatJson) {
    el.btnFormatJson.addEventListener('click', formatSandboxJson);
  }

  // Load sample template
  if (el.btnLoadDefaultTemplate) {
    el.btnLoadDefaultTemplate.addEventListener('click', loadDefaultSampleTemplate);
  }

  // Sandbox File Upload & Drag-and-Drop
  if (el.sandboxFileInput) {
    el.sandboxFileInput.addEventListener('change', handleFileUpload);
  }

  if (el.uploadDropZone) {
    el.uploadDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      el.uploadDropZone.classList.add('drag-over');
    });
    el.uploadDropZone.addEventListener('dragleave', () => {
      el.uploadDropZone.classList.remove('drag-over');
    });
    el.uploadDropZone.addEventListener('drop', handleFileDrop);
  }

  // Also support drag-and-drop directly onto textarea
  if (el.sandboxPayloadText) {
    el.sandboxPayloadText.addEventListener('dragover', (e) => {
      e.preventDefault();
      el.sandboxPayloadText.style.borderColor = 'var(--accent-blue)';
    });
    el.sandboxPayloadText.addEventListener('dragleave', () => {
      el.sandboxPayloadText.style.borderColor = '';
    });
    el.sandboxPayloadText.addEventListener('drop', (e) => {
      e.preventDefault();
      el.sandboxPayloadText.style.borderColor = '';
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        readFileIntoSandbox(e.dataTransfer.files[0]);
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && el.sandboxModal.classList.contains('open')) {
      closeSandboxModal();
    }
  });
}

// Health Check & Model Info
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.gemini_api_configured) {
      el.modelStatusText.textContent = `⚡ Standby (${data.active_model})`;
    } else {
      el.modelStatusText.textContent = `⚡ Deterministic Fallback Active`;
    }
  } catch (err) {
    el.modelStatusText.textContent = `⚡ Offline Fallback`;
  }
}

// Fetch Customer Overview List
async function fetchCustomers() {
  try {
    const res = await fetch('/api/customers');
    const data = await res.json();
    state.customers = data.customers || [];
    updateSidebarCounts();
    renderCustomerList();
  } catch (err) {
    console.error('Error fetching customers:', err);
    showToast('Failed to load customer list.');
  }
}

// Update Sidebar Tab Numbers & Quick Stats
function updateSidebarCounts() {
  const total = state.customers.length;
  const flagged = state.customers.filter(c => c.verdict === 'ATTENTION_REQUIRED').length;
  const clean = total - flagged;

  el.countAll.textContent = total;
  el.countFlagged.textContent = flagged;
  el.countClean.textContent = clean;

  el.statTotalCount.textContent = total;
  el.statFlaggedCount.textContent = flagged;
  el.statCleanCount.textContent = clean;
}

// Set Active Filter Tab
function setFilter(mode) {
  state.filterMode = mode;
  [el.tabFilterAll, el.tabFilterFlagged, el.tabFilterClean].forEach(btn => btn.classList.remove('active'));
  if (mode === 'ALL') el.tabFilterAll.classList.add('active');
  if (mode === 'FLAGGED') el.tabFilterFlagged.classList.add('active');
  if (mode === 'CLEAN') el.tabFilterClean.classList.add('active');
  renderCustomerList();
}

// Render Sidebar Customer Cards
function renderCustomerList() {
  el.customerListContainer.innerHTML = '';
  
  const filtered = state.customers.filter(c => {
    const matchesSearch = c.name.toLowerCase().includes(state.searchTerm) ||
                          c.customer_id.toLowerCase().includes(state.searchTerm) ||
                          c.account_number.toLowerCase().includes(state.searchTerm);
    
    if (!matchesSearch) return false;
    const isFlagged = c.verdict === 'ATTENTION_REQUIRED';
    if (state.filterMode === 'FLAGGED') return isFlagged;
    if (state.filterMode === 'CLEAN') return !isFlagged;
    return true;
  });

  if (filtered.length === 0) {
    el.customerListContainer.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-dim); font-size: 0.8rem;">No matching accounts found.</div>`;
    return;
  }

  filtered.forEach(cust => {
    const card = document.createElement('div');
    const isSelected = cust.customer_id === state.activeCustomerId;
    card.className = `customer-card ${isSelected ? 'active' : ''}`;
    
    const isFlagged = cust.verdict === 'ATTENTION_REQUIRED';
    const isInsufficient = cust.verdict === 'INSUFFICIENT_EVIDENCE' || cust.total_transactions < 5;

    let tagClass = 'clean';
    let tagText = '🛡️ Normal';

    if (isFlagged) {
      tagClass = 'flagged';
      tagText = `⚠️ Risk: ${cust.risk_score}`;
    } else if (isInsufficient) {
      tagClass = 'insufficient';
      tagText = 'ℹ️ Sparse';
    }

    card.innerHTML = `
      <div class="card-top-row">
        <div>
          <div class="customer-name">${cust.name}</div>
          <div class="customer-id">${cust.customer_id} • ${cust.account_number}</div>
        </div>
        <span class="risk-tag ${tagClass}">${tagText}</span>
      </div>
      <div class="card-bottom-row">
        <span class="account-type-tag">${cust.account_type}</span>
        <span style="color: var(--text-muted);">${cust.total_transactions} txns</span>
      </div>
    `;

    card.addEventListener('click', () => selectCustomer(cust.customer_id));
    el.customerListContainer.appendChild(card);
  });
}

// Select and Load Customer Investigation
async function selectCustomer(customerId) {
  state.activeCustomerId = customerId;
  renderCustomerList();

  // Reset UI to loading state
  el.reportLoadingState.style.display = 'flex';
  el.reportContent.style.display = 'none';
  el.reportRawJson.style.display = 'none';

  try {
    // 1. Fetch analysis
    const analysisPromise = fetch(`/api/customers/${customerId}/analysis`).then(r => r.json());
    // 2. Fetch full transactions
    const txnsPromise = fetch(`/api/customers/${customerId}/transactions`).then(r => r.json());

    const [analysisResult, txnsResult] = await Promise.all([analysisPromise, txnsPromise]);

    state.activeAnalysisResult = analysisResult;
    state.activeTransactions = txnsResult.transactions || [];

    renderCustomerHeader(analysisResult);
    renderBaselineMetrics(analysisResult);
    renderInvestigationReport(analysisResult);
    renderTransactionTable();

  } catch (err) {
    console.error('Error loading customer details:', err);
    showToast('Failed to load investigation details.');
    el.reportLoadingState.style.display = 'none';
  }
}

// Render Top Customer Banner
function renderCustomerHeader(result) {
  const initials = result.customer_name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2) || '--';
  el.customerAvatar.textContent = initials;
  el.customerName.textContent = result.customer_name;
  el.customerAccountType.textContent = result.account_type;
  el.customerAccountNumber.textContent = result.account_number;
  
  const totalTx = result.summary_statistics?.total_transactions || 0;
  const totalVol = result.summary_statistics?.total_volume || 0;
  el.customerTxnCount.textContent = `${totalTx} transactions ($${totalVol.toLocaleString('en-US', { minimumFractionDigits: 2 })})`;

  const isAttention = result.verdict === 'ATTENTION_REQUIRED';
  const isInsufficient = result.verdict === 'INSUFFICIENT_EVIDENCE' || result.evidence_status === 'INSUFFICIENT_EVIDENCE';

  if (isAttention) {
    el.customerVerdictBadge.className = 'verdict-large-badge attention';
    el.verdictIcon.textContent = '🚨';
    el.verdictText.textContent = 'ATTENTION_REQUIRED';
    el.customerRiskScore.style.color = 'var(--risk-high-text)';
  } else if (isInsufficient) {
    el.customerVerdictBadge.className = 'verdict-large-badge insufficient';
    el.verdictIcon.textContent = 'ℹ️';
    el.verdictText.textContent = 'INSUFFICIENT_EVIDENCE';
    el.customerRiskScore.style.color = '#facc15';
  } else {
    el.customerVerdictBadge.className = 'verdict-large-badge clean';
    el.verdictIcon.textContent = '🛡️';
    el.verdictText.textContent = 'NOTHING_FLAGGED';
    el.customerRiskScore.style.color = 'var(--clean-text)';
  }

  el.customerRiskScore.textContent = `${result.risk_score}/100`;
}

// Render Baseline Metric Cards
function renderBaselineMetrics(result) {
  const base = result.customer_baseline || {};
  const avg = base.baseline_avg_amount || 0;
  const std = base.baseline_std_amount || 0;
  const maxNorm = base.baseline_max_normal || 0;
  const hours = base.baseline_active_hours || [8, 22];
  const payeesCount = base.known_payees_count || 0;
  const channels = base.common_channels || ['Mobile', 'POS'];

  el.metricAvgSpend.textContent = `$${avg.toFixed(2)}`;
  el.metricStdDev.textContent = `Std Dev: $${std.toFixed(2)}`;
  el.metricMaxNormal.textContent = `$${maxNorm.toFixed(2)}`;
  el.metricActiveHours.textContent = `${String(hours[0]).padStart(2, '0')}:00 - ${String(hours[1]).padStart(2, '0')}:00`;
  el.metricKnownPayees.textContent = `${payeesCount} Known Payees`;
  el.metricChannels.textContent = channels.join(', ');
}

// Render Markdown Investigation Report
function renderInvestigationReport(result) {
  el.reportLoadingState.style.display = 'none';
  state.isRawView = false;
  el.reportRawJson.style.display = 'none';
  el.reportContent.style.display = 'block';

  const rawMarkdown = result.llm_report || "No report generated.";
  
  // Parse markdown
  let html = (typeof marked !== 'undefined') ? marked.parse(rawMarkdown) : `<pre>${rawMarkdown}</pre>`;
  
  // Clean up any double code-wrapping from marked: <code>[TXN-xxxx]</code> -> [TXN-xxxx]
  html = html.replace(/<code>\s*\[?([A-Za-z0-9_-]+)\]?\s*<\/code>/g, (m, id) => {
    return (id.startsWith('TXN-') || id.startsWith('CUSTOM-') || id.startsWith('SB-') || id.startsWith('TEST-')) ? `[${id}]` : m;
  });

  // Enforce clickable interactive transaction ID tags [TXN-XXXX], [CUSTOM-XXXX], [SB-XXXX], etc.
  html = html.replace(/\[((?:TXN|CUSTOM|SB|TEST)[A-Za-z0-9_-]*)\]/g, (match, txnId) => {
    return `<code class="citation-tag" onclick="highlightTransaction('${txnId}')" title="Click to trace in transaction ledger">[${txnId}]</code>`;
  });

  el.reportContent.innerHTML = html;
  el.reportRawJson.textContent = JSON.stringify(result, null, 2);

  // Update model status accurately based on actual result
  const isFallback = result.fallback_used !== false;
  const modelName = result.llm_model_used || (isFallback ? 'Deterministic Fallback' : 'Google Gemini Grounded');
  
  if (isFallback) {
    el.modelStatusText.textContent = `⚡ Deterministic Fallback Active`;
    if (el.reportModelBadge) {
      el.reportModelBadge.textContent = `⚡ ${modelName}`;
      el.reportModelBadge.style.background = 'rgba(234, 179, 8, 0.15)';
      el.reportModelBadge.style.color = '#eab308';
      el.reportModelBadge.style.borderColor = 'rgba(234, 179, 8, 0.3)';
    }
  } else {
    el.modelStatusText.textContent = `🟢 ${modelName}`;
    if (el.reportModelBadge) {
      el.reportModelBadge.textContent = `🟢 ${modelName}`;
      el.reportModelBadge.style.background = 'rgba(34, 197, 94, 0.15)';
      el.reportModelBadge.style.color = '#22c55e';
      el.reportModelBadge.style.borderColor = 'rgba(34, 197, 94, 0.3)';
    }
  }
}

// Highlight and Scroll to Transaction from Citation Click
window.highlightTransaction = function(txnId) {
  // Clear any existing highlight
  const rows = el.txnTableBody.querySelectorAll('tr');
  rows.forEach(r => r.classList.remove('highlight-target'));

  const targetRow = document.getElementById(`row-${txnId}`);
  if (targetRow) {
    targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    targetRow.classList.add('highlight-target');
    showToast(`Traceable Citation: Jumped to transaction [${txnId}]`);
    setTimeout(() => {
      targetRow.classList.remove('highlight-target');
    }, 4500);
  } else {
    // If filtered out, turn off filter
    if (state.showOnlyFlaggedTxns || state.txnSearchTerm) {
      state.showOnlyFlaggedTxns = false;
      state.txnSearchTerm = '';
      el.chkOnlyFlagged.checked = false;
      el.txnTableSearch.value = '';
      renderTransactionTable();
      setTimeout(() => highlightTransaction(txnId), 100);
    } else {
      showToast(`Transaction ${txnId} not found in current ledger.`);
    }
  }
};

// Render Transaction Ledger Table
function renderTransactionTable() {
  el.txnTableBody.innerHTML = '';
  
  const txns = state.activeTransactions;
  const filtered = txns.filter(t => {
    if (state.showOnlyFlaggedTxns && !t.is_flagged) return false;
    if (state.txnSearchTerm) {
      const match = t.transaction_id.toLowerCase().includes(state.txnSearchTerm) ||
                    t.payee.toLowerCase().includes(state.txnSearchTerm) ||
                    t.description.toLowerCase().includes(state.txnSearchTerm) ||
                    t.channel.toLowerCase().includes(state.txnSearchTerm);
      if (!match) return false;
    }
    return true;
  });

  const flaggedCount = txns.filter(t => t.is_flagged).length;
  el.ledgerBadgeInfo.textContent = `${filtered.length} of ${txns.length} (${flaggedCount} Cited)`;

  if (filtered.length === 0) {
    el.txnTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-dim);">No transactions found.</td></tr>`;
    return;
  }

  filtered.forEach(t => {
    const row = document.createElement('tr');
    row.id = `row-${t.transaction_id}`;
    if (t.is_flagged) {
      row.className = 'flagged-row';
    }

    const channelClass = t.channel.toLowerCase() === 'wire' ? 'channel-pill wire' : 'channel-pill';
    const statusHtml = t.is_flagged
      ? `<span class="flag-badge" title="${(t.flag_reasons || []).join(', ')}">⚠️ ${t.flag_reasons?.[0] || 'Flagged'}</span>`
      : `<span style="color: var(--clean-text); font-size: 0.72rem;">✓ Routine</span>`;

    const formattedDate = t.timestamp.replace('T', ' ');

    row.innerHTML = `
      <td style="font-family: monospace; font-weight: 600;">${t.transaction_id}</td>
      <td style="font-size: 0.73rem;">${formattedDate}</td>
      <td>
        <div style="font-weight: 500; color: var(--text-main);">${t.payee}</div>
        <div style="font-size: 0.7rem; color: var(--text-dim);">${t.description}</div>
      </td>
      <td><span class="${channelClass}">${t.channel}</span></td>
      <td class="txn-amount">$${t.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
      <td>${statusHtml}</td>
    `;

    el.txnTableBody.appendChild(row);
  });
}

// Copy Report
function copyReportToClipboard() {
  if (!state.activeAnalysisResult?.llm_report) {
    showToast('No report available to copy.');
    return;
  }
  navigator.clipboard.writeText(state.activeAnalysisResult.llm_report)
    .then(() => showToast('📋 Investigation Report copied to clipboard!'))
    .catch(() => showToast('Failed to copy report.'));
}

// Toggle Raw JSON vs Markdown View
function toggleRawView() {
  state.isRawView = !state.isRawView;
  if (state.isRawView) {
    el.reportContent.style.display = 'none';
    el.reportRawJson.style.display = 'block';
    showToast('Switched to Raw Findings JSON view.');
  } else {
    el.reportContent.style.display = 'block';
    el.reportRawJson.style.display = 'none';
    showToast('Switched to Formatted AI Report view.');
  }
}

// Fetch Benchmark Test Fixtures
async function fetchTestFixtures() {
  try {
    const res = await fetch('/api/test-fixtures');
    const data = await res.json();
    state.testFixtures = data.test_cases || [];
    renderBenchmarkGrid();
  } catch (err) {
    console.error('Error fetching test fixtures:', err);
  }
}

// Switch between Benchmark Suite (Tab 1) and Custom JSON (Tab 2)
function switchSandboxTab(tab) {
  const isBenchmarks = tab === 'BENCHMARKS';
  
  if (el.tabBenchmarks) {
    el.tabBenchmarks.classList.toggle('active', isBenchmarks);
    el.tabBenchmarks.style.background = isBenchmarks ? 'linear-gradient(135deg, #4f46e5, #0ea5e9)' : 'rgba(255, 255, 255, 0.04)';
    el.tabBenchmarks.style.color = isBenchmarks ? '#ffffff' : '#94a3b8';
    el.tabBenchmarks.style.border = isBenchmarks ? '1px solid transparent' : '1px solid rgba(255, 255, 255, 0.08)';
    el.tabBenchmarks.style.boxShadow = isBenchmarks ? '0 4px 14px rgba(79, 70, 229, 0.4)' : 'none';
  }
  
  if (el.tabCustomJson) {
    el.tabCustomJson.classList.toggle('active', !isBenchmarks);
    el.tabCustomJson.style.background = !isBenchmarks ? 'linear-gradient(135deg, #4f46e5, #0ea5e9)' : 'rgba(255, 255, 255, 0.04)';
    el.tabCustomJson.style.color = !isBenchmarks ? '#ffffff' : '#94a3b8';
    el.tabCustomJson.style.border = !isBenchmarks ? '1px solid transparent' : '1px solid rgba(255, 255, 255, 0.08)';
    el.tabCustomJson.style.boxShadow = !isBenchmarks ? '0 4px 14px rgba(79, 70, 229, 0.4)' : 'none';
  }

  if (el.viewBenchmarks) el.viewBenchmarks.style.display = isBenchmarks ? 'block' : 'none';
  if (el.viewCustomJson) el.viewCustomJson.style.display = isBenchmarks ? 'none' : 'block';
  if (el.btnRunSandboxAnalysis) el.btnRunSandboxAnalysis.style.display = isBenchmarks ? 'none' : 'inline-block';
}

// Render 1-Click Benchmark Scenario Cards Grouped by Logical Category
function renderBenchmarkGrid() {
  const container = el.benchmarkGridContainer || document.getElementById('benchmarkGridContainer') || document.getElementById('benchmarkGrid');
  if (!container) return;
  container.innerHTML = '';

  const verdictConfig = {
    'ATTENTION_REQUIRED': {
      cardClass: 'risk-attention',
      badgeClass: 'attention',
      borderColor: '#ef4444',
      badgeBg: 'rgba(239, 68, 68, 0.15)',
      badgeColor: '#f87171',
      badgeBorder: 'rgba(239, 68, 68, 0.35)',
      label: '⚠️ ATTENTION REQUIRED'
    },
    'NOTHING_FLAGGED': {
      cardClass: 'risk-clean',
      badgeClass: 'clean',
      borderColor: '#10b981',
      badgeBg: 'rgba(16, 185, 129, 0.15)',
      badgeColor: '#34d399',
      badgeBorder: 'rgba(16, 185, 129, 0.35)',
      label: '✅ NOTHING FLAGGED'
    },
    'INSUFFICIENT_EVIDENCE': {
      cardClass: 'risk-insufficient',
      badgeClass: 'insufficient',
      borderColor: '#f59e0b',
      badgeBg: 'rgba(245, 158, 11, 0.15)',
      badgeColor: '#fbbf24',
      badgeBorder: 'rgba(245, 158, 11, 0.35)',
      label: '⏳ INSUFFICIENT EVIDENCE'
    }
  };

  const categories = [
    {
      id: 'ANOMALIES',
      title: '🚨 High-Risk Behavioral Anomalies',
      subtitle: 'Triggers multi-vector deterministic rules & elevated risk scores (Urgency Index)',
      filter: fix => fix.expected_verdict === 'ATTENTION_REQUIRED'
    },
    {
      id: 'CLEAN',
      title: '✅ Normal Baseline Adherence Control',
      subtitle: 'Routine customer accounts conforming strictly to established spending and temporal baseline',
      filter: fix => fix.expected_verdict === 'NOTHING_FLAGGED'
    },
    {
      id: 'EDGE_CASES',
      title: '⏳ Data Quality & Cold-Start Limits',
      subtitle: 'Sparse and empty account records with insufficient baseline history (< 5 transactions)',
      filter: fix => fix.expected_verdict === 'INSUFFICIENT_EVIDENCE'
    }
  ];

  categories.forEach((cat) => {
    const items = state.testFixtures.filter(cat.filter);
    if (items.length === 0) return;

    const section = document.createElement('div');
    section.style.marginBottom = '20px';

    section.innerHTML = `
      <div class="benchmark-category-header" style="display: flex; align-items: center; justify-content: space-between; margin-top: 14px; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
        <div class="benchmark-category-title" style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; display: flex; align-items: center; gap: 8px; color: #e2e8f0;">
          <span>${cat.title}</span>
          <span style="font-size: 0.72rem; color: #94a3b8; font-weight: 400; text-transform: none;">— ${cat.subtitle}</span>
        </div>
        <span class="benchmark-category-count" style="font-size: 0.7rem; background: rgba(255, 255, 255, 0.08); padding: 3px 10px; border-radius: 12px; color: #cbd5e1; font-weight: 600;">
          ${items.length} Test Case${items.length > 1 ? 's' : ''}
        </span>
      </div>
      <div class="benchmark-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 12px;"></div>
    `;

    const grid = section.querySelector('.benchmark-grid');

    items.forEach((fix) => {
      const card = document.createElement('div');
      card.className = `benchmark-card ${fix.expected_verdict}`;

      const cfg = verdictConfig[fix.expected_verdict] || {
        borderColor: '#38bdf8',
        badgeBg: 'rgba(56, 189, 248, 0.15)',
        badgeColor: '#38bdf8',
        badgeBorder: 'rgba(56, 189, 248, 0.35)',
        label: fix.expected_verdict
      };

      const cleanCaseTitle = fix.case_id
        .replace(/^TEST_CASE_\d+_/, '')
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/\b\w/g, l => l.toUpperCase());

      card.setAttribute('style', `
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid ${cfg.borderColor};
        border-radius: 10px;
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
      `);

      card.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
            <div style="font-size: 0.86rem; font-weight: 700; color: #f8fafc; line-height: 1.3;">${cleanCaseTitle}</div>
            <span style="background: ${cfg.badgeBg}; color: ${cfg.badgeColor}; border: 1px solid ${cfg.badgeBorder}; padding: 3px 8px; border-radius: 4px; font-size: 0.67rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;">
              ${cfg.label}
            </span>
          </div>
          <div style="font-size: 0.74rem; color: #94a3b8; display: flex; align-items: center; gap: 6px;">
            <span>👤 <strong>${fix.customer_name}</strong></span>
            <span>•</span>
            <code style="color: var(--accent-blue); background: rgba(56, 189, 248, 0.1); padding: 1px 5px; border-radius: 3px;">${fix.customer_id}</code>
          </div>
          <div style="font-size: 0.77rem; color: #cbd5e1; line-height: 1.4; background: rgba(0, 0, 0, 0.3); padding: 8px 10px; border-radius: 6px; margin-top: 2px;">
            ${fix.description}
          </div>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 6px;">
          <button class="btn-benchmark-run" style="flex: 1.3; background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; border: none; padding: 8px 14px; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);">
            ⚡ Run Test Instantly
          </button>
          <button class="btn-benchmark-inspect" style="flex: 1; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.14); color: #cbd5e1; padding: 8px 12px; border-radius: 6px; font-size: 0.76rem; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 4px;">
            📝 Inspect JSON
          </button>
        </div>
      `;

      // 1-Click Instant Execution
      const runBtn = card.querySelector('.btn-benchmark-run');
      runBtn.addEventListener('click', async () => {
        closeSandboxModal();
        showToast(`⚡ Executing ${fix.customer_name} benchmark...`);
        await selectCustomer(fix.customer_id);
      });

      // Inspect / Edit JSON in Tab 2
      const inspectBtn = card.querySelector('.btn-benchmark-inspect');
      inspectBtn.addEventListener('click', async () => {
        await loadPresetIntoSandbox(fix);
        switchSandboxTab('CUSTOM');
      });

      grid.appendChild(card);
    });

    container.appendChild(section);
  });
}

// Load testcase payload into Custom JSON editor
async function loadPresetIntoSandbox(fix) {
  try {
    const res = await fetch(`/api/customers/${fix.customer_id}/transactions`);
    const data = await res.json();
    const txns = data.transactions || [];
    const flaggedIds = new Set(fix.sample_transaction_ids || []);

    let hist, obs;
    if (flaggedIds.size > 0) {
      obs = txns.filter(t => flaggedIds.has(t.transaction_id));
      hist = txns.filter(t => !flaggedIds.has(t.transaction_id));
    } else if (txns.length >= 5) {
      obs = txns.slice(-2);
      hist = txns.slice(0, -2);
    } else {
      hist = txns;
      obs = [];
    }

    const payload = {
      scenario_description: fix.description,
      customer_profile: {
        customer_id: fix.customer_id,
        name: fix.customer_name,
        account_type: "Standard Checking",
        account_number: "ACC-CUSTOM-001"
      },
      historical_transactions: hist,
      observed_transactions: obs
    };
    el.sandboxPayloadText.value = JSON.stringify(payload, null, 2);
    showToast(`Loaded ${fix.customer_name} payload into editor.`);
  } catch (err) {
    showToast('Could not load preset data.');
  }
}

// Auto-Format and Syntax-Clean JSON
function formatSandboxJson() {
  let raw = (el.sandboxPayloadText.value || '').trim();
  if (!raw) {
    showToast('⚠️ JSON editor is empty.');
    return;
  }
  if (raw.includes('```json')) {
    raw = raw.split('```json')[1].split('```')[0].trim();
  } else if (raw.includes('```')) {
    raw = raw.split('```')[1].split('```')[0].trim();
  }
  try {
    const parsed = JSON.parse(raw);
    el.sandboxPayloadText.value = JSON.stringify(parsed, null, 2);
    showToast('✨ JSON formatted successfully!');
  } catch (err) {
    showToast('❌ JSON parse error: ' + err.message);
  }
}

// Load Default Alex Mercer Sample
function loadDefaultSampleTemplate() {
  const sample = {
    customer_profile: {
      customer_id: "CUST-DEMO-999",
      name: "Alex Mercer",
      account_type: "Personal Checking",
      account_number: "ACC-99201948",
      known_payees: ["Local Supermarket", "Metro Fuel", "Neighborhood Cafe"],
      common_channels: ["POS", "Mobile"]
    },
    historical_transactions: [
      {
        transaction_id: "HIST-01",
        customer_id: "CUST-DEMO-999",
        timestamp: "2026-08-01T10:00:00",
        description: "Groceries",
        payee: "Local Supermarket",
        amount: 45.00,
        channel: "POS"
      },
      {
        transaction_id: "HIST-02",
        customer_id: "CUST-DEMO-999",
        timestamp: "2026-08-02T11:30:00",
        description: "Fuel",
        payee: "Metro Fuel",
        amount: 52.50,
        channel: "POS"
      },
      {
        transaction_id: "HIST-03",
        customer_id: "CUST-DEMO-999",
        timestamp: "2026-08-03T12:15:00",
        description: "Lunch",
        payee: "Neighborhood Cafe",
        amount: 38.00,
        channel: "Mobile"
      },
      {
        transaction_id: "HIST-04",
        customer_id: "CUST-DEMO-999",
        timestamp: "2026-08-04T09:45:00",
        description: "Groceries",
        payee: "Local Supermarket",
        amount: 60.00,
        channel: "POS"
      },
      {
        transaction_id: "HIST-05",
        customer_id: "CUST-DEMO-999",
        timestamp: "2026-08-05T13:00:00",
        description: "Coffee",
        payee: "Neighborhood Cafe",
        amount: 35.50,
        channel: "Mobile"
      }
    ],
    observed_transactions: [
      {
        transaction_id: "TXN-ANOMALOUS-01",
        customer_id: "CUST-DEMO-999",
        timestamp: "2026-08-06T03:42:00",
        description: "Urgent High Value Wire",
        payee: "Unknown Offshore Crypto",
        amount: 8950.00,
        channel: "Wire"
      }
    ]
  };
  el.sandboxPayloadText.value = JSON.stringify(sample, null, 2);
  showToast('📋 Loaded Alex Mercer sample payload.');
}

// File Upload Handlers
function handleFileUpload(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  readFileIntoSandbox(file);
}

function handleFileDrop(e) {
  e.preventDefault();
  if (el.uploadDropZone) el.uploadDropZone.classList.remove('drag-over');
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    readFileIntoSandbox(e.dataTransfer.files[0]);
  }
}

function readFileIntoSandbox(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    el.sandboxPayloadText.value = e.target.result;
    formatSandboxJson();
    switchSandboxTab('CUSTOM');
    showToast(`📁 Loaded: ${file.name}`);
  };
  reader.onerror = () => {
    showToast('❌ Error reading file.');
  };
  reader.readAsText(file);
}

function openSandboxModal() {
  switchSandboxTab('BENCHMARKS');
  if (!el.sandboxPayloadText.value) {
    loadDefaultSampleTemplate();
  }
  el.sandboxModal.classList.add('open');
}

function closeSandboxModal() {
  el.sandboxModal.classList.remove('open');
}

// Run Sandbox Analysis
async function runSandboxAnalysis() {
  try {
    let raw = (el.sandboxPayloadText.value || '').trim();
    if (!raw) {
      showToast('❌ Please provide a JSON payload.');
      return;
    }

    // Auto-clean if wrapped in markdown codeblocks or leading prompt commentary
    if (raw.includes('```json')) {
      raw = raw.split('```json')[1].split('```')[0].trim();
    } else if (raw.includes('```')) {
      raw = raw.split('```')[1].split('```')[0].trim();
    } else {
      const firstBrace = raw.indexOf('{');
      const firstBracket = raw.indexOf('[');
      let startIdx = -1;
      let isArray = false;

      if (firstBrace !== -1 && (firstBracket === -1 || firstBrace < firstBracket)) {
        startIdx = firstBrace;
      } else if (firstBracket !== -1) {
        startIdx = firstBracket;
        isArray = true;
      }

      if (startIdx !== -1) {
        const endChar = isArray ? ']' : '}';
        const endIdx = raw.lastIndexOf(endChar);
        if (endIdx > startIdx) {
          raw = raw.substring(startIdx, endIdx + 1);
        }
      }
    }

    let jsonPayload;
    try {
      jsonPayload = JSON.parse(raw);
    } catch (parseErr) {
      showToast('❌ Invalid JSON syntax: ' + parseErr.message);
      el.sandboxPayloadText.style.borderColor = 'var(--risk-high-text)';
      setTimeout(() => {
        el.sandboxPayloadText.style.borderColor = '';
      }, 3000);
      return;
    }

    // If user passed a top-level array of transactions: [ {...}, {...} ]
    if (Array.isArray(jsonPayload)) {
      if (jsonPayload.length >= 6) {
        jsonPayload = {
          historical_transactions: jsonPayload.slice(0, -1),
          observed_transactions: jsonPayload.slice(-1)
        };
      } else {
        jsonPayload = {
          transactions: jsonPayload
        };
      }
    }
    
    closeSandboxModal();
    el.reportLoadingState.style.display = 'flex';
    el.reportContent.style.display = 'none';

    const res = await fetch('/api/analyze/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jsonPayload)
    });

    const result = await res.json();
    if (!res.ok) {
      const errDetail = Array.isArray(result.detail)
        ? result.detail.map(d => `${d.loc ? d.loc.slice(-1).join('') : ''}: ${d.msg}`).join('; ')
        : (result.detail || 'Analysis request failed.');
      showToast(`❌ Error (${res.status}): ${errDetail}`);
      el.reportLoadingState.style.display = 'none';
      el.sandboxModal.classList.add('open');
      return;
    }

    state.activeAnalysisResult = result;
    state.activeCustomerId = result.customer_id;

    // Collect all transactions for table view: observed transactions first, then historical
    const obsTxns = jsonPayload.observed_transactions || [];
    const histTxns = jsonPayload.historical_transactions || [];
    const legacyTxns = jsonPayload.transactions || [];
    const allTxns = obsTxns.length > 0 ? [...obsTxns, ...histTxns] : (legacyTxns.length > 0 ? legacyTxns : histTxns);

    // Track flagged transaction IDs from findings and cited transactions
    const flaggedIdSet = new Set((result.cited_transactions || []).map(t => t.transaction_id));
    if (result.findings) {
      result.findings.forEach(f => {
        const ids = f.cited_transactions || f.cited_transaction_ids || f.transaction_ids || [];
        ids.forEach(id => flaggedIdSet.add(id));
      });
    }

    state.activeTransactions = allTxns.map((t, idx) => {
      const tid = t.transaction_id || `CUSTOM-TXN-${idx + 1}`;
      const isFlagged = flaggedIdSet.has(tid);
      const reasons = (result.findings || [])
        .filter(f => {
          const ids = f.cited_transactions || f.cited_transaction_ids || f.transaction_ids || [];
          return ids.includes(tid);
        })
        .map(f => f.rule_name);
      return {
        ...t,
        transaction_id: tid,
        is_flagged: isFlagged,
        flag_reasons: reasons
      };
    });

    renderCustomerHeader(result);
    renderBaselineMetrics(result);
    renderInvestigationReport(result);
    renderTransactionTable();
    showToast('✅ Custom sandbox investigation completed!');

  } catch (err) {
    console.error('Error running sandbox analysis:', err);
    showToast('❌ Error: ' + err.message);
    el.reportLoadingState.style.display = 'none';
  }
}

// Toast Display Helper
function showToast(msg) {
  el.toastMsg.textContent = msg;
  el.toastMsg.style.display = 'block';
  setTimeout(() => {
    el.toastMsg.style.display = 'none';
  }, 3000);
}

// Kickoff
document.addEventListener('DOMContentLoaded', initApp);
