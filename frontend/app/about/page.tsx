import React from "react";
import { ScientificCaveat } from "../../components/ScientificCaveat";

export default function AboutPage() {
  return (
    <div className="py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 space-y-10 font-sans text-foreground/80 leading-relaxed text-sm">
        {/* Header */}
        <div className="border-b border-paper-border pb-6 space-y-2 font-mono">
          <span className="text-xs uppercase tracking-widest text-fly font-bold">
            BACKGROUND & DISCLOSURES
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground font-sans">
            About FlyCast
          </h1>
          <p className="text-xs text-foreground/60 leading-relaxed">
            Distinguishing biological observations from engineered computational choices.
          </p>
        </div>

        <ScientificCaveat detailed={true} />

        {/* Section: Observed vs Engineered */}
        <section className="space-y-4 font-mono text-xs">
          <h2 className="text-lg font-bold text-foreground font-sans uppercase tracking-wide">
            Observed Biology vs. Engineered Modeling Choices
          </h2>

          <div className="overflow-x-auto border border-paper-border bg-paper-light rounded-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-paper-border bg-paper-dark/70 text-foreground">
                  <th className="p-3 w-1/2 font-bold uppercase text-[11px] text-fly">
                    OBSERVED (MaleCNS Dataset)
                  </th>
                  <th className="p-3 w-1/2 font-bold uppercase text-[11px] text-foreground">
                    ENGINEERED (FlyCast System)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-border/60 text-[11px]">
                <tr>
                  <td className="p-3 align-top">
                    166,691 physical neuron reconstructions across the male fruit fly central nervous system.
                  </td>
                  <td className="p-3 align-top">
                    166,483 nodes filtered by superclass annotation and treated as rate-neuron computational units.
                  </td>
                </tr>
                <tr>
                  <td className="p-3 align-top">
                    Observed synaptic contact counts between pre- and postsynaptic pairs.
                  </td>
                  <td className="p-3 align-top">
                    Synaptic weights transformed via log(1 + count) and normalized per postsynaptic row (L1 = 1.0).
                  </td>
                </tr>
                <tr>
                  <td className="p-3 align-top">
                    Neurotransmitter identity predictions (acetylcholine, GABA, glutamate, etc.).
                  </td>
                  <td className="p-3 align-top">
                    Unsigned reservoir mode by default to avoid speculative sign mappings; optional heuristic mode.
                  </td>
                </tr>
                <tr>
                  <td className="p-3 align-top">
                    Biological sensory receptor classifications (optic lobes, antennal lobes).
                  </td>
                  <td className="p-3 align-top">
                    Deterministic injection of external time series into 512 sensory neurons with uniform weights.
                  </td>
                </tr>
                <tr>
                  <td className="p-3 align-top">
                    Complex living biophysical membrane dynamics, ion channels, and spike generation.
                  </td>
                  <td className="p-3 align-top">
                    Leaky tanh rate dynamics and linear Ridge regression readout for discrete-time forecasting.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* The Core Question */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-sans">The Research Question</h2>
          <blockquote className="p-4 border-l-2 border-fly bg-paper-light text-foreground font-serif italic text-base">
            &ldquo;Can an evolved biological network provide computational utility when used directly as a fixed recurrent computer?&rdquo;
          </blockquote>
          <p>
            Most modern neural networks are described as &ldquo;brain-inspired.&rdquo; FlyCast takes a different path: it
            investigates whether the exact structural topology of an actual animal nervous system exhibits useful
            nonlinear memory, separation, and dynamic properties when driven by external data.
          </p>
        </section>

        {/* Attribution and Team Acknowledgments */}
        <section className="space-y-3 pt-4 border-t border-paper-border/60">
          <h2 className="text-xl font-bold text-foreground font-sans">Data Attribution</h2>
          <p>
            FlyCast relies on the monumental connectomics work accomplished by the MaleCNS collaboration:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>HHMI Janelia Research Campus (FlyEM Project Team)</li>
            <li>University of Cambridge (Department of Zoology)</li>
            <li>MRC Laboratory of Molecular Biology (LMB)</li>
            <li>Google Research</li>
          </ul>
          <p className="text-xs text-foreground/60 pt-2">
            MaleCNS data is provided under Creative Commons Attribution (CC BY). FlyCast is an independent open-source
            experiment created to explore reservoir computing over biological graphs.
          </p>
        </section>
      </div>
    </div>
  );
}
