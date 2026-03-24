"""데이터 수집 모듈."""

__all__ = ["StockDataFetcher", "FinancialDataFetcher"]


def __getattr__(name: str):
    if name == "StockDataFetcher":
        from .stock_data import StockDataFetcher
        return StockDataFetcher
    if name == "FinancialDataFetcher":
        from .financial_data import FinancialDataFetcher
        return FinancialDataFetcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
