"""Optional authentic frozen-snapshot integration (never synthesizes market data)."""

from pathlib import Path

import pytest


@pytest.mark.realdata
def test_actual_nifty_snapshot_quantum_classical_allocation():
    from qcompass.data.snapshots import list_snapshots

    snapshots = list_snapshots()
    if not snapshots:
        pytest.skip("Download a real snapshot first")
    dataset_id = snapshots[0]["dataset_id"]
    root = Path(__file__).resolve().parents[1]
    if not (root / "data/manifests" / f"{dataset_id}.json").exists():
        pytest.skip("Download the verified frozen NIFTY snapshot to run this integration.")
    from qcompass.data.prepare import build_instance
    from qcompass.quantum.solver import QuantumConfig, solve_qaoa
    from qcompass.classical.solvers import exact_select, scip_select
    from qcompass.classical.weights import allocate

    p, audit = build_instance(dataset_id, n=8, k=4, root=root)
    q = solve_qaoa(
        p, QuantumConfig("real-xy-p1", mixer="xy", optimizer="spsa"), evaluations=6, shots=128, seed=42
    )
    exact, scip = exact_select(p), scip_select(p)
    assert audit["return_observations"] == 252
    assert p.feasible(q["bits"])
    assert q["objective"] >= exact["objective"] - 1e-9
    assert scip["objective"] == pytest.approx(exact["objective"], abs=1e-6)
    assert q["shots_used"] == 896
    assert all(sum(map(int, bitstring)) == p.k for bitstring in q["counts"])
    assert allocate(p, q["bits"])["violations"] == []
