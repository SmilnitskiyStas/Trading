from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Trading Control Center</title>
  <style>
    :root {
      --bg: #f3efe6;
      --panel: rgba(255, 252, 246, 0.85);
      --ink: #1f2a2e;
      --muted: #5f6b6f;
      --line: rgba(31, 42, 46, 0.12);
      --accent: #d16b3b;
      --accent-2: #2f7d6c;
      --accent-3: #7c5c2c;
      --warn: #b45d2a;
      --ok: #2f7d6c;
      --shadow: 0 16px 45px rgba(64, 52, 37, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(209, 107, 59, 0.18), transparent 32%),
        radial-gradient(circle at top right, rgba(47, 125, 108, 0.18), transparent 28%),
        linear-gradient(180deg, #f9f5ee 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .shell {
      width: min(1360px, calc(100% - 32px));
      margin: 24px auto 40px;
    }
    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(255,255,255,0.88), rgba(250,244,234,0.92));
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: auto -60px -60px auto;
      width: 220px;
      height: 220px;
      background: radial-gradient(circle, rgba(209,107,59,0.24), transparent 65%);
    }
    h1, h2, button, textarea { font-family: "Trebuchet MS", Verdana, sans-serif; }
    h1 { margin: 0 0 8px; font-size: clamp(30px, 4vw, 52px); }
    .subtitle { margin: 0; color: var(--muted); max-width: 820px; line-height: 1.5; }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
      align-items: center;
    }
    button {
      border: 0;
      padding: 12px 18px;
      background: var(--ink);
      color: white;
      cursor: pointer;
      letter-spacing: 0.02em;
    }
    button.secondary { background: var(--accent-2); }
    button.tertiary { background: var(--accent-3); }
    button.warn { background: var(--warn); }
    button:disabled { opacity: 0.55; cursor: wait; }
    textarea {
      width: min(360px, 100%);
      min-height: 52px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.65);
      color: var(--ink);
      resize: vertical;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: rgba(31,42,46,0.06);
      border: 1px solid var(--line);
      font-family: "Trebuchet MS", Verdana, sans-serif;
      font-size: 14px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
      margin-top: 18px;
    }
    .card {
      grid-column: span 12;
      background: var(--panel);
      backdrop-filter: blur(8px);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 18px;
    }
    .card.half { grid-column: span 6; }
    .card.third { grid-column: span 4; }
    .card.quarter { grid-column: span 3; }
    .card h2 { margin: 0 0 14px; font-size: 18px; }
    .metric {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .metric-item {
      padding: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.55);
    }
    .metric-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .metric-value {
      margin-top: 8px;
      font-family: "Trebuchet MS", Verdana, sans-serif;
      font-size: 22px;
    }
    .list {
      display: grid;
      gap: 10px;
    }
    .list-item {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.5);
      padding: 12px;
    }
    .list-item strong { font-family: "Trebuchet MS", Verdana, sans-serif; }
    .muted { color: var(--muted); }
    .ok { color: var(--ok); }
    .warn-text { color: var(--warn); }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.5;
    }
    @media (max-width: 960px) {
      .card.half, .card.third, .card.quarter { grid-column: span 12; }
      .metric { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Trading Control Center</h1>
      <p class="subtitle">Live MVP dashboard for the paper-trading bot. It watches health, automation, kill-switch state, symbol-specific routing, account performance, and operational events from one screen.</p>
      <div class="toolbar">
        <button id="refreshBtn">Refresh Snapshot</button>
        <button id="runBtn" class="secondary">Run Automation Now</button>
        <button id="pauseBtn" class="tertiary">Pause</button>
        <button id="resumeBtn" class="secondary">Resume</button>
        <button id="stopBtn" class="warn">Stop</button>
        <button id="killOnBtn" class="warn">Engage Kill Switch</button>
        <button id="killOffBtn" class="secondary">Release Kill Switch</button>
        <textarea id="killReason" placeholder="Reason for emergency stop...">Manual emergency stop from dashboard.</textarea>
        <span class="badge" id="lastRefresh">Waiting for first refresh...</span>
      </div>
    </section>

    <section class="grid">
      <article class="card third"><h2>Health</h2><div id="health" class="metric"></div></article>
      <article class="card third"><h2>Automation</h2><div id="automation" class="metric"></div></article>
      <article class="card third"><h2>Kill Switch</h2><div id="killSwitch" class="metric"></div></article>
      <article class="card half"><h2>Paper Test Mode</h2><div id="paperTestMode" class="metric"></div><div id="paperTestSummary" class="list" style="margin-top:12px;"></div></article>
      <article class="card half"><h2>Launch Guidance</h2><div id="launchGuidance" class="list"></div></article>

      <article class="card third"><h2>ML Gate</h2><div id="mlGate" class="metric"></div></article>
      <article class="card third"><h2>BTC ML Risk Check</h2><div id="btcMlRiskCheck" class="metric"></div></article>
      <article class="card third"><h2>ETH Risk Check</h2><div id="ethMlRiskCheck" class="metric"></div></article>
      <article class="card half"><h2>BTC ML Model</h2><div id="btcMl" class="list"></div></article>
      <article class="card half"><h2>ETH ML Model</h2><div id="ethMl" class="list"></div></article>

      <article class="card quarter"><h2>Account</h2><div id="account" class="metric"></div></article>
      <article class="card quarter"><h2>Return</h2><div id="perfReturn" class="metric"></div></article>
      <article class="card quarter"><h2>Trades</h2><div id="perfTrades" class="metric"></div></article>
      <article class="card quarter"><h2>Edge</h2><div id="perfEdge" class="metric"></div></article>

      <article class="card half"><h2>BTC Route</h2><div id="btcRoute" class="list"></div></article>
      <article class="card half"><h2>ETH Route</h2><div id="ethRoute" class="list"></div></article>

      <article class="card half"><h2>Performance By Symbol</h2><div id="symbolPerf" class="list"></div></article>
      <article class="card half"><h2>Performance By Day</h2><div id="dayPerf" class="list"></div></article>

      <article class="card half"><h2>Recent Trades</h2><div id="trades" class="list"></div></article>
      <article class="card half"><h2>Recent Events</h2><div id="events" class="list"></div></article>

      <article class="card"><h2>Latest Automation Cycle</h2><pre id="automationCycle">No cycle data yet.</pre></article>
    </section>
  </div>

  <script>
    const qs = (id) => document.getElementById(id);

    function metricCard(items) {
      return items.map(([label, value, extraClass]) => `
        <div class="metric-item">
          <div class="metric-label">${label}</div>
          <div class="metric-value ${extraClass || ""}">${value}</div>
        </div>
      `).join("");
    }

    function listCard(items) {
      if (!items.length) return '<div class="list-item muted">No data yet.</div>';
      return items.map((item) => `<div class="list-item">${item}</div>`).join("");
    }

    async function getJson(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        throw new Error(`${url} -> ${response.status}`);
      }
      return await response.json();
    }

    async function getJsonSafe(url, options) {
      try {
        return await getJson(url, options);
      } catch (error) {
        return { __error: String(error) };
      }
    }

    async function postControl(path, body) {
      await getJson(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined
      });
      await refresh();
    }

    function setControlButtons(automation, killSwitch) {
      qs('pauseBtn').disabled = automation.mode !== 'running' || automation.is_running;
      qs('resumeBtn').disabled = automation.mode === 'running';
      qs('stopBtn').disabled = automation.mode === 'stopped' && !automation.is_running;
      qs('runBtn').disabled = automation.is_running;
      qs('killOnBtn').disabled = killSwitch.enabled;
      qs('killOffBtn').disabled = !killSwitch.enabled;
    }

    async function refresh() {
      const [health, automation, killSwitch, testStatus, account, performance, dailyPerf, symbolPerf, trades, events, btc, eth, btcModels, ethModels, btcMlPredict, btcRisk, ethRisk] = await Promise.all([
        getJson('/health'),
        getJson('/api/v1/automation/status'),
        getJson('/api/v1/automation/kill-switch'),
        getJson('/api/v1/paper-trading/test-status?account_name=paper-main'),
        getJson('/api/v1/paper-trading/account?account_name=paper-main'),
        getJson('/api/v1/paper-trading/performance?account_name=paper-main'),
        getJson('/api/v1/paper-trading/performance/by-day?account_name=paper-main'),
        getJson('/api/v1/paper-trading/performance/by-symbol?account_name=paper-main'),
        getJson('/api/v1/paper-trading/trades?account_name=paper-main&limit=8'),
        getJson('/api/v1/events?limit=8'),
        getJson('/api/v1/strategy/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ exchange: 'binance', symbol: 'BTC/USDT', timeframe: '1h', limit: 300 })
        }),
        getJson('/api/v1/strategy/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ exchange: 'binance', symbol: 'ETH/USDT', timeframe: '1h', limit: 300 })
        }),
        getJsonSafe('/api/v1/ml/models?symbol=BTC/USDT&timeframe=1h'),
        getJsonSafe('/api/v1/ml/models?symbol=ETH/USDT&timeframe=1h'),
        getJsonSafe('/api/v1/ml/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ exchange: 'binance', symbol: 'BTC/USDT', timeframe: '1h', limit: 300 })
        }),
        getJson('/api/v1/risk/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            exchange: 'binance',
            symbol: 'BTC/USDT',
            timeframe: '1h',
            limit: 300,
            account_balance: 1000,
            current_daily_loss_percent: 0,
            current_drawdown_percent: 0,
            open_positions_count: 0,
            has_open_position_for_symbol: false,
            market_data_is_fresh: true,
            exchange_api_healthy: true
          })
        }),
        getJson('/api/v1/risk/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            exchange: 'binance',
            symbol: 'ETH/USDT',
            timeframe: '1h',
            limit: 300,
            account_balance: 1000,
            current_daily_loss_percent: 0,
            current_drawdown_percent: 0,
            open_positions_count: 0,
            has_open_position_for_symbol: false,
            market_data_is_fresh: true,
            exchange_api_healthy: true
          })
        }),
      ]);

      qs('health').innerHTML = metricCard([
        ['System', health.status, health.status === 'ok' ? 'ok' : 'warn-text'],
        ['Database', health.services.database.status, health.services.database.status === 'ok' ? 'ok' : 'warn-text'],
        ['Redis', health.services.redis.status, health.services.redis.status === 'ok' ? 'ok' : 'warn-text'],
        ['Env', health.environment, ''],
      ]);

      qs('automation').innerHTML = metricCard([
        ['Mode', automation.mode || 'n/a', automation.mode === 'running' ? 'ok' : 'warn-text'],
        ['Running', String(automation.is_running), automation.is_running ? 'warn-text' : 'ok'],
        ['Loop', `${automation.loop_interval_seconds}s`, ''],
        ['Control', automation.last_control_action || 'none', ''],
      ]);

      qs('killSwitch').innerHTML = metricCard([
        ['Enabled', String(killSwitch.enabled), killSwitch.enabled ? 'warn-text' : 'ok'],
        ['Reason', killSwitch.reason || 'none', ''],
        ['Updated', killSwitch.updated_at || 'n/a', ''],
        ['Impact', killSwitch.enabled ? 'New entries blocked' : 'Entries allowed', killSwitch.enabled ? 'warn-text' : 'ok'],
      ]);

      qs('paperTestMode').innerHTML = metricCard([
        ['Phase', testStatus.phase, testStatus.phase === 'EVALUATING' ? 'ok' : 'warn-text'],
        ['PnL Status', testStatus.pnl_status, testStatus.pnl_status === 'PROFITABLE' ? 'ok' : (testStatus.pnl_status === 'UNPROFITABLE' ? 'warn-text' : '')],
        ['Return %', testStatus.realized_return_percent, Number(testStatus.realized_return_percent) >= 0 ? 'ok' : 'warn-text'],
        ['Closed Trades', testStatus.closed_trades, Number(testStatus.closed_trades) >= 5 ? 'ok' : 'warn-text'],
      ]);

      qs('paperTestSummary').innerHTML = listCard([
        `<strong>Summary</strong><br>${testStatus.summary}`,
        `<strong>Current Balance</strong>: ${testStatus.current_balance}<br><strong>Realized PnL</strong>: ${testStatus.realized_pnl}<br><strong>Days With Closed Trades</strong>: ${testStatus.days_with_closed_trades}`,
        `<strong>Last Closed Trade</strong>: ${testStatus.last_closed_trade_at || 'none yet'}<br><strong>Last Trade PnL</strong>: ${testStatus.last_closed_trade_pnl || 'n/a'}`
      ]);

      const launchSteps = [
        automation.mode === 'running' ? 'Automation is enabled and ready to keep collecting paper-trading data.' : 'Automation is not in running mode. Resume it before judging performance.',
        killSwitch.enabled ? 'Kill switch is engaged, so new entries are blocked. Release it to continue testing.' : 'Kill switch is released, so the bot can continue paper entries.',
        testStatus.ready_for_evaluation ? 'There is enough closed-trade history to start judging whether the setup is profitable or not.' : 'The sample is still small. Let the bot collect more closed trades before making decisions.',
        Number(testStatus.realized_pnl) >= 0 ? 'Current realized result is non-negative.' : 'Current realized result is negative, so this setup needs more observation or tuning.',
      ];
      qs('launchGuidance').innerHTML = listCard(
        launchSteps.map((item) => `<strong>Step</strong><br>${item}`)
      );

      const btcMlModel = Array.isArray(btcModels) && btcModels.length ? btcModels[0] : null;
      const ethMlModel = Array.isArray(ethModels) && ethModels.length ? ethModels[0] : null;
      const btcMlPredictionOk = !btcMlPredict.__error;

      qs('mlGate').innerHTML = metricCard([
        ['Enabled', 'true', 'ok'],
        ['Symbols', 'BTC/USDT', ''],
        ['Require Model', 'false', ''],
        ['BTC Model', btcMlModel ? btcMlModel.algorithm : 'not found', btcMlModel ? 'ok' : 'warn-text'],
      ]);

      qs('btcMlRiskCheck').innerHTML = metricCard([
        ['Strategy', btcRisk.strategy.signal, btcRisk.strategy.signal === 'BUY' ? 'ok' : 'warn-text'],
        ['ML Gate', btcRisk.ml_filter ? (btcRisk.ml_filter.available ? 'active' : 'skipped') : 'off', btcRisk.ml_filter && btcRisk.ml_filter.available ? 'ok' : 'warn-text'],
        ['ML Advisory', btcRisk.ml_filter && btcRisk.ml_filter.advisory_signal ? btcRisk.ml_filter.advisory_signal : 'n/a', btcRisk.ml_filter && btcRisk.ml_filter.advisory_signal === 'UP' ? 'ok' : 'warn-text'],
        ['Allowed', String(btcRisk.allowed), btcRisk.allowed ? 'ok' : 'warn-text'],
      ]);

      qs('ethMlRiskCheck').innerHTML = metricCard([
        ['Strategy', ethRisk.strategy.signal, ethRisk.strategy.signal === 'BUY' ? 'ok' : 'warn-text'],
        ['ML Gate', ethRisk.ml_filter ? (ethRisk.ml_filter.available ? 'active' : 'skipped') : 'off', ethRisk.ml_filter ? 'warn-text' : 'ok'],
        ['ML Advisory', ethRisk.ml_filter && ethRisk.ml_filter.advisory_signal ? ethRisk.ml_filter.advisory_signal : 'n/a', ''],
        ['Allowed', String(ethRisk.allowed), ethRisk.allowed ? 'ok' : 'warn-text'],
      ]);

      qs('account').innerHTML = metricCard([
        ['Account', account.name, ''],
        ['Initial', account.initial_balance, ''],
        ['Current', account.current_balance, ''],
        ['Active', String(account.is_active), account.is_active ? 'ok' : 'warn-text'],
      ]);

      qs('perfReturn').innerHTML = metricCard([
        ['Return %', performance.realized_return_percent, Number(performance.realized_return_percent) >= 0 ? 'ok' : 'warn-text'],
        ['Profit Factor', performance.profit_factor, Number(performance.profit_factor) >= 1 ? 'ok' : 'warn-text'],
      ]);

      qs('perfTrades').innerHTML = metricCard([
        ['Total', performance.total_trades, ''],
        ['Closed', performance.closed_trades, ''],
        ['Open', performance.open_trades, ''],
        ['Win Rate %', performance.win_rate_percent, Number(performance.win_rate_percent) >= 50 ? 'ok' : 'warn-text'],
      ]);

      qs('perfEdge').innerHTML = metricCard([
        ['Winners', performance.winning_trades, 'ok'],
        ['Losers', performance.losing_trades, 'warn-text'],
        ['Avg Win', performance.average_win, 'ok'],
        ['Avg Loss', performance.average_loss, 'warn-text'],
      ]);

      qs('btcRoute').innerHTML = listCard([
        `<strong>Strategy</strong>: ${btc.strategy_name}`,
        `<strong>Signal</strong>: ${btc.signal}`,
        `<strong>Close</strong>: ${btc.latest_close_price}`,
        `<strong>Reasons</strong><br>${btc.reasons.join('<br>')}`,
      ]);

      qs('ethRoute').innerHTML = listCard([
        `<strong>Strategy</strong>: ${eth.strategy_name}`,
        `<strong>Signal</strong>: ${eth.signal}`,
        `<strong>Close</strong>: ${eth.latest_close_price}`,
        `<strong>Reasons</strong><br>${eth.reasons.join('<br>')}`,
      ]);

      qs('btcMl').innerHTML = listCard([
        btcMlModel
          ? `<strong>Model</strong>: ${btcMlModel.model_id}<br><strong>Algorithm</strong>: ${btcMlModel.algorithm}<br><strong>Trained</strong>: ${btcMlModel.trained_at}<br><strong>Rows</strong>: ${btcMlModel.dataset_rows}<br><strong>Threshold</strong>: ${btcMlModel.confidence_threshold}`
          : `<strong>Model</strong>: not found<br><span class="muted">Train BTC 1h model to enable ML assistance.</span>`,
        btcMlPredictionOk
          ? `<strong>Advisory</strong>: ${btcMlPredict.advisory_signal}<br><strong>Probability Up</strong>: ${Number(btcMlPredict.probability_up).toFixed(3)}<br><strong>Confidence</strong>: ${Number(btcMlPredict.confidence).toFixed(3)}<br><strong>Passes Threshold</strong>: ${String(btcMlPredict.passes_confidence_threshold)}`
          : `<strong>Prediction</strong>: unavailable<br><span class="muted">${btcMlPredict.__error}</span>`,
      ]);

      qs('ethMl').innerHTML = listCard([
        ethMlModel
          ? `<strong>Model</strong>: ${ethMlModel.model_id}<br><strong>Algorithm</strong>: ${ethMlModel.algorithm}<br><strong>Trained</strong>: ${ethMlModel.trained_at}<br><strong>Rows</strong>: ${ethMlModel.dataset_rows}<br><strong>Threshold</strong>: ${ethMlModel.confidence_threshold}`
          : `<strong>Model</strong>: none active<br><span class="muted">ETH is currently outside the ML risk gate allowlist.</span>`,
        `<strong>ML Gate</strong>: disabled for ETH/USDT<br><span class="muted">Strategy and risk still run normally without ML confirmation.</span>`,
      ]);

      qs('symbolPerf').innerHTML = listCard(
        symbolPerf.map((row) => `
          <strong>${row.symbol}</strong><br>
          Closed trades: ${row.closed_trades}<br>
          Realized PnL: ${row.realized_pnl}<br>
          Win rate: ${row.win_rate_percent}<br>
          Profit factor: ${row.profit_factor}
        `)
      );

      qs('dayPerf').innerHTML = listCard(
        dailyPerf.map((row) => `
          <strong>${row.trading_day}</strong><br>
          Closed trades: ${row.closed_trades}<br>
          Realized PnL: ${row.realized_pnl}<br>
          Win rate: ${row.win_rate_percent}
        `)
      );

      qs('trades').innerHTML = listCard(
        trades.map((trade) => `
          <strong>${trade.strategy_name}</strong> - ${trade.status}<br>
          Entry: ${trade.entry_price}<br>
          Exit: ${trade.exit_price || 'open'}<br>
          PnL: ${trade.realized_pnl}
        `)
      );

      qs('events').innerHTML = listCard(
        events.map((event) => `
          <strong>${event.event_type}</strong> - ${event.level}<br>
          ${event.message}<br>
          <span class="muted">${event.created_at}</span>
        `)
      );

      qs('automationCycle').textContent = JSON.stringify(automation.last_cycle || {}, null, 2);
      qs('lastRefresh').textContent = `Last refresh: ${new Date().toLocaleString()}`;
      setControlButtons(automation, killSwitch);
    }

    qs('refreshBtn').addEventListener('click', refresh);
    qs('runBtn').addEventListener('click', async () => postControl('/api/v1/automation/run-once'));
    qs('pauseBtn').addEventListener('click', async () => postControl('/api/v1/automation/pause'));
    qs('resumeBtn').addEventListener('click', async () => postControl('/api/v1/automation/resume'));
    qs('stopBtn').addEventListener('click', async () => postControl('/api/v1/automation/stop'));
    qs('killOnBtn').addEventListener('click', async () => postControl('/api/v1/automation/kill-switch/enable', { reason: qs('killReason').value }));
    qs('killOffBtn').addEventListener('click', async () => postControl('/api/v1/automation/kill-switch/disable'));

    refresh();
    setInterval(refresh, 30000);
  </script>
</body>
</html>"""
