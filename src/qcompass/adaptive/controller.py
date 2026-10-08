from dataclasses import asdict
from datetime import date
from time import perf_counter

import numpy as np

from qcompass.quantum.solver import QuantumConfig, solve_qaoa


def configuration_library():
    configs = []
    for depth in range(1, 5):
        for mixer in ("x", "xy"):
            for optimizer in ("cobyla", "spsa"):
                for alpha in (1.0, 0.25):
                    suffix = ("-spsa" if optimizer == "spsa" else "") + ("-cvar" if alpha < 1 else "")
                    configs.append(
                        QuantumConfig(
                            f"{mixer}-p{depth}{suffix}",
                            depth=depth,
                            mixer=mixer,
                            optimizer=optimizer,
                            alpha=alpha,
                        )
                    )
    return configs


class TemporalRanker:
    """Small decision tree serialized as JSON arrays; no executable pickle loading."""

    def __init__(self, max_depth=3):
        self.max_depth = max_depth
        self.features = []
        self.tree = None
        self.latest_training_date = None
        self.records = []

    def fit(self, records, target_as_of):
        from sklearn.tree import DecisionTreeClassifier

        target = date.fromisoformat(target_as_of)
        if not records:
            raise ValueError("Ranker requires prior training records.")
        for record in records:
            if record.get("split") != "train" or date.fromisoformat(record["as_of"]) >= target:
                raise ValueError("Only strictly earlier training records may train a target-date ranker.")
        self.features = sorted({k for record in records for k in record.get("features", {})})
        self.latest_training_date = max(record["as_of"] for record in records)
        self.records = [dict(record) for record in records]
        # A constant feature allows an honest majority baseline when no features are supplied.
        x = np.array(
            [[float(r.get("features", {}).get(k, 0.0)) for k in self.features] or [0.0] for r in records]
        )
        if not np.isfinite(x).all():
            raise ValueError("Ranker features must be finite.")
        y = [r["best_config"] for r in records]
        estimator = DecisionTreeClassifier(max_depth=self.max_depth, random_state=42, min_samples_leaf=2)
        estimator.fit(x, y)
        tree = estimator.tree_
        self.tree = dict(
            left=tree.children_left.tolist(),
            right=tree.children_right.tolist(),
            feature=tree.feature.tolist(),
            threshold=tree.threshold.tolist(),
            labels=estimator.classes_.tolist(),
            values=tree.value[:, 0, :].tolist(),
        )
        return self

    def predict(self, instance):
        if self.tree is None:
            return None
        if not instance.as_of or date.fromisoformat(self.latest_training_date) >= date.fromisoformat(
            instance.as_of
        ):
            raise ValueError("Ranker training dates must precede the target date.")
        values = [float(instance.features.get(k, 0.0)) for k in self.features] or [0.0]
        node = 0
        while self.tree["left"][node] != -1:
            node = (
                self.tree["left"][node]
                if values[self.tree["feature"][node]] <= self.tree["threshold"][node]
                else self.tree["right"][node]
            )
        return self.tree["labels"][int(np.argmax(self.tree["values"][node]))]

    def warm_start(self, instance, config):
        from qcompass.quantum.model import build_qubo

        self.predict(instance)  # validate the target chronology even if no compatible record exists
        encoded_qubits = build_qubo(instance, config.penalty_multiplier).num_qubits
        for record in sorted(self.records, key=lambda r: r["as_of"], reverse=True):
            if record.get("split") != "train" or record["as_of"] >= instance.as_of:
                continue
            recorded_config = record.get("config", {})
            params = record.get("parameters")
            if (
                record.get("n") == instance.n
                and record.get("num_qubits") == encoded_qubits
                and recorded_config.get("depth") == config.depth
                and recorded_config.get("mixer") == config.mixer
                and recorded_config.get("alpha", 1.0) == config.alpha
                and recorded_config.get("penalty_multiplier", 1.0) == config.penalty_multiplier
                and params is not None
                and len(params) == 2 * config.depth
                and np.isfinite(params).all()
            ):
                return list(params)
        return None

    def to_dict(self):
        return dict(
            schema_version=1,
            max_depth=self.max_depth,
            features=self.features,
            tree=self.tree,
            latest_training_date=self.latest_training_date,
            records=self.records,
        )

    @classmethod
    def from_dict(cls, data):
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported ranker schema.")
        ranker = cls(data["max_depth"])
        ranker.features = list(data["features"])
        ranker.tree = data["tree"]
        ranker.latest_training_date = data["latest_training_date"]
        ranker.records = data["records"]
        return ranker


def adaptive_solve(
    instance,
    configs=None,
    evaluations=60,
    pilot_evaluations=10,
    shots=1024,
    seed=42,
    progress=None,
    cancel=None,
    max_seconds=300,
    ranker=None,
):
    if not isinstance(evaluations, int) or evaluations < 0 or pilot_evaluations < 1:
        raise ValueError("Nonnegative total budget and positive pilot budget required.")
    configs = configs if configs is not None else [QuantumConfig("x-p1"), QuantumConfig("x-p2", depth=2)]
    configs = [QuantumConfig(**c) if isinstance(c, dict) else c for c in configs]
    if not configs or len({c.name for c in configs}) != len(configs):
        raise ValueError("Provide configurations with unique names.")
    if 0 < evaluations < len(configs):
        raise ValueError("The budget must pilot every candidate configuration")
    start = perf_counter()
    prior_choice = ranker.predict(instance) if ranker else None
    if prior_choice:
        configs = sorted(configs, key=lambda c: c.name != prior_choice)
    runs, used = [], 0
    halted = None
    for index, config in enumerate(configs):
        if cancel and cancel():
            halted = "cancelled"
            break
        remaining_seconds = max_seconds - (perf_counter() - start)
        if remaining_seconds <= 0:
            halted = "time_limit"
            break
        remaining = evaluations - used
        if remaining <= 0:
            break
        # Share very small budgets fairly; otherwise use the specified pilot allocation.
        budget = min(pilot_evaluations, max(1, remaining // (len(configs) - index)))
        initial = ranker.warm_start(instance, config) if ranker else None
        result = solve_qaoa(
            instance,
            config,
            evaluations=budget,
            shots=shots,
            seed=seed + index * 1009,
            initial_point=initial,
            progress=progress,
            cancel=cancel,
            max_seconds=remaining_seconds,
        )
        runs.append(result)
        used += result["evaluations"]
        if result["status"] in ("cancelled", "time_limit"):
            halted = result["status"]
            break
    pilots = list(runs)
    if not pilots:
        empty = solve_qaoa(
            instance,
            configs[0],
            evaluations=0,
            shots=shots,
            seed=seed,
            cancel=cancel,
            max_seconds=max_seconds,
        )
        empty.update(
            method="adaptive",
            pilots=[],
            decision="No pilot completed within the available budget.",
            seconds=perf_counter() - start,
            status=halted or empty["status"],
        )
        return empty

    # Penalized energy scales differ across configurations. Rank solely by ORIGINAL
    # feasible objective, then feasible fraction; no exact solution is consulted.
    def score(result):
        return (
            result["objective"] is None,
            result["objective"] if result["objective"] is not None else float("inf"),
            -result["feasible_fraction"],
        )

    chosen = min(pilots, key=score)
    chosen_config = QuantumConfig(**chosen["config"])
    decision = (
        f"Selected {chosen_config.name} using pilot original feasible objectives and feasible fraction. "
        "Penalized energies were not compared across configurations; no exact oracle was used."
    )
    remaining = evaluations - used
    if not halted and remaining > 0 and chosen["parameters"]:
        continuation = solve_qaoa(
            instance,
            chosen_config,
            evaluations=remaining,
            shots=shots,
            seed=seed + 100_003,
            initial_point=chosen["parameters"],
            progress=progress,
            cancel=cancel,
            max_seconds=max(0, max_seconds - (perf_counter() - start)),
        )
        runs.append(continuation)
        if continuation["status"] in ("cancelled", "time_limit"):
            halted = continuation["status"]
    winner = min(runs, key=score)
    output = dict(winner)
    output["metadata"] = dict(winner["metadata"])
    output.update(
        method="adaptive",
        pilots=pilots,
        decision=decision,
        config=asdict(chosen_config),
        parameters=winner["parameters"],
        evaluations=sum(r["evaluations"] for r in runs),
        shots_used=sum(r["shots_used"] for r in runs),
        seconds=perf_counter() - start,
        trace=[
            dict(entry, run=i, config=r["config"]["name"]) for i, r in enumerate(runs) for entry in r["trace"]
        ],
        status=halted or winner["status"],
    )
    output["metadata"].update(
        total_final_sampling_shots=sum(r["metadata"]["final_sampling_shots"] for r in runs),
        total_final_sampling_seconds=sum(r["metadata"]["final_sampling_seconds"] for r in runs),
        total_optimizer_requests=sum(r["metadata"]["optimizer_requests"] for r in runs),
        chosen_config=chosen_config.name,
        ranker_suggestion=prior_choice,
        result_source=winner["config"]["name"],
        continuation_parameters=runs[-1]["parameters"] if len(runs) > len(pilots) else None,
        runs=len(runs),
        selection_rule="best original feasible objective observed across included runs",
    )
    return output
