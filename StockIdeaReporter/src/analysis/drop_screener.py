"""급락 종목 스크리닝 모듈.

스윙 매매 관점에서 단기 과도하게 하락한 종목을 필터링하고 점수화한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger(__name__)

# ── 스크리닝 기준 상수 ────────────────────────────────────────────
_MIN_ROWS = 30
_DROP_3D = -0.05       # 3일 낙폭 기준 (-5%)
_DROP_10D = -0.10      # 10일 낙폭 기준 (-10%)
_DROP_20D = -0.08      # 20일 낙폭 기준 (-8%)
_FROM_52W = -0.20      # 52주 고점 대비 (-20%)
_RSI_OVERSOLD = 35
_BB_PCT_THRESH = 0.20
_STOCH_OVERSOLD = 25


@dataclass(frozen=True)
class DropCandidate:
    """급락 종목 스크리닝 결과."""

    ticker: str
    market: str
    name: str
    drop_3d: float          # % (음수)
    drop_10d: float
    drop_20d: float
    from_52w_high: float    # 52주 고점 대비 %
    rsi: float
    bb_pct: float           # 볼린저밴드 내 위치 (0~1)
    stoch_k: float
    volume_ratio: float     # 최근 거래량 / 20일 평균
    drop_score: float       # 종합 점수 (높을수록 매력)
    signals: list[str] = field(default_factory=list)


class DropScreener:
    """급락 종목 필터링 및 점수화."""

    def screen(
        self,
        universe_data: dict[str, pd.DataFrame],
        market_map: dict[str, str],
        name_map: dict[str, str] | None = None,
    ) -> list[DropCandidate]:
        """전체 유니버스에서 급락 종목 필터링.

        Args:
            universe_data: ticker → OHLCV DataFrame
            market_map: ticker → "KR" / "US"
            name_map: ticker → 기업명

        Returns:
            점수 내림차순 정렬된 후보 리스트
        """
        name_map = name_map or {}
        candidates: list[DropCandidate] = []

        for ticker, df in universe_data.items():
            try:
                c = self._evaluate(
                    ticker, df,
                    market_map.get(ticker, "US"),
                    name_map.get(ticker, ticker),
                )
                if c is not None:
                    candidates.append(c)
            except Exception as e:
                logger.debug("스크리닝 실패 (%s): %s", ticker, e)

        return sorted(candidates, key=lambda c: c.drop_score, reverse=True)

    def rank_candidates(
        self, candidates: list[DropCandidate], top_n: int = 10
    ) -> list[DropCandidate]:
        """상위 N개 반환."""
        return candidates[:top_n]

    # ── 개별 종목 평가 ──────────────────────────────────────────

    def _evaluate(
        self, ticker: str, df: pd.DataFrame, market: str, name: str
    ) -> DropCandidate | None:
        if len(df) < _MIN_ROWS:
            return None

        close = df["Close"]
        volume = df.get("Volume", pd.Series(dtype=float))

        drop_3d = _drop(close, 3)
        drop_10d = _drop(close, 10)
        drop_20d = _drop(close, 20)
        from_52w = _from_52w_high(close)

        # 1단계: 낙폭 필터 (3일 OR 10일 + 20일 + 52주)
        passes = (
            (drop_3d <= _DROP_3D or drop_10d <= _DROP_10D)
            and drop_20d <= _DROP_20D
            and from_52w <= _FROM_52W
        )
        if not passes:
            return None

        rsi = _calc_rsi(close)
        bb_pct = _calc_bb_pct(close)
        stoch_k = _calc_stoch(df)
        vol_ratio = _calc_volume_ratio(volume)

        # 2단계: 과매도 조건 (하나 이상)
        signals: list[str] = []
        if rsi < _RSI_OVERSOLD:
            signals.append(f"RSI 과매도({rsi:.1f})")
        if bb_pct < _BB_PCT_THRESH:
            signals.append(f"BB 하단({bb_pct:.2f})")
        if stoch_k < _STOCH_OVERSOLD:
            signals.append(f"Stoch 과매도({stoch_k:.1f})")
        if vol_ratio >= 2.0:
            signals.append(f"거래량급증({vol_ratio:.1f}x)")

        if not signals:
            return None

        score = _calc_score(drop_3d, drop_10d, from_52w, rsi, bb_pct, vol_ratio)

        return DropCandidate(
            ticker=ticker,
            market=market,
            name=name,
            drop_3d=round(drop_3d * 100, 2),
            drop_10d=round(drop_10d * 100, 2),
            drop_20d=round(drop_20d * 100, 2),
            from_52w_high=round(from_52w * 100, 2),
            rsi=round(rsi, 1),
            bb_pct=round(bb_pct, 3),
            stoch_k=round(stoch_k, 1),
            volume_ratio=round(vol_ratio, 2),
            drop_score=round(score, 3),
            signals=signals,
        )


# ── 지표 계산 함수 (모듈 레벨) ───────────────────────────────────

def _drop(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        return 0.0
    return float((close.iloc[-1] - close.iloc[-days - 1]) / close.iloc[-days - 1])


def _from_52w_high(close: pd.Series) -> float:
    high = close.tail(252).max()
    if not high or high == 0:
        return 0.0
    return float((close.iloc[-1] - high) / high)


def _calc_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return float(val) if pd.notna(val) else 50.0


def _calc_bb_pct(close: pd.Series, period: int = 20) -> float:
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    rng = upper.iloc[-1] - lower.iloc[-1]
    if not rng or rng == 0:
        return 0.5
    val = (close.iloc[-1] - lower.iloc[-1]) / rng
    return float(val) if pd.notna(val) else 0.5


def _calc_stoch(df: pd.DataFrame, period: int = 14) -> float:
    high = df["High"].rolling(period).max()
    low = df["Low"].rolling(period).min()
    rng = (high - low).replace(0, float("nan"))
    k = 100 * (df["Close"] - low) / rng
    val = k.iloc[-1]
    return float(val) if pd.notna(val) else 50.0


def _calc_volume_ratio(volume: pd.Series) -> float:
    if volume.empty:
        return 1.0
    avg = volume.tail(20).mean()
    if not avg or avg == 0:
        return 1.0
    return float(volume.iloc[-1] / avg)


def _calc_score(
    drop_3d: float,
    drop_10d: float,
    from_52w: float,
    rsi: float,
    bb_pct: float,
    vol_ratio: float,
) -> float:
    score = 0.0
    score += min(abs(drop_3d) * 5, 2.0)      # 단기 낙폭 (최대 2점)
    score += min(abs(drop_10d) * 3, 2.0)     # 중기 낙폭 (최대 2점)
    score += min(abs(from_52w) * 2, 2.0)     # 52주 낙폭 (최대 2점)
    score += max(0.0, (35 - rsi) / 35)        # RSI 과매도 (최대 1점)
    score += max(0.0, (0.2 - bb_pct) / 0.2)  # BB 하단 (최대 1점)
    if vol_ratio >= 2.0:
        score += min((vol_ratio - 2) * 0.2, 1.0)
    return score
