"""Technical indicator calculations for crypto trading.

Provides pure Python implementations of common technical indicators
operating on OHLCV data. No external library dependency.
"""

import math
from dataclasses import dataclass, field


@dataclass
class IndicatorResult:
    """Container for indicator calculation results."""

    name: str
    values: list[float | None] = field(default_factory=list)
    metadata: dict[str, float | str] = field(default_factory=dict)


def _sma(values: list[float], period: int) -> list[float | None]:
    """Simple Moving Average.

    Args:
        values: List of price values.
        period: Lookback period.

    Returns:
        SMA values (first period-1 entries are None).
    """
    result: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            window = values[i - period + 1 : i + 1]
            result.append(sum(window) / period)
    return result


def _ema(values: list[float], period: int) -> list[float | None]:
    """Exponential Moving Average.

    Uses the Wilder smoothing method where alpha = 1/period.

    Args:
        values: List of price values.
        period: Lookback period.

    Returns:
        EMA values.
    """
    result: list[float | None] = []
    alpha = 2.0 / (period + 1)
    ema_prev: float | None = None

    for i, price in enumerate(values):
        if i < period - 1:
            result.append(None)
        elif i == period - 1:
            sma = sum(values[:period]) / period
            result.append(sma)
            ema_prev = sma
        else:
            ema_val = (price - ema_prev) * alpha + ema_prev
            result.append(ema_val)
            ema_prev = ema_val
    return result


def _rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index.

    Uses the Wilder smoothing method (average gain / average loss).

    Args:
        closes: List of closing prices.
        period: Lookback period (typically 14).

    Returns:
        RSI values (0-100).
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    result: list[float | None] = [None] * len(closes)
    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0.0)
        losses.append(abs(diff) if diff < 0 else 0.0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


def _atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    """Average True Range.

    Args:
        highs: High prices.
        lows: Low prices.
        closes: Closing prices.
        period: Lookback period.

    Returns:
        ATR values.
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    tr_values: list[float] = []
    for i in range(len(closes)):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        tr_values.append(tr)

    result: list[float | None] = [None] * len(closes)
    result[period] = sum(tr_values[:period]) / period
    atr_prev = result[period]

    for i in range(period, len(tr_values)):
        atr_val = (atr_prev * (period - 1) + tr_values[i]) / period
        result[i] = atr_val
        atr_prev = atr_val

    return result


def _macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float | None]]:
    """MACD (Moving Average Convergence Divergence).

    Args:
        closes: Closing prices.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        Dict with 'macd', 'signal', 'histogram' lists.
    """
    fast_ema = _ema(closes, fast)
    slow_ema = _ema(closes, slow)

    macd_line: list[float | None] = []
    for f, s in zip(fast_ema, slow_ema):
        if f is not None and s is not None:
            macd_line.append(f - s)
        else:
            macd_line.append(None)

    valid_macd = [v for v in macd_line if v is not None]

    if len(valid_macd) < signal:
        signal_line: list[float | None] = [None] * len(macd_line)
    else:
        signal_line = _ema(valid_macd, signal)
        padding = [None] * (len(macd_line) - len(signal_line))
        signal_line = padding + signal_line

    histogram: list[float | None] = []
    for m, s in zip(macd_line, signal_line):
        if m is not None and s is not None:
            histogram.append(m - s)
        else:
            histogram.append(None)

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def _bollinger_bands(
    closes: list[float], period: int = 20, std_dev: float = 2.0
) -> dict[str, list[float | None]]:
    """Bollinger Bands.

    Args:
        closes: Closing prices.
        period: SMA period (default 20).
        std_dev: Standard deviation multiplier (default 2.0).

    Returns:
        Dict with 'upper', 'middle', 'lower' lists.
    """
    middle = _sma(closes, period)

    upper: list[float | None] = []
    lower: list[float | None] = []
    bandwidth: list[float | None] = []

    for i, mid in enumerate(middle):
        if mid is None:
            upper.append(None)
            lower.append(None)
            bandwidth.append(None)
            continue

        window = closes[i - period + 1 : i + 1]
        variance = sum((x - mid) ** 2 for x in window) / period
        std = math.sqrt(variance)

        upper.append(mid + std_dev * std)
        lower.append(mid - std_dev * std)
        bandwidth.append((upper[-1] - lower[-1]) / mid * 100 if mid > 0 else 0)  # type: ignore[arg-type]

    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "bandwidth": bandwidth,
    }


def _vwap(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> list[float | None]:
    """Volume-Weighted Average Price.

    Calculated using the typical price: (high + low + close) / 3.

    Args:
        highs: High prices.
        lows: Low prices.
        closes: Closing prices.
        volumes: Volume data.

    Returns:
        VWAP values (cumulative from start).
    """
    result: list[float | None] = []
    cum_pv = 0.0
    cum_vol = 0.0

    for i in range(len(closes)):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += typical * volumes[i]
        cum_vol += volumes[i]
        result.append(cum_pv / cum_vol if cum_vol > 0 else None)

    return result


def _volume_delta(closes: list[float], volumes: list[float]) -> list[float | None]:
    """Volume Delta (up volume - down volume cumulative).

    Args:
        closes: Closing prices.
        volumes: Volume data.

    Returns:
        Cumulative volume delta values.
    """
    result: list[float | None] = []
    cum_delta = 0.0

    for i in range(len(closes)):
        if i == 0:
            result.append(0.0)
            continue
        delta = volumes[i] if closes[i] >= closes[i - 1] else -volumes[i]
        cum_delta += delta
        result.append(cum_delta)

    return result


def _cvd(closes: list[float], volumes: list[float]) -> list[float | None]:
    """Cumulative Volume Delta (alias for volume delta)."""
    return _volume_delta(closes, volumes)


def _momentum(closes: list[float], period: int = 10) -> list[float | None]:
    """Momentum indicator: close_price - close_price[period] ago.

    Args:
        closes: Closing prices.
        period: Lookback period.

    Returns:
        Momentum values.
    """
    result: list[float | None] = []
    for i in range(len(closes)):
        if i < period:
            result.append(None)
        else:
            result.append(closes[i] - closes[i - period])
    return result


def _roc(closes: list[float], period: int = 10) -> list[float | None]:
    """Rate of Change: ((close - close[period]) / close[period]) * 100.

    Args:
        closes: Closing prices.
        period: Lookback period.

    Returns:
        ROC values in percent.
    """
    result: list[float | None] = []
    for i in range(len(closes)):
        if i < period:
            result.append(None)
        else:
            prev = closes[i - period]
            if prev == 0:
                result.append(None)
            else:
                result.append(((closes[i] - prev) / prev) * 100)
    return result


INDICATOR_MAP: dict[str, tuple] = {
    "sma": (_sma, ["close"], True),
    "ema": (_ema, ["close"], True),
    "rsi": (_rsi, ["close"], True),
    "atr": (_atr, ["high", "low", "close"], True),
    "macd": (_macd, ["close"], False),
    "bollinger_bands": (_bollinger_bands, ["close"], False),
    "vwap": (_vwap, ["high", "low", "close", "volume"], False),
    "volume_delta": (_volume_delta, ["close", "volume"], False),
    "cvd": (_cvd, ["close", "volume"], False),
    "momentum": (_momentum, ["close"], True),
    "roc": (_roc, ["close"], True),
}


def calculate_indicators(
    symbol: str,
    timeframe: str,
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    indicators: list[str],
    period: int = 14,
) -> dict[str, dict[str, float | None] | list[float | None]]:
    """Calculate multiple technical indicators on OHLCV data.

    Args:
        symbol: Trading pair (for metadata).
        timeframe: Candle interval (for metadata).
        opens: Open prices list.
        highs: High prices list.
        lows: Low prices list.
        closes: Close prices list.
        volumes: Volume list.
        indicators: List of indicator names to calculate.
        period: Default period for applicable indicators.

    Returns:
        Dictionary mapping indicator names to their values.
    """
    if not closes or len(closes) < period:
        return {"error": f"Insufficient data: need at least {period} candles"}

    result: dict[str, dict[str, float | None] | list[float | None]] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "period": period,
        "last_close": closes[-1],
    }

    for ind_name in indicators:
        key = ind_name.lower().replace(" ", "_")
        if key not in INDICATOR_MAP:
            result[key] = {"error": f"Unknown indicator: {ind_name}"}
            continue

        func, required_fields, needs_period = INDICATOR_MAP[key]
        field_map = {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }

        args = [field_map[f] for f in required_fields]
        if needs_period:
            args.append(period)
        output = func(*args)

        if isinstance(output, dict):
            result[key] = {k: v[-1] if v and v[-1] is not None else None for k, v in output.items()}
        else:
            result[key] = output[-1] if output and output[-1] is not None else None

    return result
