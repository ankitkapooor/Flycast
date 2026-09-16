# FlyCast: Scientific Modeling Notes & Assumptions

> **"Can an evolved biological network provide useful computation when operated as a recurrent computer?"**

FlyCast is an engineering and scientific experiment that evaluates the computational capacity of the complete **MaleCNS v1.0** *Drosophila melanogaster* connectome when repurposed as a fixed physical reservoir.

To ensure scientific integrity, this document explicitly delineates what was **empirically observed** in the biological reconstruction versus what was **engineered by FlyCast**.

---

## 1. Observed Biological Data (MaleCNS v1.0 Release)

The biological substrate used by FlyCast comes directly from the MaleCNS v1.0 publication by HHMI Janelia FlyEM, Cambridge, MRC LMB, and Google Research:

1. **Neuron Identities & Anatomical Superclasses:**
   - 166,691 identified neurons spanning the entire adult male central nervous system (brain, optic lobes, ventral nerve cord).
   - High-confidence superclass classifications (sensory, central interneurons, descending, motor/efferent).
2. **Synaptic Contact Counts (Structural Connectivity):**
   - Synapse-level physical contact counts for approximately 25.58 million directed connections between identified neuron pairs.
3. **Neurotransmitter Predictions:**
   - Machine-learning predictions of primary neurotransmitter identity (acetylcholine, GABA, glutamate, dopamine, serotonin, octopamine).
4. **Physical Graph Topology:**
   - The exact directed degree distributions, clustering coefficients, recurrent loops, and modular hierarchy evolved in *Drosophila melanogaster*.

---

## 2. Engineered Modeling Choices (FlyCast Implementation)

Connectomics data provides structural wiring, but not the electrophysiological state, receptor distribution, or dynamic firing history of the living animal. FlyCast bridges this gap through the following mathematical and engineering choices:

1. **Continuous Leaky Rate Neurons:**
   - Biological neurons transmit information via action potentials (spikes) and graded potential fluctuations. FlyCast models neurons as continuous-variable rate units operating under an Echo State Network (ESN) formulation.
2. **Sigmoidal Nonlinearity (Hyperbolic Tangent):**
   - Local synaptic integration is compressed via `tanh(.)` to bound activation between -1.0 and +1.0 while providing smooth derivative characteristics around zero.
3. **Synaptic Weight Scaling:**
   - Raw synaptic counts follow an extreme heavy-tailed distribution (from 1 to thousands of contacts). FlyCast applies `w = log(1 + synapse_count)` to compress dynamic range while strictly preserving relative connection hierarchies.
4. **Postsynaptic Incoming Normalization:**
   - Each postsynaptic neuron's incoming connections are normalized such that $\sum |w_{in}| = 1.0$. This prevents highly connected hub neurons from saturating or diverging while maintaining the relative proportion of inputs from each presynaptic partner.
5. **Global Dynamics (Leak and Gain):**
   - Recurrent gain ($g = 0.95$) and leak rate ($\alpha = 0.25$) are tuned for computational memory and stability near the edge of chaos.
6. **Synthetic Sensory Injection:**
   - Arbitrary scalar and multivariate time series (financial, weather, oscillatory) do not correspond to literal olfactory or visual signals. FlyCast projects external signals across 512 annotated sensory neurons via fixed random projection weights sampled from $\text{Uniform}(-1, +1) \times 0.5$.
7. **Virtual Readout Electrodes:**
   - Rather than observing all 166,483 neurons, a stratified sample of 4,096 readout neurons is monitored at each timestep.
8. **Linear Ridge Readout:**
   - The recurrent connectome remains completely frozen. A multi-output Ridge regression is trained on sampled reservoir states to forecast future target values across horizons $h \in [1, H]$.
9. **Unsigned Connectome Mode:**
   - In default mode, all structural connections are treated as positive magnitudes. While neurotransmitter predictions are retained in metadata, variable postsynaptic receptor expression prevents unambiguous sign assignment in all cases without further physiological characterization.

---

## 3. Scientific Caveats

- FlyCast **does not** simulate a conscious fly, recreate fly thoughts, or emulate the original insect's behavioral state.
- FlyCast **does** test whether the structural organization of an evolved biological graph possesses nonlinear computational memory and reservoir forecasting utility when benchmarked against standard linear, persistence, and weight-scrambled controls.
