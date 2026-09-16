import React from "react";
import { ScientificCaveat } from "../../components/ScientificCaveat";

export default function MethodologyPage() {
  return (
    <div className="py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 space-y-12 font-sans text-foreground/80 leading-relaxed text-sm">
        {/* Header */}
        <div className="border-b border-paper-border pb-6 space-y-2 font-mono">
          <span className="text-xs uppercase tracking-widest text-fly font-bold">
            SPECIFICATION & ARCHITECTURE
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground font-sans">
            Methodology
          </h1>
          <p className="text-xs text-foreground/60 leading-relaxed">
            A comprehensive technical breakdown of how the MaleCNS fruit-fly connectome was converted into a recurrent
            reservoir computing system for time-series forecasting.
          </p>
        </div>

        <ScientificCaveat detailed={true} />

        {/* 01 The Connectome */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">01</span> / The Connectome (MaleCNS v1.0)
          </h2>
          <p>
            The connectome used in FlyCast originates from the open-access <strong>MaleCNS v1.0</strong> release, an
            imaging and reconstruction effort by HHMI Janelia FlyEM, the University of Cambridge, the MRC Laboratory of
            Molecular Biology, and Google Research.
          </p>
          <p>
            The published dataset contains <strong>166,691 identified neurons</strong> across the adult male fruit fly
            central nervous system (brain, optic lobes, and ventral nerve cord) and 11,691 annotated cell types. FlyCast
            treats bodies with non-null superclass annotations as computational nodes, resulting in a runtime graph of
            approximately <strong>166,483 connected nodes</strong> and <strong>25.58 million directed edges</strong>.
          </p>
        </section>

        {/* 02 Turning Wiring into a Reservoir */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">02</span> / Turning Wiring into a Sparse Reservoir
          </h2>
          <p>
            The 1.1 GB raw graph is transformed once into a Compressed Sparse Row (CSR) matrix. To reduce the extreme
            heavy-tailed distribution of raw synaptic contact counts while preserving connection hierarchies, synaptic
            strengths are scaled via:
          </p>
          <div className="p-3 bg-paper-dark/60 border border-paper-border rounded font-mono text-xs text-foreground">
            w = log(1 + raw_synapse_count)
          </div>
          <p>
            The sparse CSR matrix is strictly constructed with <code>W[post, pre]</code> orientation so that matrix-vector
            multiplication <code>next_input = W @ state</code> faithfully reflects activity flowing from presynaptic to
            postsynaptic neurons.
          </p>
          <p>
            To prevent runaway excitation or numerical divergence, incoming synaptic weights are normalized per
            postsynaptic neuron such that the L1 norm of incoming weights equals 1.0 (row normalization).
          </p>
        </section>

        {/* 03 Injecting Arbitrary Data */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">03</span> / Injecting User Data into Biological Neurons
          </h2>
          <p>
            Arbitrary financial, seasonal, or physical time-series signals do not correspond to literal fruit fly
            sensory stimuli. However, biological inspiration dictates that external information enters the nervous
            system via dedicated sensory populations.
          </p>
          <p>
            FlyCast identifies neurons whose anatomical superclass marks them as sensory. A deterministic subset of
            <strong>512 sensory neurons</strong> (seed 42) is selected. Each input feature is projected across a
            partition of these sensory neurons with fixed projection weights sampled from:
          </p>
          <div className="p-3 bg-paper-dark/60 border border-paper-border rounded font-mono text-xs text-foreground">
            Win[i, f] ~ Uniform(-1, +1) * input_gain
          </div>
        </section>

        {/* 04 Reservoir Dynamics */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">04</span> / Leaky Recurrent Rate Dynamics
          </h2>
          <p>
            FlyCast executes a classic Echo State Network (ESN) leaky rate update for each discrete observation:
          </p>
          <div className="p-4 bg-paper-dark border border-paper-border rounded font-mono text-xs text-foreground space-y-1 overflow-x-auto">
            <div>x[t+1] = (1 - leak) * x[t] + leak * tanh( recurrent_gain * W @ x[t] + Win @ u[t] )</div>
          </div>
          <p>
            Default parameters: <code>leak = 0.25</code>, <code>recurrent_gain = 0.95</code>, and{" "}
            <code>input_gain = 0.50</code>. All states are stored as 32-bit floating point vectors.
          </p>
        </section>

        {/* 05 Training the Readout */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">05</span> / Direct Multi-Horizon Ridge Readout
          </h2>
          <p>
            The recurrent connectome weights remain completely frozen. Rather than storing all ~166K neuron states at
            each timestep, <strong>4,096 virtual readout electrodes</strong> are deterministically sampled across the CNS.
          </p>
          <p>
            For a forecast horizon <em>H</em>, FlyCast constructs direct multi-output targets:
          </p>
          <div className="p-3 bg-paper-dark/60 border border-paper-border rounded font-mono text-xs text-foreground">
            Y[t] = [ y[t+1], y[t+2], ..., y[t+H] ]
          </div>
          <p>
            A multi-output linear Ridge model is trained on the sampled reservoir states. Chronological splits (70%
            Train, 15% Validation, 15% Test) are strictly enforced without shuffling. Hyperparameter selection across
            candidate alphas (<code>1e-4</code> to <code>100</code>) is determined exclusively on validation RMSE. The
            final model is refitted on Train + Validation and evaluated on unseen Test rows.
          </p>
        </section>

        {/* 06 Baselines */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">06</span> / Baseline Benchmarks
          </h2>
          <p>
            Every experiment is evaluated alongside standard non-connectome baselines using identical chronological
            splits:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Persistence:</strong> Projects the last observed value <code>y[t]</code> forward across all future
              horizons.
            </li>
            <li>
              <strong>Autoregressive Ridge:</strong> Uses lagged values of the target series (candidate lags: 10, 20, 40)
              with cross-validated Ridge regularization.
            </li>
          </ul>
        </section>

        {/* 07 Scientific Limitations */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">07</span> / Scientific Limitations
          </h2>
          <p>
            Electron microscopy connectomics provides static anatomical structure. It does not record the animal's
            dynamic firing patterns, electrophysiological conductance, neurotransmitter receptor densities, or
            neuromodulatory state.
          </p>
          <p>
            Therefore, FlyCast represents an engineered computational machine operating over biological graph topology.
            It is not a digital resurrection or cognitive simulation of a living fruit fly.
          </p>
        </section>

        {/* 08 Reproducibility */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-mono flex items-center gap-2">
            <span className="text-fly font-mono">08</span> / Reproducibility & Open Source
          </h2>
          <p>
            Every run records the dataset SHA-256 hash, connectome manifest hash, random seed (42), split boundaries,
            and exact hyperparameter selections. Any experiment can be audited and reproduced identically.
          </p>
        </section>
      </div>
    </div>
  );
}
