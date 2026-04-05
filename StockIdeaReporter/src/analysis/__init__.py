"""분석 모듈."""

__all__ = [
    "TechnicalAnalyzer",
    "TechnicalSignals",
    "FundamentalAnalyzer",
    "FundamentalSummary",
]


def __getattr__(name: str):
    if name in ("TechnicalAnalyzer", "TechnicalSignals"):
        from .technical import TechnicalAnalyzer, TechnicalSignals
        return locals()[name]
    if name in ("FundamentalAnalyzer", "FundamentalSummary"):
        from .fundamental import FundamentalAnalyzer, FundamentalSummary
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
