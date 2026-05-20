from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = Field(default="Crypto Trading Research Bot", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    backend_reload: bool = Field(default=True, alias="BACKEND_RELOAD")

    database_url: str = Field(
        default="postgresql+asyncpg://trading:trading@postgres:5432/trading",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    market_data_exchange: str = Field(default="binance", alias="MARKET_DATA_EXCHANGE")
    market_data_symbols: str = Field(default="BTC/USDT,ETH/USDT", alias="MARKET_DATA_SYMBOLS")
    market_data_timeframes: str = Field(default="1h,4h", alias="MARKET_DATA_TIMEFRAMES")
    market_data_default_fetch_limit: int = Field(default=500, alias="MARKET_DATA_DEFAULT_FETCH_LIMIT")
    risk_mode: str = Field(default="paper", alias="RISK_MODE")
    risk_initial_balance: float = Field(default=1000.0, alias="RISK_INITIAL_BALANCE")
    risk_per_trade_percent: float = Field(default=1.0, alias="RISK_PER_TRADE_PERCENT")
    risk_max_daily_loss_percent: float = Field(default=5.0, alias="RISK_MAX_DAILY_LOSS_PERCENT")
    risk_max_total_drawdown_percent: float = Field(default=15.0, alias="RISK_MAX_TOTAL_DRAWDOWN_PERCENT")
    risk_max_open_positions: int = Field(default=1, alias="RISK_MAX_OPEN_POSITIONS")
    risk_require_stop_loss: bool = Field(default=True, alias="RISK_REQUIRE_STOP_LOSS")
    risk_slippage_percent: float = Field(default=0.05, alias="RISK_SLIPPAGE_PERCENT")
    risk_fee_percent: float = Field(default=0.1, alias="RISK_FEE_PERCENT")
    risk_atr_stop_multiplier: float = Field(default=2.0, alias="RISK_ATR_STOP_MULTIPLIER")
    risk_reward_to_risk_ratio: float = Field(default=2.5, alias="RISK_REWARD_TO_RISK_RATIO")
    risk_use_real_trading: bool = Field(default=False, alias="RISK_USE_REAL_TRADING")
    strategy_default_name: str = Field(default="rsi_ema_trend_multi_v1", alias="STRATEGY_DEFAULT_NAME")
    strategy_rsi_ema_v1_buy_rsi_max: float = Field(default=35.0, alias="STRATEGY_RSI_EMA_V1_BUY_RSI_MAX")
    strategy_rsi_ema_v1_sell_rsi_min: float = Field(default=65.0, alias="STRATEGY_RSI_EMA_V1_SELL_RSI_MIN")
    strategy_rsi_ema_v1_require_macd_improving: bool = Field(
        default=True,
        alias="STRATEGY_RSI_EMA_V1_REQUIRE_MACD_IMPROVING",
    )
    strategy_rsi_ema_v2_buy_rsi_max: float = Field(default=40.0, alias="STRATEGY_RSI_EMA_V2_BUY_RSI_MAX")
    strategy_rsi_ema_v2_sell_rsi_min: float = Field(default=58.0, alias="STRATEGY_RSI_EMA_V2_SELL_RSI_MIN")
    strategy_rsi_ema_v2_require_macd_improving: bool = Field(
        default=False,
        alias="STRATEGY_RSI_EMA_V2_REQUIRE_MACD_IMPROVING",
    )
    strategy_rsi_ema_multi_v1_trend_period: int = Field(
        default=100,
        alias="STRATEGY_RSI_EMA_MULTI_V1_TREND_PERIOD",
    )
    strategy_rsi_ema_multi_v1_buy_rsi_max: float = Field(
        default=40.0,
        alias="STRATEGY_RSI_EMA_MULTI_V1_BUY_RSI_MAX",
    )
    strategy_rsi_ema_multi_v1_sell_rsi_min: float = Field(
        default=58.0,
        alias="STRATEGY_RSI_EMA_MULTI_V1_SELL_RSI_MIN",
    )
    strategy_rsi_ema_multi_v1_require_macd_improving: bool = Field(
        default=False,
        alias="STRATEGY_RSI_EMA_MULTI_V1_REQUIRE_MACD_IMPROVING",
    )
    strategy_rsi_ema_paper_v1_trend_period: int = Field(
        default=50,
        alias="STRATEGY_RSI_EMA_PAPER_V1_TREND_PERIOD",
    )
    strategy_rsi_ema_paper_v1_buy_rsi_max: float = Field(
        default=52.0,
        alias="STRATEGY_RSI_EMA_PAPER_V1_BUY_RSI_MAX",
    )
    strategy_rsi_ema_paper_v1_sell_rsi_min: float = Field(
        default=55.0,
        alias="STRATEGY_RSI_EMA_PAPER_V1_SELL_RSI_MIN",
    )
    strategy_rsi_ema_paper_v1_require_macd_improving: bool = Field(
        default=False,
        alias="STRATEGY_RSI_EMA_PAPER_V1_REQUIRE_MACD_IMPROVING",
    )
    strategy_symbol_overrides: str = Field(
        default="BTC/USDT:rsi_ema_trend_v2,ETH/USDT:rsi_ema_trend_multi_v1",
        alias="STRATEGY_SYMBOL_OVERRIDES",
    )
    paper_strategy_symbol_overrides: str = Field(
        default="BTC/USDT:rsi_ema_trend_paper_v1,ETH/USDT:rsi_ema_trend_paper_v1",
        alias="PAPER_STRATEGY_SYMBOL_OVERRIDES",
    )
    automation_enabled: bool = Field(default=True, alias="AUTOMATION_ENABLED")
    automation_account_name: str = Field(default="paper-main", alias="AUTOMATION_ACCOUNT_NAME")
    automation_loop_interval_seconds: int = Field(default=300, alias="AUTOMATION_LOOP_INTERVAL_SECONDS")
    automation_execution_timeframes: str = Field(default="1h", alias="AUTOMATION_EXECUTION_TIMEFRAMES")
    daily_report_enabled: bool = Field(default=True, alias="DAILY_REPORT_ENABLED")
    daily_report_account_name: str = Field(default="paper-main", alias="DAILY_REPORT_ACCOUNT_NAME")
    daily_report_timezone: str = Field(default="Europe/Kiev", alias="DAILY_REPORT_TIMEZONE")
    daily_report_time_local: str = Field(default="09:00", alias="DAILY_REPORT_TIME_LOCAL")
    telegram_enabled: bool = Field(default=False, alias="TELEGRAM_ENABLED")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    telegram_bot_name: str = Field(default="", alias="TELEGRAM_BOT_NAME")
    telegram_username: str = Field(default="", alias="TELEGRAM_USERNAME")
    ml_models_dir: str = Field(default="ml/models", alias="ML_MODELS_DIR")
    ml_datasets_dir: str = Field(default="ml/datasets", alias="ML_DATASETS_DIR")
    ml_default_confidence_threshold: float = Field(default=0.6, alias="ML_DEFAULT_CONFIDENCE_THRESHOLD")
    ml_default_target: str = Field(default="future_edge_long", alias="ML_DEFAULT_TARGET")
    ml_default_forecast_horizon_candles: int = Field(default=3, alias="ML_DEFAULT_FORECAST_HORIZON_CANDLES")
    ml_default_min_edge_percent: float = Field(default=0.4, alias="ML_DEFAULT_MIN_EDGE_PERCENT")
    ml_default_min_precision: float = Field(default=0.4, alias="ML_DEFAULT_MIN_PRECISION")
    ml_default_min_positive_predictions: int = Field(default=12, alias="ML_DEFAULT_MIN_POSITIVE_PREDICTIONS")
    ml_train_ratio: float = Field(default=0.6, alias="ML_TRAIN_RATIO")
    ml_validation_ratio: float = Field(default=0.2, alias="ML_VALIDATION_RATIO")
    ml_test_ratio: float = Field(default=0.2, alias="ML_TEST_RATIO")
    ml_min_rows: int = Field(default=120, alias="ML_MIN_ROWS")
    ml_risk_filter_enabled: bool = Field(default=False, alias="ML_RISK_FILTER_ENABLED")
    ml_risk_filter_require_model: bool = Field(default=False, alias="ML_RISK_FILTER_REQUIRE_MODEL")
    ml_risk_filter_confidence_threshold: float = Field(
        default=0.6,
        alias="ML_RISK_FILTER_CONFIDENCE_THRESHOLD",
    )
    ml_risk_filter_symbols: str = Field(default="BTC/USDT", alias="ML_RISK_FILTER_SYMBOLS")
    ml_eval_min_closed_trades: int = Field(default=5, alias="ML_EVAL_MIN_CLOSED_TRADES")
    ml_eval_min_profit_factor: float = Field(default=1.05, alias="ML_EVAL_MIN_PROFIT_FACTOR")
    ml_eval_max_drawdown_percent: float = Field(default=12.0, alias="ML_EVAL_MAX_DRAWDOWN_PERCENT")
    ml_eval_min_test_precision: float = Field(default=0.35, alias="ML_EVAL_MIN_TEST_PRECISION")
    ml_eval_allowed_review_statuses: str = Field(
        default="approved_for_paper_gate,approved",
        alias="ML_EVAL_ALLOWED_REVIEW_STATUSES",
    )

    @property
    def market_data_symbol_list(self) -> list[str]:
        return [symbol.strip() for symbol in self.market_data_symbols.split(",") if symbol.strip()]

    @property
    def market_data_timeframe_list(self) -> list[str]:
        return [timeframe.strip() for timeframe in self.market_data_timeframes.split(",") if timeframe.strip()]

    @property
    def strategy_symbol_override_map(self) -> dict[str, str]:
        overrides: dict[str, str] = {}
        for item in self.strategy_symbol_overrides.split(","):
            raw_item = item.strip()
            if not raw_item or ":" not in raw_item:
                continue
            symbol, strategy_name = raw_item.split(":", maxsplit=1)
            symbol = symbol.strip()
            strategy_name = strategy_name.strip()
            if symbol and strategy_name:
                overrides[symbol] = strategy_name
        return overrides

    @property
    def paper_strategy_symbol_override_map(self) -> dict[str, str]:
        overrides: dict[str, str] = {}
        for item in self.paper_strategy_symbol_overrides.split(","):
            raw_item = item.strip()
            if not raw_item or ":" not in raw_item:
                continue
            symbol, strategy_name = raw_item.split(":", maxsplit=1)
            symbol = symbol.strip()
            strategy_name = strategy_name.strip()
            if symbol and strategy_name:
                overrides[symbol] = strategy_name
        return overrides

    @property
    def automation_execution_timeframe_list(self) -> list[str]:
        return [timeframe.strip() for timeframe in self.automation_execution_timeframes.split(",") if timeframe.strip()]

    @property
    def ml_risk_filter_symbol_list(self) -> list[str]:
        return [symbol.strip() for symbol in self.ml_risk_filter_symbols.split(",") if symbol.strip()]

    @property
    def ml_eval_allowed_review_status_list(self) -> list[str]:
        return [status.strip() for status in self.ml_eval_allowed_review_statuses.split(",") if status.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
