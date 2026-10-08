"""Validated annualized, equal-weight subset-selection problem."""

from dataclasses import asdict, dataclass, field

import numpy as np


class InfeasibleProblem(ValueError):
    """The specified hard constraints have no possible solution."""


@dataclass
class PortfolioInstance:
    symbols: list[str]
    sectors: list[str]
    mu: np.ndarray
    covariance: np.ndarray
    k: int
    sector_min: dict[str, int]
    sector_max: dict[str, int]
    risk_aversion: float = 1.0
    as_of: str = ""
    dataset_id: str = ""
    features: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.symbols, self.sectors = list(self.symbols), list(self.sectors)
        self.mu = np.asarray(self.mu, dtype=float)
        self.covariance = np.asarray(self.covariance, dtype=float)
        if not self.n or len(set(self.symbols)) != self.n or len(self.sectors) != self.n:
            raise ValueError("Symbols must be unique and nonempty; sectors must align.")
        if self.mu.shape != (self.n,) or self.covariance.shape != (self.n, self.n):
            raise ValueError("Expected mu[n] and covariance[n,n].")
        if not np.isfinite(self.mu).all() or not np.isfinite(self.covariance).all():
            raise ValueError("Nonfinite moments.")
        if not np.allclose(self.covariance, self.covariance.T, atol=1e-10, rtol=1e-8):
            raise ValueError("Covariance must be symmetric.")
        if np.linalg.eigvalsh(self.covariance).min() < -1e-9:
            raise ValueError("Covariance must be positive semidefinite.")
        if not np.isfinite(self.risk_aversion) or self.risk_aversion < 0:
            raise ValueError("Risk aversion must be finite and nonnegative.")
        if not isinstance(self.k, (int, np.integer)) or not 1 <= self.k <= self.n:
            raise InfeasibleProblem("Require integer 1 <= K <= N.")
        keys = set(self.sectors) | self.sector_min.keys() | self.sector_max.keys()
        lo, hi = 0, 0
        for sector in keys:
            available = self.sectors.count(sector)
            low, high = self.sector_min.get(sector, 0), self.sector_max.get(sector, available)
            if any(not isinstance(v, (int, np.integer)) or v < 0 for v in (low, high)):
                raise ValueError("Sector count bounds must be nonnegative integers.")
            if low > high or low > available:
                raise InfeasibleProblem(f"Impossible sector count bounds: {sector}.")
            lo += low
            hi += min(high, available)
        if lo > self.k or hi < self.k:
            raise InfeasibleProblem("Sector bounds cannot achieve K selections.")

    @property
    def n(self):
        return len(self.symbols)

    def objective(self, bits):
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.n,):
            raise ValueError("Selection dimension mismatch.")
        return float(self.risk_aversion * x @ self.covariance @ x / self.k**2 - self.mu @ x / self.k)

    def violations(self, bits):
        try:
            x = np.asarray(bits, dtype=float)
        except (TypeError, ValueError):
            return ["selection must be a binary vector"]
        if x.shape != (self.n,) or not np.isfinite(x).all():
            return ["selection dimension/nonfinite violation"]
        errors = []
        if not np.isin(x, [0, 1]).all():
            errors.append("selection must be binary")
        if x.sum() != self.k:
            errors.append(f"cardinality: expected {self.k}, got {x.sum():g}")
        for s in sorted(set(self.sectors) | self.sector_min.keys() | self.sector_max.keys()):
            count = sum(x[i] for i, sector in enumerate(self.sectors) if sector == s)
            if count < self.sector_min.get(s, 0):
                errors.append(f"sector minimum: {s}")
            if count > self.sector_max.get(s, self.n):
                errors.append(f"sector maximum: {s}")
        return errors

    def feasible(self, bits):
        return not self.violations(bits)

    def to_dict(self):
        value = asdict(self)
        value["mu"] = self.mu.tolist()
        value["covariance"] = self.covariance.tolist()
        value["k"] = int(self.k)
        value["sector_min"] = {s: int(v) for s, v in self.sector_min.items()}
        value["sector_max"] = {s: int(v) for s, v in self.sector_max.items()}
        return value

    @classmethod
    def from_dict(cls, value):
        return cls(**value)
