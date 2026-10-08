from dataclasses import dataclass

import numpy as np
from qiskit.quantum_info import SparsePauliOp
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo


@dataclass
class EncodedProblem:
    operator: SparsePauliOp
    offset: float
    num_qubits: int
    asset_indices: list[int]
    qubo: QuadraticProgram
    converter: QuadraticProgramToQubo
    penalty: float

    def evaluate(self, bits):
        x = np.asarray(bits, dtype=float)
        if x.shape != (self.num_qubits,) or not np.isin(x, [0, 1]).all():
            raise ValueError("Expected a binary vector covering asset AND slack variables.")
        return float(self.qubo.objective.evaluate(x))

    def decode(self, bitstring):
        """Aer/Qiskit count strings are MSB-left; assets are original QP variables."""
        text = bitstring.replace(" ", "")
        if len(text) != self.num_qubits or set(text) - {"0", "1"}:
            raise ValueError("Count string must cover the encoded register.")
        little = [int(v) for v in text[::-1]]
        return [little[i] for i in self.asset_indices]


def build_qubo(instance, penalty_multiplier=1.0):
    if not np.isfinite(penalty_multiplier) or penalty_multiplier <= 0:
        raise ValueError("Penalty multiplier must be positive and finite.")
    p = QuadraticProgram("equal_weight_subset")
    for i in range(instance.n):
        p.binary_var(name=f"asset_{i}")
    linear = -instance.mu / instance.k
    quadratic = instance.risk_aversion * instance.covariance / instance.k**2
    p.minimize(linear=linear, quadratic=quadratic)
    p.linear_constraint({f"asset_{i}": 1 for i in range(instance.n)}, "==", instance.k, "cardinality")
    for number, sector in enumerate(sorted(set(instance.sectors))):
        ids = [i for i in range(instance.n) if instance.sectors[i] == sector]
        low = instance.sector_min.get(sector, 0)
        high = min(instance.sector_max.get(sector, len(ids)), len(ids))
        expression = {f"asset_{i}": 1 for i in ids}
        if low == high:
            p.linear_constraint(expression, "==", low, f"sector_{number}_equal")
        else:
            if low > 0:
                p.linear_constraint(expression, ">=", low, f"sector_{number}_min")
            if high < len(ids):
                p.linear_constraint(expression, "<=", high, f"sector_{number}_max")
    # This exceeds the objective's total range, so multiplier >=1 makes any unit
    # constraint violation cost more than any improvement in the original objective.
    penalty = float((1 + np.abs(linear).sum() + np.abs(quadratic).sum()) * penalty_multiplier)
    converter = QuadraticProgramToQubo(penalty=penalty)
    qubo = converter.convert(p)
    operator, offset = qubo.to_ising()
    lookup = {v.name: i for i, v in enumerate(qubo.variables)}
    return EncodedProblem(
        operator,
        float(offset),
        qubo.get_num_vars(),
        [lookup[f"asset_{i}"] for i in range(instance.n)],
        qubo,
        converter,
        penalty,
    )
