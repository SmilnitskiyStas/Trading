# PROJECT_PROMPT.md

# Проєкт: Crypto Trading Research Bot

## 1. Мета проєкту

Створити сервіс для аналізу криптовалютного ринку, тестування торгових стратегій, прогнозування ймовірності руху ціни за допомогою математичних індикаторів та ML-моделей, а також автоматичного виконання угод спочатку в режимі paper trading, а після довготривалого тестування — з можливістю обережного переходу до реальної торгівлі малими сумами.

Головна ціль першої версії — не заробіток, а створення безпечної дослідницької системи, яка дозволяє:

- збирати ринкові дані;
- рахувати технічні індикатори;
- тестувати стратегії на історії;
- запускати paper trading;
- логувати кожну дію бота;
- оцінювати прибутковість, ризики та стабільність стратегії;
- поступово додавати ML та AI-модулі.

> Важливо: система не повинна одразу торгувати реальними грошима. Перший реліз має працювати тільки в режимі симуляції / paper trading.

---

## 2. Основна ідея

Проєкт має бути побудований не як “AI, який сам вирішує купити або продати”, а як комплексна система:

```text
Market Data → Feature Engineering → Strategy / ML Signal → Risk Engine → Paper Execution → Logs → Analytics
```

AI-агент або LLM не повинен напряму відкривати угоди. Його краще використовувати для:

- аналізу новин;
- sentiment analysis;
- пояснення рішень системи;
- генерації ідей для нових стратегій;
- допомоги в аналізі результатів backtesting.

Критичні рішення щодо входу в позицію, розміру позиції, stop-loss, take-profit і закриття угод мають виконуватися детермінованим кодом.

---

## 3. Рекомендований технологічний стек

### Backend

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy або SQLModel
- Alembic для міграцій БД

### Дані та база

- PostgreSQL
- TimescaleDB для time-series даних
- Redis для кешу, черг і короткочасного стану

### ML / Data Science

- pandas
- numpy
- scikit-learn
- XGBoost
- LightGBM, опційно
- PyTorch або TensorFlow, тільки на пізніших етапах
- Optuna для підбору параметрів
- MLflow для трекінгу експериментів, опційно

### Технічні індикатори

- pandas-ta
- ta
- TA-Lib, якщо вдасться комфортно встановити

### Біржі та дані

- ccxt для роботи з Binance, Bybit, OKX та іншими біржами
- Binance API / Bybit API для OHLCV, trades, order book
- CoinGecko API для загальних ринкових даних
- Alternative.me API для Fear & Greed Index
- CryptoQuant / Glassnode / Santiment — опційно, для on-chain метрик

### Frontend

- React або Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts або TradingView Lightweight Charts

### DevOps

- Docker
- Docker Compose
- GitHub Actions, опційно
- Prometheus + Grafana для моніторингу
- Telegram Bot API для алертів

---

## 4. Загальна архітектура

```text
crypto-trading-bot/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── market_data/
│   │   │   ├── indicators/
│   │   │   ├── strategies/
│   │   │   ├── ml/
│   │   │   ├── risk/
│   │   │   ├── execution/
│   │   │   ├── backtesting/
│   │   │   └── notifications/
│   │   ├── schemas/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/ або app/
│   └── package.json
│
├── ml/
│   ├── notebooks/
│   ├── training/
│   ├── experiments/
│   ├── models/
│   └── datasets/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 5. Основні модулі системи

## 5.1 Market Data Service

Відповідає за отримання та збереження ринкових даних.

### Що збирати

- OHLCV:
  - open
  - high
  - low
  - close
  - volume
- trades
- order book snapshots
- funding rate, якщо використовуються ф’ючерси
- open interest, якщо доступно
- spread
- bid/ask imbalance

### Таймфрейми

Для старту краще використовувати:

- 1h
- 4h
- 1d

Не варто починати зі скальпінгу на 1m або 5m, бо там більше шуму, комісій, latency та slippage.

### Перші торгові пари

Для MVP:

- BTC/USDT
- ETH/USDT

Не потрібно стартувати з великої кількості монет.

---

## 5.2 Indicator Service

Модуль розрахунку математичних і технічних індикаторів.

### Базові індикатори для MVP

#### SMA — Simple Moving Average

```text
SMA = сума цін закриття за N періодів / N
```

Використання:

- визначення тренду;
- фільтр для входу;
- порівняння короткої та довгої середньої.

---

#### EMA — Exponential Moving Average

```text
EMA_today = Price_today * k + EMA_yesterday * (1 - k)
k = 2 / (N + 1)
```

Використання:

- швидше реагує на зміну ціни, ніж SMA;
- може використовуватися для EMA crossover.

---

#### RSI — Relative Strength Index

```text
RSI = 100 - 100 / (1 + RS)
RS = average gain / average loss
```

Типові рівні:

- RSI < 30 — актив може бути перепроданий;
- RSI > 70 — актив може бути перекуплений.

Але не можна використовувати RSI як єдиний сигнал.

---

#### MACD

```text
MACD = EMA(12) - EMA(26)
Signal = EMA(9) від MACD
Histogram = MACD - Signal
```

Використання:

- визначення зміни momentum;
- підтвердження тренду;
- фільтр для buy/sell сигналів.

---

#### Bollinger Bands

```text
Middle Band = SMA(N)
Upper Band = SMA(N) + K * Standard Deviation
Lower Band = SMA(N) - K * Standard Deviation
```

Зазвичай:

```text
N = 20
K = 2
```

Використання:

- оцінка волатильності;
- пошук моментів, коли ціна виходить за межі нормального діапазону.

---

#### ATR — Average True Range

```text
TR = max(
  high - low,
  abs(high - previous_close),
  abs(low - previous_close)
)
ATR = average(TR, N)
```

Використання:

- розрахунок stop-loss;
- оцінка волатильності;
- адаптивний position sizing.

---

#### VWAP — Volume Weighted Average Price

```text
VWAP = sum(price * volume) / sum(volume)
```

Використання:

- оцінка середньої ціни з урахуванням обсягу;
- фільтр для входу в позицію.

---

#### Volatility

```text
Return = ln(close_today / close_yesterday)
Volatility = standard deviation(Returns) * sqrt(N)
```

Використання:

- визначення ризику;
- фільтр для відключення стратегії під час надмірної волатильності.

---

## 5.3 Strategy Service

На першому етапі стратегія має бути rule-based.

### MVP-стратегія №1: RSI + EMA Trend Filter

Приклад логіки:

```text
BUY якщо:
- close > EMA(200)
- RSI < 35
- MACD histogram починає рости

SELL якщо:
- RSI > 65
- close < EMA(50)
- або спрацював stop-loss / take-profit
```

Це не гарантує прибуток, але це проста база для тестування всієї системи.

---

### MVP-стратегія №2: EMA Crossover

```text
BUY якщо EMA(20) перетинає EMA(50) знизу вверх
SELL якщо EMA(20) перетинає EMA(50) зверху вниз
```

Додаткові фільтри:

- торгувати тільки якщо ціна вище EMA(200);
- не торгувати при дуже низькому volume;
- не торгувати при надмірній волатильності.

---

## 5.4 Risk Management Service

Це один із найважливіших модулів.

### Обов’язкові правила для MVP

```text
1. Максимум 1-2% ризику на одну угоду.
2. Максимум 5% денного збитку.
3. Максимум 15-20% загального drawdown.
4. Не відкривати нову позицію, якщо вже є активна позиція по цій парі.
5. Не торгувати, якщо дані застарілі або API біржі працює нестабільно.
6. Усі угоди повинні мати stop-loss.
7. Усі угоди повинні логуватися.
```

### Position Sizing

Формула:

```text
Position Size = Account Risk / Trade Risk
```

Де:

```text
Account Risk = Balance * Risk Percent
Trade Risk = Entry Price - Stop Loss Price
```

Приклад:

```text
Balance = 1000 USDT
Risk Percent = 1%
Account Risk = 10 USDT
Entry = 100
Stop Loss = 95
Trade Risk = 5
Position Size = 10 / 5 = 2 одиниці активу
```

---

### Stop-Loss через ATR

```text
Stop Loss = Entry Price - ATR * multiplier
```

Для long-позиції:

```text
SL = Entry - ATR * 1.5 або 2
```

Для short-позиції:

```text
SL = Entry + ATR * 1.5 або 2
```

Для старту краще працювати тільки з long-позиціями на spot.

---

### Take-Profit

Простий варіант:

```text
Take Profit = Entry + Risk * 2
```

Тобто Risk/Reward = 1:2.

---

### Trailing Stop

Пізніший етап:

```text
Trailing Stop = Highest Price Since Entry - ATR * multiplier
```

---

## 5.5 Backtesting Service

Backtesting — це модуль, який перевіряє стратегію на історичних даних.

### Backtesting повинен враховувати

- комісію біржі;
- spread;
- slippage;
- затримку виконання;
- розмір позиції;
- stop-loss;
- take-profit;
- максимальний drawdown;
- кількість угод;
- win rate;
- profit factor;
- Sharpe ratio.

### Важливо

Не можна тестувати модель на тих самих даних, на яких вона навчалась.

Потрібно розділяти дані:

```text
Train data: 70%
Validation data: 15%
Test data: 15%
```

Для time series не можна перемішувати рядки випадково. Дані мають залишатися в хронологічному порядку.

---

## 5.6 Paper Trading Service

Paper trading — це режим, де бот поводиться так, ніби торгує реальними грошима, але угоди записуються тільки в базу.

### Що має симулюватися

- відкриття позиції;
- закриття позиції;
- комісія;
- slippage;
- баланс;
- P&L;
- stop-loss;
- take-profit;
- помилки біржі;
- затримка виконання.

### Мінімальна тривалість paper trading

Перед реальними грошима бажано мати:

```text
мінімум 2-3 місяці стабільного paper trading
```

Краще, якщо бот пройде різні фази ринку:

- ріст;
- падіння;
- боковик;
- висока волатильність.

---

## 5.7 ML Service

ML-модуль не потрібно робити першим. Спочатку потрібно побудувати збір даних, backtesting і paper trading.

### Перша ML-модель

Рекомендована модель для старту:

```text
XGBoost Classifier
```

### Чому XGBoost

- добре працює з табличними даними;
- не потребує GPU;
- швидко навчається;
- легше аналізувати, ніж нейромережу;
- підходить для фіч на основі індикаторів.

### Що прогнозувати

Не варто намагатися прогнозувати точну ціну.

Краще прогнозувати:

```text
ймовірність, що ціна через N свічок буде вище на X%
```

Наприклад:

```text
target = 1, якщо close через 4 години буде вище поточної ціни на 1.5%
target = 0, якщо ні
```

Або 3 класи:

```text
0 = sell / down
1 = hold / neutral
2 = buy / up
```

### Приклад features

```text
rsi_14
macd
macd_signal
macd_histogram
ema_20
ema_50
ema_200
close_above_ema_200
atr_14
volume_change
volatility_24h
return_1h
return_4h
return_24h
bollinger_position
vwap_distance
funding_rate
fear_greed_index
btc_dominance
order_book_imbalance
```

### ML pipeline

```text
1. Load historical OHLCV data
2. Calculate indicators
3. Generate features
4. Generate target
5. Split data chronologically
6. Train XGBoost
7. Validate
8. Test on unseen data
9. Save model
10. Use model in paper trading
```

---

## 5.8 AI Agent Service

AI-агент не повинен бути основою торгового рішення.

Його роль:

- аналіз новин;
- аналіз sentiment;
- генерація пояснення;
- summarization ринку;
- пошук аномалій;
- допомога в аналітиці результатів.

### Приклад використання

```text
ML model signal: BUY BTC/USDT confidence 78%
Risk engine: allowed
AI agent: explains why signal appeared and checks whether there are major negative news
Execution: paper trading engine opens simulated position
```

---

## 6. Джерела даних для ML

## 6.1 Біржові дані

### Binance API

Дані:

- OHLCV
- trades
- order book
- ticker
- volume

Підходить для MVP.

### Bybit API

Дані:

- OHLCV
- funding rate
- open interest
- derivatives data

Корисно для пізнішого етапу.

### ccxt

Бібліотека, яка дозволяє працювати з різними біржами через один інтерфейс.

Рекомендовано використовувати ccxt, щоб не прив’язуватися до однієї біржі.

---

## 6.2 Ринкові агрегатори

### CoinGecko

Можна використовувати для:

- ціни;
- market cap;
- volume;
- trending coins;
- dominance;
- загальної інформації по монетах.

### CoinMarketCap

Схожий функціонал, але часто потребує API key.

---

## 6.3 Sentiment та новини

### Fear & Greed Index

Джерело:

- alternative.me API

Фіча:

```text
fear_greed_index
```

Може використовуватися як додатковий ринковий sentiment.

### Новини

Можливі джерела:

- CryptoPanic
- NewsAPI
- RSS-стрічки CoinDesk, Cointelegraph, Decrypt

Важливо: новини краще не використовувати в першому MVP, щоб не ускладнювати систему.

---

## 6.4 On-chain метрики

Пізніший етап:

- Glassnode
- CryptoQuant
- Santiment

Можливі features:

```text
active_addresses
exchange_inflow
exchange_outflow
whale_transactions
miner_reserves
stablecoin_supply
```

Для MVP не обов’язково.

---

## 7. База даних

## 7.1 Основні таблиці

### exchanges

```text
id
name
api_base_url
is_active
created_at
updated_at
```

### trading_pairs

```text
id
exchange_id
symbol
base_asset
quote_asset
timeframe
is_active
created_at
updated_at
```

### candles

```text
id
exchange_id
symbol
timeframe
open_time
open
high
low
close
volume
close_time
created_at
```

Індекс:

```text
exchange_id + symbol + timeframe + open_time
```

### indicators

```text
id
symbol
timeframe
open_time
rsi_14
ema_20
ema_50
ema_200
macd
macd_signal
macd_histogram
atr_14
bb_upper
bb_middle
bb_lower
vwap
volatility
created_at
```

### strategies

```text
id
name
description
version
config_json
is_active
created_at
updated_at
```

### strategy_signals

```text
id
strategy_id
symbol
timeframe
signal_type
confidence
price
reason_json
created_at
```

### paper_trades

```text
id
strategy_id
symbol
side
entry_price
exit_price
quantity
stop_loss
take_profit
status
pnl
pnl_percent
fee
slippage
entry_time
exit_time
created_at
updated_at
```

### ml_models

```text
id
name
version
model_type
features_json
metrics_json
model_path
is_active
created_at
```

### ml_predictions

```text
id
model_id
symbol
timeframe
prediction
confidence
features_snapshot_json
created_at
```

### risk_events

```text
id
event_type
severity
message
context_json
created_at
```

### system_logs

```text
id
level
service
message
context_json
created_at
```

---

## 8. API endpoints

### Market Data

```text
GET /api/market/pairs
GET /api/market/candles?symbol=BTC/USDT&timeframe=1h
POST /api/market/sync
```

### Indicators

```text
POST /api/indicators/calculate
GET /api/indicators?symbol=BTC/USDT&timeframe=1h
```

### Strategies

```text
GET /api/strategies
POST /api/strategies
POST /api/strategies/{id}/backtest
GET /api/strategies/{id}/signals
```

### Backtesting

```text
POST /api/backtests/run
GET /api/backtests/{id}
GET /api/backtests/{id}/trades
GET /api/backtests/{id}/metrics
```

### Paper Trading

```text
POST /api/paper/start
POST /api/paper/stop
GET /api/paper/status
GET /api/paper/trades
GET /api/paper/performance
```

### ML

```text
POST /api/ml/train
GET /api/ml/models
POST /api/ml/predict
GET /api/ml/predictions
```

### Risk

```text
GET /api/risk/events
GET /api/risk/settings
PUT /api/risk/settings
```

---

## 9. Frontend сторінки

## 9.1 Dashboard

Показує:

- поточний paper balance;
- P&L;
- відкриті позиції;
- останні сигнали;
- статус бота;
- останні помилки;
- графік equity curve.

## 9.2 Market

Показує:

- графік ціни;
- свічки;
- volume;
- RSI;
- MACD;
- EMA;
- Bollinger Bands.

## 9.3 Strategies

Показує:

- список стратегій;
- параметри;
- активна / неактивна;
- кнопка запуску backtest;
- результати тестів.

## 9.4 Backtesting

Показує:

- вибір пари;
- вибір таймфрейму;
- вибір періоду;
- параметри стратегії;
- результати:
  - total return;
  - max drawdown;
  - win rate;
  - profit factor;
  - Sharpe ratio;
  - кількість угод.

## 9.5 Paper Trading

Показує:

- статус paper trading;
- відкриті позиції;
- історію угод;
- P&L;
- причини входу/виходу;
- помилки виконання.

## 9.6 ML Models

Показує:

- список моделей;
- версії;
- features;
- accuracy;
- precision;
- recall;
- F1;
- performance у backtesting;
- активна модель.

## 9.7 Logs

Показує:

- системні логи;
- risk events;
- помилки API;
- алерти.

## 9.8 Settings

Показує:

- API ключі;
- paper balance;
- risk limits;
- Telegram alerts;
- активні біржі;
- активні торгові пари.

---

## 10. MVP: що зробити першим

## MVP Scope

Перша версія повинна включати:

```text
1. Backend на FastAPI
2. PostgreSQL + TimescaleDB
3. Підключення до Binance через ccxt
4. Збір OHLCV для BTC/USDT і ETH/USDT
5. Розрахунок RSI, EMA, MACD, ATR
6. Одна проста rule-based стратегія
7. Backtesting engine
8. Paper trading engine
9. Логування угод
10. Простий Dashboard
11. Telegram alerts
```

Не включати в MVP:

```text
- реальну торгівлю;
- LSTM;
- reinforcement learning;
- багато бірж;
- багато монет;
- складний AI-агент;
- ф’ючерси з плечем;
- скальпінг.
```

---

## 11. Покрокова реалізація

## Етап 0. Підготовка

### Завдання

- створити GitHub репозиторій;
- створити структуру проєкту;
- підготувати Docker Compose;
- підняти PostgreSQL, Redis, backend, frontend;
- створити `.env.example`.

### Результат

Проєкт запускається локально командою:

```bash
docker compose up --build
```

---

## Етап 1. Market Data

### Завдання

- підключити ccxt;
- реалізувати отримання OHLCV;
- зберігати candles у PostgreSQL;
- зробити endpoint для синхронізації;
- зробити cron/job для регулярного оновлення даних.

### Перевірка

- у БД є свічки BTC/USDT;
- немає дублікатів;
- дані мають правильний timestamp;
- можна отримати дані через API.

---

## Етап 2. Indicators

### Завдання

- реалізувати RSI;
- реалізувати EMA;
- реалізувати MACD;
- реалізувати ATR;
- зберігати результати в БД або рахувати on demand;
- написати unit tests для формул.

### Перевірка

- індикатори рахуються правильно;
- значення не NaN після достатньої кількості свічок;
- API повертає індикатори для графіка.

---

## Етап 3. Strategy Engine

### Завдання

- створити інтерфейс для стратегій;
- реалізувати першу стратегію RSI + EMA;
- генерувати сигнали BUY / SELL / HOLD;
- зберігати сигнали в БД.

### Перевірка

- стратегія не відкриває угоди без сигналу;
- сигнал має reason_json;
- можна подивитися історію сигналів.

---

## Етап 4. Backtesting

### Завдання

- створити backtest runner;
- проганяти стратегію по історичних даних;
- симулювати угоди;
- враховувати fee і slippage;
- рахувати метрики.

### Метрики

```text
Total Return
Max Drawdown
Win Rate
Profit Factor
Average Win
Average Loss
Sharpe Ratio
Number of Trades
```

### Перевірка

- backtest запускається для BTC/USDT;
- результати зберігаються;
- можна подивитися всі simulated trades;
- комісія впливає на результат.

---

## Етап 5. Paper Trading

### Завдання

- створити віртуальний баланс;
- запускати стратегію на live market data;
- відкривати simulated trades;
- закривати угоди по stop-loss / take-profit / sell signal;
- логувати всі події.

### Перевірка

- угоди не відправляються на біржу;
- баланс змінюється тільки в БД;
- усі дії видно в Dashboard;
- Telegram надсилає повідомлення про угоди.

---

## Етап 6. Dashboard

### Завдання

- створити frontend;
- показати balance, P&L, open positions;
- показати графік ціни;
- показати останні сигнали;
- показати історію угод.

### Перевірка

- користувач бачить стан системи;
- можна зрозуміти, чому бот відкрив угоду;
- видно помилки й алерти.

---

## Етап 7. ML v1

### Завдання

- створити feature dataset;
- створити target;
- навчити XGBoost;
- зберегти модель;
- отримувати prediction через API;
- додати ML confidence до strategy decision.

### Перевірка

- модель не навчається на майбутніх даних;
- є train/validation/test split;
- збережені метрики;
- модель можна вимкнути, якщо вона погіршує результат.

---

## Етап 8. AI Agent v1

### Завдання

- додати модуль пояснення сигналів;
- додати аналіз новин, якщо є API;
- не дозволяти AI напряму відкривати угоди;
- AI тільки додає контекст.

### Перевірка

- торгове рішення приймає strategy/risk engine;
- AI пояснює рішення;
- AI не має доступу до execution без risk engine.

---

## Етап 9. Pre-release

### Завдання

- покрити критичні модулі тестами;
- додати healthcheck;
- додати dead man's switch;
- додати Telegram emergency stop;
- перевірити роботу 24/7;
- перевірити backup БД;
- зробити staging-середовище.

---

## Етап 10. Release Candidate

Умови переходу до real-money test:

```text
1. Paper trading мінімум 2-3 місяці.
2. Max drawdown < 15-20%.
3. Strategy має позитивний результат після fee/slippage.
4. Немає критичних помилок execution.
5. Є manual kill switch.
6. Є Telegram alerts.
7. Є логи кожної дії.
8. Є backup.
9. Реальна торгівля стартує тільки з малої суми.
```

---

## 12. Тестування

## 12.1 Unit Tests

Тестувати:

- RSI;
- EMA;
- MACD;
- ATR;
- position sizing;
- stop-loss формули;
- take-profit формули;
- P&L розрахунок;
- fee calculation.

---

## 12.2 Integration Tests

Тестувати:

- отримання даних з біржі;
- запис candles у БД;
- запуск стратегії;
- створення сигналу;
- створення paper trade;
- Telegram notification.

---

## 12.3 Backtesting Tests

Перевірити:

- чи не використовуються майбутні дані;
- чи правильно враховується комісія;
- чи правильно працює stop-loss;
- чи правильно рахується drawdown;
- чи правильно рахується win rate.

---

## 12.4 Paper Trading Tests

Перевірити:

- бот не створює реальні ордери;
- баланс оновлюється правильно;
- одночасно не відкривається зайва позиція;
- stop-loss закриває позицію;
- take-profit закриває позицію;
- при помилці API бот не відкриває угоду.

---

## 12.5 ML Tests

Перевірити:

- немає data leakage;
- train/test split хронологічний;
- features однакові для train і live inference;
- модель не приймає рішення без confidence threshold;
- модель зберігається з версією.

---

## 12.6 Stress Tests

Перевірити:

- різкий рух ціни;
- API біржі не відповідає;
- Redis недоступний;
- БД недоступна;
- дублікати candles;
- пропущені candles;
- Telegram недоступний.

---

## 13. Метрики якості стратегії

### Total Return

Загальний прибуток або збиток.

### Max Drawdown

Максимальна просадка від піку балансу.

```text
Drawdown = (Peak Equity - Current Equity) / Peak Equity
```

### Win Rate

```text
Win Rate = Winning Trades / Total Trades
```

### Profit Factor

```text
Profit Factor = Gross Profit / Gross Loss
```

Бажано:

```text
Profit Factor > 1.3
```

### Sharpe Ratio

```text
Sharpe Ratio = (Average Return - Risk Free Rate) / Std(Returns)
```

Для crypto risk-free rate можна спростити до 0 на MVP.

Бажано:

```text
Sharpe Ratio > 1.0
```

Але це не гарантія прибутковості.

### Average Risk/Reward

```text
Average Win / Average Loss
```

---

## 14. Правила безпеки

```text
1. Реальна торгівля вимкнена за замовчуванням.
2. API ключі зберігаються тільки в .env або secret manager.
3. Для MVP API ключі біржі не повинні мати права withdrawal.
4. Усі ордери проходять через risk engine.
5. Кожна дія логуються.
6. Має бути emergency stop.
7. Якщо дані застарілі — не торгувати.
8. Якщо API повертає помилку — не торгувати.
9. Якщо денний ліміт збитку досягнуто — зупинити торгівлю.
10. Якщо drawdown перевищено — зупинити торгівлю.
```

---

## 15. Конфігурація ризику для старту

```json
{
  "mode": "paper",
  "initial_balance": 1000,
  "risk_per_trade_percent": 1,
  "max_daily_loss_percent": 5,
  "max_total_drawdown_percent": 15,
  "max_open_positions": 1,
  "allowed_symbols": ["BTC/USDT", "ETH/USDT"],
  "allowed_timeframes": ["1h", "4h"],
  "use_real_trading": false,
  "require_stop_loss": true,
  "slippage_percent": 0.05,
  "fee_percent": 0.1
}
```

---

## 16. Приклад decision flow

```text
1. Scheduler отримує нову свічку BTC/USDT 1h.
2. Система оновлює candles.
3. Indicator Service рахує RSI, EMA, MACD, ATR.
4. Strategy Service генерує сигнал.
5. ML Service повертає probability.
6. Risk Engine перевіряє:
   - денний ліміт;
   - drawdown;
   - відкриті позиції;
   - stop-loss;
   - розмір позиції.
7. Якщо все дозволено — Paper Execution відкриває simulated trade.
8. Trade записується в БД.
9. Telegram надсилає повідомлення.
10. Dashboard оновлює стан.
```

---

## 17. Telegram alerts

Повідомлення мають приходити для:

- старту бота;
- зупинки бота;
- відкриття угоди;
- закриття угоди;
- stop-loss;
- take-profit;
- помилки API;
- перевищення drawdown;
- досягнення денного ліміту збитку;
- emergency stop.

Приклад повідомлення:

```text
BTC/USDT PAPER TRADE OPENED
Side: BUY
Entry: 65000
Stop Loss: 63700
Take Profit: 67600
Risk: 1%
Reason: RSI < 35, price above EMA200, MACD improving
```

---

## 18. Roadmap

## Version 0.1 — Local MVP

- backend;
- database;
- market data;
- indicators;
- one strategy;
- backtesting.

## Version 0.2 — Paper Trading

- live data sync;
- paper balance;
- simulated trades;
- Telegram alerts;
- dashboard.

## Version 0.3 — ML v1

- feature dataset;
- XGBoost;
- prediction API;
- confidence threshold;
- ML metrics.

## Version 0.4 — Analytics

- equity curve;
- drawdown chart;
- strategy comparison;
- trade journal;
- model comparison.

## Version 0.5 — AI Assistant

- signal explanation;
- news summary;
- strategy report;
- weekly performance analysis.

## Version 1.0 — Release Candidate

- stable paper trading;
- monitoring;
- alerts;
- emergency stop;
- deployment;
- documentation;
- optional real trading with very small capital.

---

## 19. Що не робити на старті

```text
1. Не запускати реальні гроші одразу.
2. Не використовувати leverage.
3. Не робити scalping bot.
4. Не торгувати 20+ монетами.
5. Не починати з LSTM/Transformer.
6. Не дозволяти AI напряму торгувати.
7. Не ігнорувати комісії та slippage.
8. Не оцінювати стратегію тільки по win rate.
9. Не навчати модель на майбутніх даних.
10. Не міняти стратегію щодня без нормального аналізу.
```

---

## 20. Команди для AI/Codex під час розробки

Цей файл можна використовувати як основний prompt для AI-асистента або Codex.

### Основна команда

```text
Ти працюєш над проєктом Crypto Trading Research Bot.
Дотримуйся архітектури, описаної в PROJECT_PROMPT.md.
Не додавай реальну торгівлю в MVP.
Спочатку реалізуй market data, indicators, backtesting і paper trading.
Усі торгові рішення повинні проходити через risk engine.
Усі дії повинні логуватися.
```

### Команда для першого етапу

```text
Створи backend на FastAPI для Crypto Trading Research Bot.
Додай Docker Compose з PostgreSQL, Redis і backend.
Створи моделі БД для exchanges, trading_pairs і candles.
Додай сервіс отримання OHLCV через ccxt для BTC/USDT і ETH/USDT.
Реальна торгівля не потрібна.
```

### Команда для індикаторів

```text
Додай Indicator Service.
Реалізуй RSI, EMA, MACD, ATR для candles.
Додай unit tests для формул.
Зроби API endpoint для отримання індикаторів по symbol і timeframe.
```

### Команда для backtesting

```text
Додай Backtesting Service.
Він має запускати strategy по історичних candles, симулювати угоди, враховувати fee і slippage, рахувати total return, max drawdown, win rate, profit factor і Sharpe ratio.
```

### Команда для paper trading

```text
Додай Paper Trading Service.
Він має працювати тільки з віртуальним балансом, не створювати реальні ордери, логувати всі угоди і надсилати Telegram alerts.
```

---

## 21. Критерій успішного MVP

MVP можна вважати готовим, якщо:

```text
1. Дані BTC/USDT і ETH/USDT регулярно завантажуються.
2. Індикатори рахуються автоматично.
3. Є хоча б одна стратегія.
4. Backtesting працює на історичних даних.
5. Paper trading працює без реальних грошей.
6. Усі угоди логуються.
7. Dashboard показує стан системи.
8. Telegram надсилає алерти.
9. Є базові тести.
10. Реальна торгівля технічно заблокована в MVP.
```

---

## 22. Фінальний принцип

Цей проєкт потрібно будувати як дослідницьку платформу для перевірки торгових гіпотез, а не як “бот для гарантованого заробітку”.

Правильний фокус:

```text
спочатку стабільність → потім аналітика → потім ML → потім paper trading → тільки потім обережний real trading
```

Головний пріоритет — контроль ризику, прозорість рішень і можливість зупинити систему в будь-який момент.
