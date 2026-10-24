"""Round half up (82.5 -> 83). Python's round() rounds half to even, so never use it for display."""
from decimal import ROUND_HALF_UP, Decimal


def rhu(x: float, nd: int = 0) -> float:
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def r4(x: float | None) -> float | None:
    """Output precision for every non-final number in a result."""
    return None if x is None else rhu(x, 4)
