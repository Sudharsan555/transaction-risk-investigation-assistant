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
  presetsContainer: document.getElementById('presetsContainer'),
  sandboxPayloadText: document.getElementById('sandboxPayloadText'),
  
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
      el.modelStatusText.textContent = `🟢 Gemini 2.0 Flash Grounded`;
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
  const flagged = state.customers.filter(c => c.verdict === 'ATTENTION_REQUIRED' || c.verdict === 'ATTENTION NEEDED').length;
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
    const isFlagged = c.verdict === 'ATTENTION_REQUIRED' || c.verdict === 'ATTENTION NEEDED';
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
    
    const isFlagged = cust.verdict === 'ATTENTION_REQUIRED' || cust.verdict === 'ATTENTION NEEDED';
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

  const isAttention = result.verdict === 'ATTENTION_REQUIRED' || result.verdict === 'ATTENTION NEEDED';
  const isInsufficient = result.verdict === 'INSUFFICIENT_EVIDENCE' || result.evidence_status === 'INSUFFICIENT_EVIDENCE';

  if (isAttention) {
    el.customerVerdictBadge.className = 'verdict-large-badge attention';
    el.verdictIcon.textContent = '🚨';
    el.verdictText.textContent = 'ATTENTION REQUIRED';
    el.customerRiskScore.style.color = 'var(--risk-high-text)';
  } else if (isInsufficient) {
    el.customerVerdictBadge.className = 'verdict-large-badge insufficient';
    el.verdictIcon.textContent = 'ℹ️';
    el.verdictText.textContent = 'INSUFFICIENT EVIDENCE';
    el.customerRiskScore.style.color = '#facc15';
  } else {
    el.customerVerdictBadge.className = 'verdict-large-badge clean';
    el.verdictIcon.textContent = '🛡️';
    el.verdictText.textContent = 'NOTHING FLAGGED';
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
    renderSandboxPresets();
  } catch (err) {
    console.error('Error fetching test fixtures:', err);
  }
}

// Render Sandbox Preset Buttons
function renderSandboxPresets() {
  el.presetsContainer.innerHTML = '';
  state.testFixtures.forEach(fix => {
    const btn = document.createElement('button');
    btn.className = 'btn-fixture';
    btn.textContent = fix.customer_name + ` (${fix.expected_verdict})`;
    btn.title = fix.description;
    btn.addEventListener('click', () => loadPresetIntoSandbox(fix));
    el.presetsContainer.appendChild(btn);
  });
}

function loadPresetIntoSandbox(fix) {
  // If fixture corresponds to a known customer ID, load that customer's transactions
  fetch(`/api/customers/${fix.customer_id}/transactions`)
    .then(r => r.json())
    .then(data => {
      const payload = {
        customer_profile: {
          customer_id: fix.customer_id,
          name: fix.customer_name,
          account_type: "Checking",
          account_number: "ACC-CUSTOM-001",
          baseline_avg_amount: 100.0,
          baseline_std_amount: 40.0,
          baseline_max_normal: 300.0,
          baseline_active_hours: [8, 22],
          known_payees: ["Amazon", "Target", "Starbucks"],
          common_channels: ["POS", "Mobile"],
          total_transactions: data.transactions.length,
          total_volume: 5000.0
        },
        transactions: data.transactions
      };
      el.sandboxPayloadText.value = JSON.stringify(payload, null, 2);
      showToast(`Loaded ${fix.customer_name} fixture.`);
    })
    .catch(() => {
      showToast('Could not load preset data.');
    });
}

function openSandboxModal() {
  if (!el.sandboxPayloadText.value) {
    // Default template
    const sample = {
      customer_profile: {
        customer_id: "CUSTOM-001",
        name: "Arthur Pendelton",
        account_type: "Standard Checking",
        account_number: "ACC-99001122",
        baseline_avg_amount: 85.00,
        baseline_std_amount: 35.00,
        baseline_max_normal: 250.00,
        baseline_active_hours: [8, 21],
        known_payees: ["Supermarket", "Metro Card", "Utility Board"],
        common_channels: ["POS", "Mobile"]
      },
      transactions: [
        {
          "transaction_id": "CUSTOM-TXN-101",
          "timestamp": "2026-08-30T10:15:00",
          "description": "Weekly Groceries",
          "payee": "Supermarket",
          "amount": 75.50,
          "channel": "POS",
          "category": "Groceries"
        },
        {
          "transaction_id": "CUSTOM-TXN-102",
          "timestamp": "2026-08-30T03:30:00",
          "description": "High Value Outbound Wire",
          "payee": "Offshore Vault Pay",
          "amount": 12850.00,
          "channel": "Wire",
          "category": "Wire Transfer"
        }
      ]
    };
    el.sandboxPayloadText.value = JSON.stringify(sample, null, 2);
  }
  el.sandboxModal.classList.add('open');
}

function closeSandboxModal() {
  el.sandboxModal.classList.remove('open');
}

// Run Sandbox Analysis
async function runSandboxAnalysis() {
  try {
    const raw = el.sandboxPayloadText.value;
    const jsonPayload = JSON.parse(raw);
    
    closeSandboxModal();
    el.reportLoadingState.style.display = 'flex';
    el.reportContent.style.display = 'none';

    const res = await fetch('/api/analyze/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jsonPayload)
    });

    const result = await res.json();
    state.activeAnalysisResult = result;
    state.activeTransactions = jsonPayload.transactions.map((t, idx) => ({
      ...t,
      transaction_id: t.transaction_id || `CUSTOM-TXN-${idx+1}`,
      is_flagged: result.cited_transactions.some(ct => ct.transaction_id === (t.transaction_id || `CUSTOM-TXN-${idx+1}`)),
      flag_reasons: result.findings.filter(f => f.cited_transaction_ids.includes(t.transaction_id || `CUSTOM-TXN-${idx+1}`)).map(f => f.rule_name)
    }));

    renderCustomerHeader(result);
    renderBaselineMetrics(result);
    renderInvestigationReport(result);
    renderTransactionTable();
    showToast('✅ Custom sandbox investigation completed!');

  } catch (err) {
    console.error('Error running sandbox analysis:', err);
    showToast('Invalid JSON payload or evaluation error.');
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
