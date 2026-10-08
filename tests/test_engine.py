"""Small hand-checkable algebra fixtures; these are NOT market-price data."""

import itertools
import json

import numpy as np
import pytest


def instance():
    from qcompass.portfolio.models import PortfolioInstance

    return PortfolioInstance(
        ["a", "b", "c", "d"],
        ["s", "s", "t", "t"],
        np.array([0.1, 0.2, 0.05, 0.15]),
        np.eye(4) * 0.04,
        2,
        {"s": 1, "t": 1},
        {"s": 1, "t": 1},
        as_of="2024-01-01",
    )


def test_selection_objective_and_roundtrip():
    from qcompass.portfolio.models import PortfolioInstance

    p = instance()
    assert p.objective([0, 1, 0, 1]) == pytest.approx(-0.155)
    assert p.feasible([0, 1, 0, 1])
    assert not p.feasible([1, 1, 0, 0])
    assert not p.feasible([0, 0.5, 0.5, 1])
    assert PortfolioInstance.from_dict(json.loads(json.dumps(p.to_dict()))).n == 4


def test_reject_impossible_and_non_psd():
    from qcompass.portfolio.models import PortfolioInstance, InfeasibleProblem

    d = instance().to_dict()
    d["sector_min"] = {"s": 2, "t": 1}
    with pytest.raises(InfeasibleProblem):
        PortfolioInstance.from_dict(d)
    d = instance().to_dict()
    d["covariance"][0][0] = -1
    with pytest.raises(ValueError):
        PortfolioInstance.from_dict(d)


def test_exact_scip_and_greedy_feasible():
    from qcompass.classical.solvers import exact_select, scip_select, greedy_select

    p = instance()
    e, s, g = exact_select(p), scip_select(p), greedy_select(p)
    assert e["bits"] == [0, 1, 0, 1]
    assert e["certified"] and s["certified"]
    assert s["objective"] == pytest.approx(e["objective"], abs=1e-6)
    assert p.feasible(g["bits"])


def test_allocation_caps_forced_sales_and_joint():
    from qcompass.classical.weights import allocate, continuous_mvo, joint_select_weights

    p = instance()
    a = allocate(p, [0, 1, 0, 1], sector_caps={"s": 0.5, "t": 0.6})
    assert a["status"] == "optimal"
    assert a["weights"] == pytest.approx([0, 0.5, 0, 0.5], abs=1e-5)
    # All previous capital in a delisted/outside-universe asset requires turnover=1.
    bad = allocate(p, [0, 1, 0, 1], previous_weights={"outside": 1}, turnover_limit=0.9)
    assert bad["weights"] is None and bad["status"] == "infeasible"
    ok = allocate(p, [0, 1, 0, 1], previous_weights={"outside": 1}, turnover_limit=1)
    assert ok["turnover"] == pytest.approx(1)
    assert continuous_mvo(p)["weights"] is not None
    joint = joint_select_weights(p)
    assert p.feasible(joint["bits"])
    assert sum(joint["weights"]) == pytest.approx(1, abs=1e-5)


def test_qubo_full_energy_and_endian():
    from qcompass.quantum.model import build_qubo

    p = instance()
    q = build_qubo(p)
    diagonal = np.real(np.diag(q.operator.to_matrix())) + q.offset
    for bits in itertools.product([0, 1], repeat=q.num_qubits):
        index = sum(b << i for i, b in enumerate(bits))
        assert q.evaluate(bits) == pytest.approx(diagonal[index], abs=1e-9)
        assert q.decode("".join(map(str, bits[::-1]))) == list(bits[: p.n])
    feasible_energies = [
        q.evaluate(x) for x in itertools.product([0, 1], repeat=q.num_qubits) if p.feasible(x[: p.n])
    ]
    assert min(feasible_energies) == pytest.approx(-0.155)


def test_seeded_qaoa_budget_xy_and_cancel():
    from qcompass.quantum.solver import QuantumConfig, solve_qaoa

    p = instance()
    c = QuantumConfig("xy-test", mixer="xy", optimizer="spsa")
    a = solve_qaoa(p, c, evaluations=4, shots=64, seed=2)
    b = solve_qaoa(p, c, evaluations=4, shots=64, seed=2)
    assert a["counts"] == b["counts"]
    assert a["evaluations"] == 4
    assert a["shots_used"] == 64 * 5
    assert all(sum(int(x) for x in key[-4:]) == 2 for key in a["counts"])
    stopped = solve_qaoa(p, c, evaluations=4, shots=64, cancel=lambda: True)
    assert stopped["status"] == "cancelled" and stopped["evaluations"] == 0


def test_adaptive_budget_and_ranker_temporal_gate():
    from qcompass.adaptive.controller import adaptive_solve, TemporalRanker

    p = instance()
    with pytest.raises(ValueError):
        adaptive_solve(p, evaluations=1, shots=32)
    a = adaptive_solve(p, evaluations=9, pilot_evaluations=2, shots=32, seed=3)
    assert a["evaluations"] == 9
    assert len(a["pilots"]) == 2
    assert a["shots_used"] == 32 * 12
    source = next(p for p in a["pilots"] if p["counts"] == a["counts"])
    assert a["parameters"] == source["parameters"]
    ranker = TemporalRanker()
    with pytest.raises(ValueError):
        ranker.fit(
            [{"as_of": "2024-01-01", "split": "train", "features": {}, "best_config": "x-p1"}],
            target_as_of="2024-01-01",
        )


def test_quantum_config_numpy_start_serializes():
    from qcompass.quantum.solver import QuantumConfig, solve_qaoa
    from qcompass.adaptive.controller import TemporalRanker

    ranker = TemporalRanker()
    c = QuantumConfig("array-start", initial_point=np.array([0.1, 0.2]))
    result = solve_qaoa(instance(), c, evaluations=2, shots=32)
    assert json.loads(json.dumps(result))["config"]["initial_point"] == [0.1, 0.2]
    with pytest.raises(ValueError):
        ranker.fit(
            [{"as_of": "2023-01-01", "split": "test", "features": {}, "best_config": "x-p1"}],
            target_as_of="2024-01-01",
        )


def test_slack_encoded_minimum_matches_original_and_invalid_binary_rejected():
    from qcompass.quantum.model import build_qubo
    from qcompass.portfolio.models import PortfolioInstance

    p = PortfolioInstance(
        list("abcdef"), ["s"] * 4 + ["t"] * 2, np.arange(6) * 0.01, np.eye(6) * 0.04, 3, {"s": 1}, {"s": 2}
    )
    q = build_qubo(p)
    assert q.num_qubits > p.n
    diagonal = np.real(np.diag(q.operator.to_matrix())) + q.offset
    minima = {}
    for x in itertools.product([0, 1], repeat=q.num_qubits):
        value = q.evaluate(x)
        index = sum(b << i for i, b in enumerate(x))
        assert value == pytest.approx(diagonal[index], abs=1e-9)
        minima[x[: p.n]] = min(value, minima.get(x[: p.n], float("inf")))
    for x, value in minima.items():
        # Original constraint penalty has a realizable slack for every feasible selection.
        if p.feasible(x):
            assert value == pytest.approx(p.objective(x))
        else:
            assert value >= p.objective(x) + q.penalty - 1e-8
    with pytest.raises(ValueError):
        q.evaluate([0.5] * q.num_qubits)


def test_ranker_roundtrip_and_warm_start_encoded_dimensions():
    from qcompass.adaptive.controller import TemporalRanker
    from qcompass.quantum.solver import QuantumConfig

    record = dict(
        as_of="2023-01-01",
        split="train",
        features={"vol": 0.2},
        best_config="x-p1",
        config={"depth": 1, "mixer": "x"},
        n=4,
        num_qubits=99,
        parameters=[0.1, 0.2],
    )
    ranker = TemporalRanker().fit([record], target_as_of="2024-01-01")
    ranker = TemporalRanker.from_dict(json.loads(json.dumps(ranker.to_dict())))
    assert ranker.predict(instance()) == "x-p1"
    assert ranker.warm_start(instance(), QuantumConfig("x-p1")) is None
    record["num_qubits"] = 4
    ranker.fit([record], target_as_of="2024-01-01")
    assert ranker.warm_start(instance(), QuantumConfig("x-p1")) == [0.1, 0.2]
    p = instance()
    p.as_of = "2022-01-01"
    with pytest.raises(ValueError):
        ranker.predict(p)


def test_quantum_cap_cvar_noise_and_adaptive_cancel():
    from qcompass.quantum.solver import QuantumConfig, solve_qaoa, _cvar
    from qcompass.quantum.model import build_qubo
    from qcompass.adaptive.controller import adaptive_solve

    p = instance()
    q = build_qubo(p)
    assert _cvar({"1010": 1, "1001": 3}, q, 0.25) == pytest.approx(-0.155)
    limited = solve_qaoa(p, QuantumConfig("limit"), evaluations=2, max_qubits=3)
    assert limited["status"] == "qubit_limit" and limited["shots_used"] == 0
    noisy = solve_qaoa(p, QuantumConfig("noise", noise=0.01, alpha=0.25), evaluations=2, shots=16)
    assert sum(noisy["counts"].values()) == 16
    stopped = adaptive_solve(p, cancel=lambda: True, evaluations=5)
    assert stopped["status"] == "cancelled" and stopped["shots_used"] == 0
