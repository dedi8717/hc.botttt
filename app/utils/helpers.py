from __future__ import annotations


def format_price(price: int) -> str:
    """1000000 -> '1,000,000'"""
    try:
        return f"{int(price):,}"
    except (ValueError, TypeError):
        return str(price)


def truncate(text: str, length: int = 40) -> str:
    if text is None:
        return ""
    return text if len(text) <= length else text[: length - 1] + "…"
