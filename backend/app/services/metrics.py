"""趋势与告警共享的余额消耗计算。"""
from datetime import timezone


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def burn_rate(snaps) -> float | None:
    balances = sorted(
        (s for s in snaps if s.balance_total is not None),
        key=lambda s: _utc(s.fetched_at),
    )
    if len(balances) < 2:
        return None
    elapsed = 0.0
    spent = 0.0
    for prev, curr in zip(balances, balances[1:]):
        seconds = (_utc(curr.fetched_at) - _utc(prev.fetched_at)).total_seconds()
        if seconds <= 0 or curr.currency != prev.currency:
            continue
        elapsed += seconds
        spent += max(float(prev.balance_total) - float(curr.balance_total), 0)
    return spent / (elapsed / 86400) if elapsed else None
