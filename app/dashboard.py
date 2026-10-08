"""Thin interface. All numerical work runs in the package / exclusive worker."""

import json
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

from qcompass.data.snapshots import list_snapshots, load_snapshot
from qcompass.experiments.runner import RunConfig, comparison_table, read_result
from qcompass.experiments.store import JobStore
from qcompass.experiments.worker import start_worker
from qcompass.paths import project_root

st.set_page_config(page_title="Q-Compass · Portfolio lab", page_icon="🧭", layout="wide")
st.markdown(
    """<style>
.block-container {max-width:1280px;padding-top:4rem;padding-bottom:3rem}
h1 {font-size:2.35rem!important;letter-spacing:-.035em;font-weight:700!important}
h2 {font-size:1.5rem!important;letter-spacing:-.02em}
h3 {font-size:1.12rem!important}
[data-testid="stSidebar"] {border-right:1px solid #dde5ee}
[data-testid="stMetric"] {border:1px solid #dce5ed;border-radius:10px;padding:14px}
[data-testid="stMetricValue"] {font-size:1.6rem}
[data-testid="stTabs"] button {font-size:1rem}
.intro {color:#53657f;font-size:1.1rem;margin-top:-.4rem;margin-bottom:1.5rem}
.eyebrow {color:#00828e;font-size:.76rem;letter-spacing:.12em;font-weight:650;text-transform:uppercase}
</style>""",
    unsafe_allow_html=True,
)

root = project_root()
store = JobStore(root)
snapshots = list_snapshots(root)
with st.sidebar:
    st.markdown("## Q-Compass")
    st.caption("QUANTUM PORTFOLIO LAB")
    page = st.radio(
        "Workspace",
        ["Experiment", "Data audit", "Saved runs", "Research", "How it works"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Qiskit Aer · CPU simulation\n\nLocal research only. No live trading.")
    st.caption("One worker · 4 simulator threads\n\n20 encoded-qubit limit · 4 GiB Aer cap")


def result_paths():
    return sorted(
        (root / "artifacts/runs").glob("*/result.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )


def choose_result(key, kind=None):
    verified = {}
    for path in result_paths():
        try:
            result = read_result(path)
            if not isinstance(result, dict):
                raise ValueError("Expected a saved result object")
            if kind is None or result.get("kind") == kind:
                verified[path] = result
        except (ValueError, OSError) as exc:
            st.warning(f"Unreadable saved run {path.parent.name}: {exc}")
    paths = list(verified)
    if not paths:
        st.info("No saved results. Run an experiment to see measured results.")
        return None
    choice = st.selectbox("Saved run (replay only)", paths, key=key, format_func=lambda p: p.parent.name[:12])
    return verified[choice]


def show_results(result):
    if result is None:
        return
    if result.get("kind") == "fixed_universe_study":
        st.warning(
            "Fixed current-universe research study. This is not a bias-free historical NIFTY backtest."
        )
        curves = [
            {"Date": date, "Wealth": value, "Cost": f"{bps} bps"}
            for bps, scenario in result["cost_sensitivity"].items()
            for date, value in scenario["equity"].items()
        ]
        fig = px.line(
            pd.DataFrame(curves),
            x="Date",
            y="Wealth",
            color="Cost",
            color_discrete_sequence=["#008E99", "#315680", "#DBAA54"],
        )
        fig.update_layout(template="plotly_white", height=380)
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Cost bps": bps, **scenario["metrics"]}
                    for bps, scenario in result["cost_sensitivity"].items()
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Initial wealth = 1. Risk-free rate = 0. Costs apply to traded notional, including initial purchases."
        )
        with st.expander("Study settings and limitations"):
            st.json({"config": result["config"], "limitations": result["limitations"]})
        return
    if result.get("kind") != "optimization_comparison":
        st.json(result)
        return
    instance = result["instance"]
    st.caption(
        f"Saved run {result['run_id'][:12]} · Decision date {instance['as_of']} · Seed {result['config']['seed']}"
    )
    st.info(
        "Optimization comparison only. These are not realized investment returns or proof of quantum advantage."
    )
    table = comparison_table(result)
    visible = [
        "method",
        "objective",
        "objective_gap",
        "selection_feasible",
        "allocation_feasible",
        "feasible_fraction",
        "total_seconds",
        "shots_used",
    ]
    st.dataframe(
        table.reindex(columns=visible).rename(
            columns={
                "method": "Method",
                "objective": "Selection score ↓",
                "objective_gap": "Gap to exact ↓",
                "selection_feasible": "Selection valid",
                "allocation_feasible": "Weights valid",
                "feasible_fraction": "Valid quantum samples",
                "total_seconds": "Total seconds",
                "shots_used": "Total shots",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Lower selection scores are better. Gap is an absolute objective difference, not a return percentage. "
        "Valid quantum samples refers to the final sample distribution; adaptive shows its retained candidate."
    )
    rows = result["results"]
    weights = [
        {"Method": row["method"], "Stock": symbol, "Weight": weight}
        for row in rows
        if row.get("allocation_feasible")
        for symbol, weight in zip(instance["symbols"], row["allocation"]["weights"])
        if weight > 1e-7
    ]
    if weights:
        st.subheader("Investment allocation")
        figure = px.bar(
            pd.DataFrame(weights),
            x="Method",
            y="Weight",
            color="Stock",
            color_discrete_sequence=["#008E99", "#315680", "#84C9B5", "#DBAA54", "#8580BE", "#BA6688"],
        )
        figure.update_layout(
            template="plotly_white",
            height=360,
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis_tickformat=".0%",
            legend=dict(orientation="h", y=1.13),
            font=dict(family="Arial", color="#112344"),
            xaxis_title=None,
        )
        st.plotly_chart(figure, width="stretch")
        st.dataframe(
            pd.DataFrame(weights),
            hide_index=True,
            width="stretch",
            column_config={"Weight": st.column_config.NumberColumn(format="%.4f")},
        )
    with st.expander("Failures, constraints and allocation details"):
        st.json(
            [
                {
                    k: v
                    for k, v in r.items()
                    if k in ["method", "status", "error", "allocation", "selection_violations", "repaired"]
                }
                for r in rows
            ]
        )
    with st.expander("Continuous and joint classical references"):
        st.caption(
            "Continuous mean–variance optimization omits exact holding-count and sector-count rules. "
            "The joint classical reference optimizes selection and weights together. Neither is the same objective as the binary proxy."
        )
        st.json(result.get("allocation_references", {}))
    st.download_button(
        "Download comparison CSV",
        table.to_csv(index=False),
        f"qcompass-{result['run_id'][:12]}.csv",
        "text/csv",
        key="csv-" + result["run_id"],
    )


def show_controller(result):
    if result is None:
        st.info("An adaptive decision appears here after a real run.")
        return
    adaptive = next((r for r in result.get("results", []) if r["method"] == "adaptive"), None)
    if not adaptive:
        st.info("This run has no completed adaptive comparison.")
        return
    st.subheader("Why this configuration?")
    st.write(adaptive.get("decision", adaptive.get("error", "No decision available")))
    st.dataframe(
        pd.DataFrame(
            [
                {
                    k: p.get(k)
                    for k in [
                        "method",
                        "status",
                        "objective",
                        "feasible_fraction",
                        "evaluations",
                        "shots_used",
                    ]
                }
                for p in adaptive.get("pilots", [])
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    a, b, c = st.columns(3)
    a.metric("Total objective evaluations", adaptive.get("evaluations", 0))
    b.metric("Total shots, including pilots", adaptive.get("shots_used", 0))
    c.metric("Encoded qubits", adaptive.get("num_qubits", 0))
    st.caption(
        "Pilot-only tuning is active. A trained market-context tree requires earlier experiment records; "
        "the app does not pretend such a model has already been trained."
    )
    trace = pd.DataFrame(adaptive.get("trace", []))
    if not trace.empty:
        trace["Total evaluation"] = range(1, len(trace) + 1)
        figure = px.scatter(
            trace,
            x="Total evaluation",
            y="feasible_fraction",
            color="config",
            labels={"feasible_fraction": "Valid sample fraction"},
        )
        figure.update_layout(
            template="plotly_white", height=320, yaxis_tickformat=".0%", margin=dict(t=10, l=0, r=0, b=0)
        )
        st.plotly_chart(figure, width="stretch")
    with st.expander("Controller evidence and sampling budget"):
        st.json({"budget": result["budget"], "metadata": adaptive.get("metadata", {})})


@st.fragment(run_every=2)
def job_panel():
    jobs = store.list()
    active = [j for j in jobs if j["status"] in {"queued", "running"}]
    if active:
        st.subheader("Local worker")
    for job in active:
        st.write(
            f"{job['status'].capitalize()} · {job['config'].get('kind', 'experiment')} · {job['id'][:12]}"
        )
        events = store.events(job["id"])
        if events:
            st.caption(events[-1]["message"][:350])
        if st.button("Cancel run", key="cancel-" + job["id"]):
            store.cancel(job["id"])
            st.info("Cancellation requested. The current bounded calculation/download must finish first.")
    tracked = st.session_state.get("submitted_job")
    if tracked:
        job = store.get(tracked)
        if job and job["status"] not in {"queued", "running"}:
            st.write(f"Latest submitted job: **{job['status']}** · {job['id'][:12]}")
            if job["error"]:
                st.error(job["error"])
            if st.button("Refresh saved results", key="refresh-job"):
                st.rerun()


if page == "Experiment":
    st.markdown('<div class="eyebrow">SIMULATION WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Portfolio experiment")
    st.markdown('<div class="intro">Real NIFTY data. Local quantum simulation.</div>', unsafe_allow_html=True)
    setup, results_tab, controller, record = st.tabs(["Setup", "Results", "Controller", "Run record"])
    with setup:
        if not snapshots:
            st.info("No dataset is available. Open Data audit to download authentic stock histories.")
        else:
            with st.form("experiment-config"):
                snapshot = st.selectbox(
                    "Dataset snapshot",
                    snapshots,
                    format_func=lambda m: (
                        f"NIFTY 50 · through {m['last_date']} · {m['stock_count']} histories retained · {m['dataset_id'][-6:]}"
                    ),
                )
                left, right = st.columns(2, gap="large")
                with left:
                    n = st.selectbox(
                        "Candidate stocks",
                        [8, 10, 12],
                        help="Bigger experiments require profiling, including constraint qubits.",
                    )
                    k = st.number_input("Holdings to select", 1, n, 4)
                    risk = st.number_input("Risk aversion", 0.0, 100.0, 1.0, 0.25)
                with right:
                    sector = st.number_input("Maximum holdings per industry", 1, n, 1)
                    cap = st.slider("Maximum weight per selected stock", 0.1, 1.0, 0.5, 0.05)
                    seed = st.number_input("Random seed", 0, 100000, 42)
                with st.expander("Sampling budget and investment rules"):
                    a, b = st.columns(2)
                    with a:
                        batches = st.number_input("Sample batches per quantum method", 12, 256, 48)
                        shots = st.selectbox("Shots per batch", [128, 256, 512, 1024, 2048], index=2)
                        seconds = st.number_input("Seconds per quantum method", 5, 600, 180)
                    with b:
                        min_weight = st.slider("Minimum selected-stock weight", 0.01, 0.25, 0.05, 0.01)
                        sector_cap = st.slider("Maximum investment per industry", 0.1, 1.0, 0.5, 0.05)
                        extra = st.checkbox(
                            "Include stronger classical and equal-budget search references", True
                        )
                        repair = st.checkbox("Also record bounded classical repair", False)
                    st.caption(
                        "Pilots and final sampling use the same total shot allowance as fixed QAOA. "
                        "Runtime includes preparation and post-processing; Aer timeout is checked between circuit jobs."
                    )
                submitted = st.form_submit_button("Run experiment", type="primary")
                st.caption("Exactly K holdings · Long-only allocation · Full investment · No live trading")
            if submitted:
                try:
                    cfg = RunConfig(
                        dataset_id=snapshot["dataset_id"],
                        n=n,
                        k=k,
                        sector_limit=sector,
                        risk_aversion=risk,
                        max_weight=cap,
                        seed=seed,
                        batches=batches,
                        shots=shots,
                        max_seconds=seconds,
                        min_weight=min_weight,
                        sector_weight_cap=sector_cap,
                        extra_baselines=extra,
                        repair=repair,
                    )
                    job_id = store.submit(cfg.model_dump(), token=str(uuid.uuid4()))
                    st.session_state["submitted_job"] = job_id
                    start_worker(root)
                    st.success(
                        f"Queued real experiment {job_id[:12]}. Results will be saved even if you close this page."
                    )
                except ValueError as exc:
                    st.error(str(exc))
            job_panel()
        with st.container(border=True):
            st.subheader("Reproducibility")
            st.write(
                "Every run saves its data fingerprint, settings, seed, code fingerprint and installed package versions."
            )
            st.caption(
                "Current constituent snapshots are not historical membership evidence. Missing prices remain missing."
            )
    with results_tab:
        result = choose_result("experiment-replay", "optimization_comparison")
        show_results(result)
    with controller:
        show_controller(result)
    with record:
        if result:
            st.json(
                {
                    k: result[k]
                    for k in [
                        "run_id",
                        "created_at",
                        "config",
                        "dataset_fingerprint",
                        "preparation",
                        "software",
                        "limitations",
                    ]
                }
            )
            st.download_button(
                "Download complete run JSON",
                json.dumps(result, indent=2),
                f"{result['run_id']}.json",
                "application/json",
            )
        else:
            st.info("The complete run record appears after an experiment.")

elif page == "Data audit":
    st.title("Data audit")
    st.markdown('<div class="intro">Know where every observation came from.</div>', unsafe_allow_html=True)
    st.write(
        "Membership: official NSE constituent file. Stock prices and corporate actions: Yahoo Finance via yfinance, a secondary source."
    )
    if st.button("Download a new frozen snapshot", type="primary"):
        st.session_state["submitted_job"] = store.submit({"kind": "download"})
        start_worker(root)
        st.success("Download queued. Original source files and all failures will be preserved.")
    job_panel()
    if not snapshots:
        st.info("No dataset has been collected. No sample prices or substitute records are provided.")
    else:
        snapshot = st.selectbox("Inspect snapshot", snapshots, format_func=lambda m: m["dataset_id"])
        a, b, c = st.columns(3)
        a.metric("Stock histories retained", f"{snapshot['stock_count']} / 50")
        b.metric("Real daily records", f"{snapshot['row_count']:,}")
        c.metric("Latest stored session", snapshot["last_date"])
        st.caption(f"Coverage begins {snapshot['first_date']} · Retrieved {snapshot['retrieved_at']}")
        st.caption(
            f"{snapshot.get('quarantined_row_count', 0)} invalid dated rows quarantined. "
            "A retained history can still contain gaps; eligibility is checked for each decision window."
        )
        cross = snapshot["crosscheck"]
        st.write(
            f"Official NSE close cross-check: **{cross['status']}** · {len(cross['matches'])} matching stocks on {cross['date']}."
        )
        st.caption(
            "This single-session cross-check does not certify every historical adjustment or corporate action."
        )
        with st.expander(
            "Quarantined rows and data-quality flags",
            expanded=bool(snapshot["failures"]) or bool(snapshot.get("quarantined_row_count")),
        ):
            if snapshot["failures"]:
                st.dataframe(pd.DataFrame(snapshot["failures"]), hide_index=True, width="stretch")
            flags = [
                {"symbol": a["symbol"], "flags": a["large_moves"]}
                for a in snapshot["audits"]
                if a["large_moves"]
            ]
            st.json(flags)
            quarantines = [
                {
                    "Stock": a["symbol"],
                    "Quarantined rows": a.get("quarantined_count", 0),
                    "Details": json.dumps(a.get("quarantined_rows", [])),
                }
                for a in snapshot["audits"]
                if a.get("quarantined_count", 0)
            ]
            if quarantines:
                st.dataframe(pd.DataFrame(quarantines), hide_index=True, width="stretch")
        if st.button("Verify every stored source fingerprint"):
            try:
                _, members, prices = load_snapshot(snapshot["dataset_id"], root)
                st.success(
                    f"All recorded files match their SHA-256 fingerprints: {len(members)} constituents, {len(prices):,} validated rows."
                )
            except Exception as exc:
                st.error(f"Validation blocked: {exc}")
        with st.expander("Source manifest"):
            st.json(snapshot)
        st.warning(
            "Strict historical backtesting is blocked until dated constituent eligibility and corporate-action coverage are verified."
        )

elif page == "Saved runs":
    st.title("Saved runs")
    st.caption(
        "Replay reads the saved file and checks its fingerprint. It does not launch another simulation."
    )
    show_results(choose_result("saved-replay"))
    st.subheader("Job history")
    jobs = store.list()
    if jobs:
        st.dataframe(pd.DataFrame(jobs)[["id", "status", "created", "updated", "error"]], hide_index=True)
        restartable = [j for j in jobs if j["status"] in {"failed", "cancelled", "interrupted"}]
        if restartable:
            chosen = st.selectbox(
                "Restart as a new job", restartable, format_func=lambda j: j["id"][:12] + " · " + j["status"]
            )
            if st.button("Restart selected job"):
                st.session_state["submitted_job"] = store.submit(chosen["config"])
                start_worker(root)
                st.success("A new job was created; the previous record is unchanged.")
    else:
        st.info("No queued jobs yet. Command-line runs can still be replayed above.")

elif page == "Research":
    st.title("Research workbench")
    st.write("Build evidence in stages—not a claim that quantum is automatically better.")
    st.dataframe(
        pd.DataFrame(
            [
                ["2019", "Estimation history", "Real prices available subject to per-stock validation"],
                ["2020–2022", "Development / controller training", "No training campaign claimed completed"],
                [
                    "2023",
                    "Validation / fixed configuration choice",
                    "Configuration selection must precede locked testing",
                ],
                [
                    "2024–2025",
                    "Locked historical test",
                    "Strict run blocked without verified membership / actions",
                ],
                ["2026 onward", "Separate extension", "Current optimization demonstration is separate"],
            ],
            columns=["Period", "Purpose", "Status / boundary"],
        ),
        hide_index=True,
        width="stretch",
    )
    st.subheader("Implemented research building blocks")
    st.write(
        "X and cardinality-preserving XY mixers; circuit depths 1–4; COBYLA and SPSA optimizers; "
        "mean and conditional-value-at-risk aggregation; past-only decision-tree ranking; "
        "classical repair; continuous and joint allocation references."
    )
    st.caption(
        "The default demonstration uses only X-mixer depths 1 and 2. Advanced configurations are opt-in through the Python package/configuration files."
    )
    st.warning(
        "A larger encoded circuit includes constraint variables. The 20-qubit safeguard counts all of them; a 20-stock request may be rejected."
    )
    st.subheader("What still needs research evidence")
    st.write(
        "Verified historical membership, corporate-action reconciliation, controller training, "
        "validation-selected fixed baselines, multi-seed campaigns and locked-period financial results."
    )
    st.caption(
        "Risk-free research assumption: 0%. Transaction-cost sensitivity: 0, 10 and 25 basis points of traded notional."
    )

else:
    st.title("How it works")
    st.markdown(
        '<div class="intro">A portfolio is a basket. QAOA proposes what goes in it.</div>',
        unsafe_allow_html=True,
    )
    stages = [
        ("1 · Collect", "Download real stock histories and keep a fingerprint of every file.", "data/"),
        (
            "2 · Prepare",
            "Use only prices known on the decision date to estimate return and how stocks move together.",
            "portfolio/",
        ),
        (
            "3 · Select",
            "Classical solvers and the Quantum Approximate Optimization Algorithm choose exactly K stocks.",
            "classical/ + quantum/",
        ),
        (
            "4 · Adapt",
            "Try short quantum runs at two depths, compare valid answers, and spend the remaining budget on the chosen setting.",
            "adaptive/",
        ),
        (
            "5 · Allocate",
            "The same classical calculation decides investment weights and checks the money rules for every method.",
            "classical/weights.py",
        ),
        (
            "6 · Compare",
            "Save actual answers, violations, costs and controller evidence. A browser refresh simply replays them.",
            "evaluation/ + experiments/",
        ),
    ]
    for title, body, module in stages:
        with st.container(border=True):
            st.subheader(title)
            st.write(body)
            st.caption("src/qcompass/" + module)
    st.info(
        "Simulation means this laptop imitates the quantum circuit. It does not turn your laptop into a quantum computer or establish a speed advantage."
    )
    st.caption(
        "Quadratic Unconstrained Binary Optimization encodes a score and penalties using 0/1 decisions. "
        "A qubit is one simulated quantum bit; a shot is one measured sample; circuit depth is the number of repeated QAOA layers."
    )
