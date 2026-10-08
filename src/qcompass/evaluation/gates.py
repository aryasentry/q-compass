"""Require explicit, complete evidence before permitting historical index claims.

This validates an upstream verification record; it does not infer verification
from a downloaded press release, a current constituent CSV, or adjusted prices.
"""

from datetime import date


class HistoricalEligibilityError(ValueError):
    pass


def _coverage(evidence, start, end, label):
    if not isinstance(evidence, dict) or evidence.get("verified") is not True:
        raise HistoricalEligibilityError(f"{label}: verified evidence is required.")
    try:
        first, last = (
            date.fromisoformat(evidence["coverage_start"]),
            date.fromisoformat(evidence["coverage_end"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoricalEligibilityError(f"{label}: dated coverage is required.") from exc
    if first > start or last < end or first > last:
        raise HistoricalEligibilityError(f"{label}: evidence does not cover the dataset interval.")


def strict_backtest_gate(manifest, membership_evidence=None):
    if manifest.get("membership_mode") not in ("historical_verified", "point_in_time"):
        raise HistoricalEligibilityError(
            "Current membership snapshots cannot support strict historical backtests."
        )
    if manifest.get("historical_membership_verified") is not True:
        raise HistoricalEligibilityError("Verified complete dated historical membership is required.")
    if manifest.get("corporate_actions_independently_verified") is not True:
        raise HistoricalEligibilityError("Independently verified corporate-action coverage is required.")
    try:
        start, end = date.fromisoformat(manifest["first_date"]), date.fromisoformat(manifest["last_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoricalEligibilityError("Manifest must specify the dated dataset interval.") from exc
    if start > end:
        raise HistoricalEligibilityError("Invalid dataset interval.")
    membership = (
        membership_evidence if membership_evidence is not None else manifest.get("membership_evidence")
    )
    _coverage(membership, start, end, "Membership")
    if membership.get("complete_history") is not True:
        raise HistoricalEligibilityError(
            "Membership evidence must attest complete history, not selected releases."
        )
    records = membership.get("records")
    if not isinstance(records, list) or not records:
        raise HistoricalEligibilityError("Dated full constituent records are required.")
    dates, universe = [], set()
    for record in records:
        try:
            effective = date.fromisoformat(record["effective_date"])
            symbols = record["symbols"]
            source = record["source"]
        except (KeyError, TypeError, ValueError) as exc:
            raise HistoricalEligibilityError(
                "Every membership record needs date, symbols and source."
            ) from exc
        if (
            not isinstance(symbols, list)
            or not symbols
            or any(not isinstance(s, str) or not s for s in symbols)
        ):
            raise HistoricalEligibilityError("Membership records must contain complete symbol lists.")
        if len(set(symbols)) != len(symbols) or not isinstance(source, str) or not source.strip():
            raise HistoricalEligibilityError("Membership symbols must be unique with source provenance.")
        if len(symbols) != 50:
            raise HistoricalEligibilityError("NIFTY 50 membership records must contain all 50 constituents")
        dates.append(effective)
        universe.update(symbols)
    if dates != sorted(set(dates)) or dates[0] > start:
        raise HistoricalEligibilityError(
            "Membership dates must be unique, ordered and begin before coverage."
        )
    corporate = manifest.get("corporate_action_evidence")
    _coverage(corporate, start, end, "Corporate actions")
    if corporate.get("coverage_complete") is not True:
        raise HistoricalEligibilityError("Corporate action coverage must include all relevant events.")
    sources = corporate.get("sources")
    if (
        not isinstance(sources, list)
        or not sources
        or any(not isinstance(s, str) or not s.strip() for s in sources)
    ):
        raise HistoricalEligibilityError("Corporate-action sources are required.")
    covered = corporate.get("symbols", [])
    if not isinstance(covered, list) or not universe.issubset(set(covered)):
        raise HistoricalEligibilityError("Corporate-action evidence does not cover every historical member.")
    return dict(
        eligible=True,
        mode="strict_historical",
        coverage_start=str(start),
        coverage_end=str(end),
        membership_records=len(records),
        historical_symbols=sorted(universe),
        verification_basis="upstream explicit complete membership and corporate-action verification",
    )
