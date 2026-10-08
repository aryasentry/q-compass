import { ArrowDown, ArrowRight } from "lucide-react";
import { PageHeading } from "@/components/ui";
export const metadata = { title: "Methodology" };
export default function Page() {
  return (
    <>
      <PageHeading
        title="How Q-Compass works"
        description="A simple guide to what this application does—and does not prove."
      />
      <section className="method-flow" aria-label="Experiment workflow">
        <div>
          Real NIFTY data<small>Frozen and validated</small>
        </div>
        <ArrowRight />
        <div>
          Stock selection<small>Classical + simulated quantum</small>
        </div>
        <ArrowRight />
        <div>
          Investment weights<small>The same classical allocator</small>
        </div>
        <ArrowRight />
        <div>
          Compare and save<small>Results, costs and evidence</small>
        </div>
      </section>
      <div className="method-grid">
        <section>
          <span className="eyebrow">01 / THE PROBLEM</span>
          <h2>Which stocks, and how much?</h2>
          <p>
            Imagine a basket with room for four stocks. The first step chooses
            which four to include. The second step decides what fraction of the
            money each stock gets.
          </p>
          <p>
            We estimate return and risk from the preceding 252 daily returns.
            Investment rules restrict the number of holdings, concentration by
            industry and the weight of each position.
          </p>
          <p>
            Choosing stocks and assigning weights separately is a practical
            approximation, not an exact solution of the combined financial
            problem.
          </p>
        </section>
        <section>
          <span className="eyebrow">02 / THE QUANTUM PART</span>
          <h2>A search with adjustable settings</h2>
          <p>
            QAOA (Quantum Approximate Optimization Algorithm) is a way to search
            for stock combinations. Each stock gets a yes/no variable. QUBO
            (Quadratic Unconstrained Binary Optimization) turns the score and
            rule penalties into a form a quantum circuit can use.
          </p>
          <p>
            Qiskit Aer simulates that circuit on this computer. A classical
            optimizer adjusts its angles. Repeated measurements, called shots,
            produce candidate stock combinations.
          </p>
          <p>
            This is simulation only. It is not running on a quantum processor.
          </p>
        </section>
        <section>
          <span className="eyebrow">03 / THE ADAPTIVE PART</span>
          <h2>Try small, then spend the budget</h2>
          <p>
            The controller tries short pilot runs at different circuit depths.
            It compares valid selections using the original score, then gives
            the remaining budget to a promising configuration.
          </p>
          <div className="inline-flow">
            Pilot configurations <ArrowDown size={17} /> Compare feasibility and
            score <ArrowDown size={17} /> Continue the chosen configuration
          </div>
          <p>
            The default app uses pilot-only adaptation. Learning configuration
            rankings from earlier market conditions is a later research stage,
            not an active claim.
          </p>
        </section>
        <section>
          <span className="eyebrow">04 / A FAIR COMPARISON</span>
          <h2>Every method plays by the same rules</h2>
          <p>
            Classical references include exhaustive selection, greedy local
            swaps and a constrained quadratic solver. Fixed-depth quantum runs,
            the adaptive run and equal-budget configuration search use the same
            financial input.
          </p>
          <p>
            Pilots, final sampling and post-processing are reported. A zero
            selection gap means matching the reference selection score—not
            making money or proving quantum speedup.
          </p>
          <p>
            Invalid results remain visible. Optional classical repair is
            reported separately and never changes the investment rules.
          </p>
        </section>
      </div>
      <section className="panel glossary">
        <h2>Terms, without the mystery</h2>
        <dl className="record-list">
          <dt>Covariance</dt>
          <dd>
            How two stocks tend to move together. It helps measure the basket’s
            risk.
          </dd>
          <dt>Feasibility</dt>
          <dd>
            Whether an answer follows every rule. Stock selection and investment
            weights are checked separately.
          </dd>
          <dt>Depth</dt>
          <dd>
            How many repeated layers the quantum circuit has. More layers cost
            more and need not work better.
          </dd>
          <dt>Seed</dt>
          <dd>
            A recorded starting value for random choices, so an experiment can
            be reproduced.
          </dd>
          <dt>Selection gap</dt>
          <dd>
            The difference from a certified best selection score. Lower is
            better.
          </dd>
          <dt>Fingerprint</dt>
          <dd>
            A file’s digital checksum. If the data changes, its fingerprint
            changes.
          </dd>
        </dl>
      </section>
      <div className="notice">
        <strong>What remains to be demonstrated</strong>
        <p>
          Market-aware ranking, large-scale performance and bias-controlled
          historical investment returns require further experiments. No live
          trading or forecast of guaranteed return is provided here.
        </p>
      </div>
    </>
  );
}
