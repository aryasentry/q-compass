"""Budgeted, seeded CPU QAOA with explicit circuits and measured sample costs."""

from dataclasses import asdict, dataclass
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from qcompass.classical.solvers import greedy_select
from .model import build_qubo


@dataclass
class QuantumConfig:
    name: str
    depth: int = 1
    mixer: str = "x"
    optimizer: str = "cobyla"
    alpha: float = 1.0
    penalty_multiplier: float = 1.0
    initial_point: list[float] | None = None
    noise: float = 0.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("A configuration needs a nonempty name")
        if not isinstance(self.depth, int) or not 1 <= self.depth <= 4:
            raise ValueError("Depth must be an integer from 1 to 4.")
        if self.mixer not in ("x", "xy") or self.optimizer not in ("cobyla", "spsa"):
            raise ValueError("Supported mixers x/xy and optimizers cobyla/spsa.")
        if not 0 < self.alpha <= 1 or not 0 <= self.noise < 1:
            raise ValueError("Require 0 < alpha <= 1 and 0 <= noise < 1.")
        if not np.isfinite(self.penalty_multiplier) or self.penalty_multiplier <= 0:
            raise ValueError("Penalty multiplier must be finite and positive")
        if self.initial_point is not None:
            value = np.asarray(self.initial_point, dtype=float)
            if value.shape != (2 * self.depth,) or not np.isfinite(value).all():
                raise ValueError("Initial point must contain two finite angles per layer")
            self.initial_point = value.tolist()


class _Stop(Exception):
    pass


def build_circuit(instance, encoded, config):
    """Return parameterized QAOA and explicit [gamma0,beta0,...] ordering."""
    circuit = QuantumCircuit(encoded.num_qubits)
    params = ParameterVector("theta", 2 * config.depth)
    if config.mixer == "x":
        circuit.h(range(encoded.num_qubits))
    else:
        start = greedy_select(instance)["bits"]
        for i, bit in enumerate(start):
            if bit:
                circuit.x(encoded.asset_indices[i])
        for q in range(encoded.num_qubits):
            if q not in encoded.asset_indices:
                circuit.h(q)
    terms = encoded.operator.to_list()
    for layer in range(config.depth):
        gamma, beta = params[2 * layer], params[2 * layer + 1]
        for pauli, coefficient in terms:
            indices = [i for i, value in enumerate(pauli[::-1]) if value == "Z"]
            angle = 2 * float(np.real(coefficient)) * gamma
            if len(indices) == 1:
                circuit.rz(angle, indices[0])
            elif len(indices) == 2:
                circuit.rzz(angle, *indices)
            elif len(indices) > 2:
                raise ValueError("Expected a quadratic Ising model.")
        if config.mixer == "x":
            for q in range(encoded.num_qubits):
                circuit.rx(2 * beta, q)
        else:
            ids = encoded.asset_indices
            pairs = list(zip(ids[:-1], ids[1:]))
            if len(ids) > 2:
                pairs.append((ids[-1], ids[0]))
            for a, b in pairs:
                circuit.rxx(beta, a, b)
                circuit.ryy(beta, a, b)
            for q in range(encoded.num_qubits):
                if q not in ids:
                    circuit.rx(2 * beta, q)
    circuit.measure_all()
    return circuit, list(params)


def _cvar(counts, encoded, alpha):
    values = sorted(
        (encoded.evaluate([int(v) for v in key.replace(" ", "")[::-1]]), count)
        for key, count in counts.items()
    )
    remaining = total = alpha * sum(counts.values())
    weighted = 0.0
    for value, count in values:
        used = min(remaining, count)
        weighted += used * value
        remaining -= used
        if remaining <= 1e-10:
            break
    return float(weighted / total)


def solve_qaoa(
    instance,
    config,
    evaluations=40,
    shots=1024,
    seed=42,
    initial_point=None,
    progress=None,
    cancel=None,
    max_seconds=300,
    max_qubits=20,
):
    from scipy.optimize import minimize
    import warnings

    if isinstance(config, dict):
        config = QuantumConfig(**config)
    if evaluations < 0 or not isinstance(evaluations, int) or shots <= 0 or not isinstance(shots, int):
        raise ValueError("Require nonnegative integer evaluations and positive integer shots.")
    start = perf_counter()
    metadata = dict(
        backend="AerSimulator",
        max_parallel_threads=4,
        max_memory_mb=4096,
        final_sampling_shots=0,
        final_sampling_seconds=0.0,
        optimizer_requests=0,
        xy_cardinality_preserved=config.mixer == "xy" and config.noise == 0,
        xy_sector_constraints_guaranteed=False,
        noise=config.noise,
    )
    result = dict(
        method=config.name,
        status="not_started",
        bits=None,
        objective=None,
        seconds=0.0,
        feasible_fraction=0.0,
        shots_used=0,
        evaluations=0,
        num_qubits=0,
        depth=config.depth,
        parameters=[],
        trace=[],
        counts={},
        config=asdict(config),
        metadata=metadata,
    )

    def stopped():
        if cancel is not None and cancel():
            result["status"] = "cancelled"
            return True
        if perf_counter() - start >= max_seconds:
            result["status"] = "time_limit"
            return True
        return False

    if stopped() or evaluations == 0:
        if result["status"] == "not_started":
            result["status"] = "budget_exhausted"
        result["seconds"] = perf_counter() - start
        return result
    encoded = build_qubo(instance, config.penalty_multiplier)
    result["num_qubits"] = encoded.num_qubits
    metadata.update(
        penalty=encoded.penalty,
        asset_qubits=instance.n,
        slack_qubits=encoded.num_qubits - instance.n,
        offset=encoded.offset,
    )
    if encoded.num_qubits > max_qubits:
        result["status"] = "qubit_limit"
        result["seconds"] = perf_counter() - start
        return result
    backend_args = dict(method="statevector", max_parallel_threads=4, max_memory_mb=4096)
    if config.noise:
        noise = NoiseModel()
        noise.add_all_qubit_quantum_error(depolarizing_error(config.noise, 1), ["x", "sx", "rz"])
        noise.add_all_qubit_quantum_error(depolarizing_error(config.noise, 2), ["cx"])
        backend_args["noise_model"] = noise
    backend = AerSimulator(**backend_args)
    circuit, parameters = build_circuit(instance, encoded, config)
    compiled = transpile(
        circuit, basis_gates=["x", "sx", "rz", "cx"], optimization_level=1, seed_transpiler=seed
    )
    rng = np.random.default_rng(seed)
    candidate = initial_point if initial_point is not None else config.initial_point
    theta = np.asarray(candidate if candidate is not None else rng.uniform(0, np.pi, 2 * config.depth), float)
    if theta.shape != (2 * config.depth,) or not np.isfinite(theta).all():
        raise ValueError("Initial point must contain two finite angles per layer.")
    best_theta, best_energy = theta.copy(), float("inf")

    def sample(point, sampling_seed):
        bound = compiled.assign_parameters(dict(zip(parameters, point)))
        counts = backend.run(bound, shots=shots, seed_simulator=int(sampling_seed)).result().get_counts()
        return {key.replace(" ", ""): int(value) for key, value in counts.items()}

    def evaluate(point):
        nonlocal best_theta, best_energy
        metadata["optimizer_requests"] += 1
        if stopped():
            raise _Stop()
        if result["evaluations"] >= evaluations:
            raise _Stop()
        counts = sample(point, seed + result["evaluations"])
        energy = _cvar(counts, encoded, config.alpha)
        result["evaluations"] += 1
        result["shots_used"] += shots
        if energy < best_energy:
            best_energy, best_theta = energy, np.array(point).copy()
        feasible = [
            (instance.objective(encoded.decode(key)), value)
            for key, value in counts.items()
            if instance.feasible(encoded.decode(key))
        ]
        entry = dict(
            evaluation=result["evaluations"],
            penalized_cvar=energy,
            feasible_fraction=sum(v for _, v in feasible) / shots,
            best_feasible_objective=min((v for v, _ in feasible), default=None),
            seconds=perf_counter() - start,
            parameters=np.asarray(point).tolist(),
        )
        result["trace"].append(entry)
        if progress:
            progress(dict(entry, method=config.name, phase="optimization"))
        return energy

    try:
        if config.optimizer == "cobyla":
            # Wrapper is authoritative: COBYLA may request its own larger minimum budget.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Invalid MAXFUN.*")
                minimize(
                    evaluate,
                    theta,
                    method="COBYLA",
                    options={"maxiter": max(evaluations, len(theta) + 2), "rhobeg": 0.5, "tol": 1e-5},
                )
            # If convergence occurs early, spend remaining budget on reproducible local exploration.
            while result["evaluations"] < evaluations:
                evaluate(best_theta + rng.normal(0, 0.05, size=len(theta)))
        else:
            evaluate(theta)
            iteration = 0
            while result["evaluations"] < evaluations:
                if evaluations - result["evaluations"] == 1:
                    evaluate(theta)  # spend an odd remainder on the actual updated candidate
                    metadata["spsa_unpaired_candidate_evaluations"] = 1
                    break
                iteration += 1
                delta = rng.choice([-1.0, 1.0], size=len(theta))
                c = 0.15 / iteration**0.101
                plus = evaluate(theta + c * delta)
                if result["evaluations"] >= evaluations:
                    break
                minus = evaluate(theta - c * delta)
                gradient = (plus - minus) / (2 * c) * delta
                theta = (theta - 0.12 / iteration**0.602 * gradient) % (2 * np.pi)
    except _Stop:
        pass
    result["parameters"] = best_theta.tolist()
    metadata["best_penalized_cvar"] = best_energy if np.isfinite(best_energy) else None
    if stopped():
        result["seconds"] = perf_counter() - start
        return result
    final_start = perf_counter()
    counts = sample(best_theta, seed + 1_000_000)
    metadata["final_sampling_seconds"] = perf_counter() - final_start
    metadata["final_sampling_shots"] = shots
    result["shots_used"] += shots
    result["counts"] = counts
    feasible = [
        (instance.objective(encoded.decode(key)), encoded.decode(key), value)
        for key, value in counts.items()
        if instance.feasible(encoded.decode(key))
    ]
    result["feasible_fraction"] = sum(value for _, _, value in feasible) / shots
    if feasible:
        value, bits, _ = min(feasible, key=lambda item: (item[0], item[1]))
        result.update(bits=bits, objective=value, status="completed")
    else:
        result["status"] = "no_feasible_samples"
    result["seconds"] = perf_counter() - start
    if progress:
        progress(
            dict(
                method=config.name,
                phase="complete",
                evaluations=result["evaluations"],
                feasible_fraction=result["feasible_fraction"],
                seconds=result["seconds"],
            )
        )
    return result
