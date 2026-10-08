"""Build past-only selection instances. Missing observations never get filled."""

from datetime import date

import numpy as np
from sklearn.covariance import LedoitWolf

from qcompass.data.snapshots import load_snapshot
from qcompass.data.validation import DataQualityError, validate_prices
from qcompass.portfolio.models import PortfolioInstance


def validated_date(value, label="Date"):
    """Reject ambiguous date strings before any temporal filtering."""
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("Noncanonical date")
    except (TypeError, ValueError) as exc:
        raise DataQualityError(f"{label} must use a valid YYYY-MM-DD date") from exc
    return parsed


def aligned_window(prices, symbols, sessions, as_of, lookback=252):
    cutoff = validated_date(as_of, "Decision date")
    if prices.empty or not symbols:
        raise DataQualityError("No authentic observations available")
    completed = {validated_date(str(d), "Session date") for d in sessions}
    dates = [d.isoformat() for d in sorted(d for d in completed if d <= cutoff)][-(lookback + 1) :]
    if len(dates) != lookback + 1:
        raise DataQualityError(f"Need {lookback + 1} completed session prices")
    selected = prices[prices.symbol.isin(symbols) & prices.date.isin(dates)].copy()
    audit = validate_prices(selected)
    if audit["large_moves"]:
        raise DataQualityError("Unresolved adjusted-price move above 35% in estimation window")
    wide = selected.pivot(index="date", columns="symbol", values="adj_close").reindex(
        index=dates, columns=symbols
    )
    if wide.isna().any().any():
        bad = wide.columns[wide.isna().any()].tolist()
        raise DataQualityError(f"Missing session prices for {', '.join(bad)}; no interpolation allowed")
    return wide


def build_instance(
    dataset_id, n=8, k=4, sector_limit=1, risk_aversion=1.0, as_of=None, root=None, symbols=None
):
    manifest, members, prices = load_snapshot(dataset_id, root)
    as_of = as_of or manifest["last_date"]
    cutoff = validated_date(as_of, "Decision date")
    if cutoff > validated_date(manifest["last_date"], "Snapshot end"):
        raise DataQualityError("Decision date exceeds snapshot coverage")
    if cutoff < validated_date(manifest["first_date"], "Snapshot start"):
        raise DataQualityError("Decision date precedes snapshot coverage")
    sessions = manifest["sessions"]
    eligible, excluded = [], []
    mismatches = {r["symbol"] for r in manifest["crosscheck"].get("mismatches", [])}
    for row in members.sort_values("isin").itertuples():
        try:
            if row.symbol in mismatches and as_of == manifest["crosscheck"]["date"]:
                raise DataQualityError("Latest price disagrees with official NSE report")
            aligned_window(prices, [row.symbol], sessions, as_of)
            eligible.append(row.symbol)
        except DataQualityError as exc:
            excluded.append({"symbol": row.symbol, "reason": str(exc)})
    available = members[members.symbol.isin(eligible)].sort_values("isin")
    if symbols is not None:
        if len(symbols) != n or len(set(symbols)) != n or not set(symbols).issubset(eligible):
            raise DataQualityError("All selected stocks need complete eligible price windows")
        chosen = list(symbols)
    else:
        # Most represented industries first, ties by label; identities by ISIN.
        # Round robin across at least K industries; no return-based stock picking.
        groups = sorted(available.groupby("sector"), key=lambda pair: (-len(pair[1]), pair[0]))
        groups = groups[: max(k, (k + sector_limit - 1) // sector_limit)]
        queues = [list(frame.symbol) for _, frame in groups]
        chosen = []
        while len(chosen) < n and any(queues):
            for queue in queues:
                if queue and len(chosen) < n:
                    chosen.append(queue.pop(0))
        if len(chosen) < n:
            raise DataQualityError(f"Only {len(chosen)} eligible stocks in the deterministic sector pool")
    window = aligned_window(prices, chosen, sessions, as_of)
    returns = window.pct_change(fill_method=None).iloc[1:]
    mu = returns.mean().to_numpy() * 252
    covariance = LedoitWolf().fit(returns.to_numpy()).covariance_ * 252
    sectors = members.set_index("symbol").loc[chosen, "sector"].tolist()
    corr = returns.corr().to_numpy()
    features = {
        "volatility": float(np.mean(np.sqrt(np.diag(covariance)))),
        "correlation": float(corr[np.triu_indices(n, 1)].mean()) if n > 1 else 0.0,
        "n": float(n),
        "k_fraction": k / n,
        "sector_limit": float(sector_limit),
    }
    instance = PortfolioInstance(
        chosen,
        sectors,
        mu,
        covariance,
        k,
        {},
        {s: sector_limit for s in set(sectors)},
        risk_aversion,
        as_of,
        dataset_id,
        features,
    )
    audit = {
        "decision_date": as_of,
        "estimation_start": window.index[0],
        "estimation_end": window.index[-1],
        "return_observations": len(returns),
        "eligible_count": len(eligible),
        "excluded": excluded,
        "selected": chosen,
        "policy": "ISIN-sorted round robin across most represented eligible industries; no return ranking",
        "covariance": "Ledoit-Wolf shrinkage, annualized with 252 sessions",
        "membership_mode": "current_snapshot",
        "warning": "Current membership snapshot: optimization demonstration, not a bias-free historical NIFTY backtest",
    }
    return instance, audit
