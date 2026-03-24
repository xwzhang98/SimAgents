# Cosmological Simulation Resource Database

Reference database of published compute costs for cosmological simulations.
Used by the SimAgents resource estimator to predict requirements for new runs.

---

## MP-Gadget Simulations

### BlueTides
- **Citation:** Feng et al. 2015 (arXiv:1504.06619)
- **Software:** MP-Gadget
- **Box size:** 400 Mpc/h
- **Particle count:** ~700 billion (2 x 3500^3; half gas, half DM)
- **Physics:** Hydrodynamic (SPH), star formation, black hole feedback
- **CPU-hours:** ~2.6 million node-hours (reported range 2.6-8M node-hours across phases)
- **Nodes/cores:** 20,250 Cray XE nodes; 648,000 cores (81,000 MPI ranks x 8 OpenMP threads)
- **Memory per node:** ~64 GB per node (BlueWaters XE6 nodes)
- **Storage:** Not explicitly reported
- **Wall-clock time:** ~28 days
- **HPC system:** BlueWaters (NCSA), Cray XE/XK
- **Notes:** Ran from z=99 to z=8. Largest hydro simulation at high redshift at time of publication.

### ASTRID
- **Citation:** Bird et al. 2022 (arXiv:2111.01160)
- **Software:** MP-Gadget
- **Box size:** 250 Mpc/h
- **Particle count:** 2 x 5500^3 (~332 billion total)
- **Physics:** Hydrodynamic, star formation, black hole growth (torque-limited accretion), AGN feedback, patchy reionization
- **CPU-hours:** ~3 million node-hours to z=3; ~670 million CPU-hours total to z=0.5
- **Nodes/cores:** Frontera nodes (56 Intel Xeon Platinum 8280 cores per node)
- **Memory per node:** 192 GB per node (Frontera)
- **Storage:** Not explicitly reported; uses BigFile snapshot format
- **Wall-clock time:** Not explicitly reported
- **HPC system:** Frontera (TACC)
- **Notes:** One of the most computationally ambitious galaxy formation simulations. Extended run to z=0.5 consumed 670M CPU-hours.

---

## Arepo Simulations

### IllustrisTNG TNG300-1
- **Citation:** Pillepich et al. 2018; Springel et al. 2018 (arXiv:1703.02970; arXiv:1707.03397)
- **Software:** AREPO (moving-mesh)
- **Box size:** 302.6 Mpc (205 Mpc/h)
- **Particle count:** 2 x 2500^3 (~31.25 billion total)
- **Physics:** Full galaxy formation: magnetohydrodynamics, star formation, stellar feedback, SMBH seeding/growth, AGN feedback (kinetic + thermal), radiative cooling, chemical enrichment
- **CPU-hours:** ~35 million core-hours
- **Nodes/cores:** 24,000 cores on Hazel Hen
- **Memory per node:** 128 GB per node (Hazel Hen Cray XC40)
- **Storage:** ~500 TB total (combined TNG100 + TNG300 data release)
- **Wall-clock time:** Finished November 23, 2016
- **HPC system:** Hazel Hen (HLRS Stuttgart), Cray XC40
- **Notes:** German Gauss Centre allocation. 100 full snapshots + 680 mini-snapshots stored.

### IllustrisTNG TNG100-1
- **Citation:** Pillepich et al. 2018; Nelson et al. 2018 (arXiv:1703.02970; arXiv:1812.05609)
- **Software:** AREPO (moving-mesh)
- **Box size:** 110.7 Mpc (75 Mpc/h)
- **Particle count:** 2 x 1820^3 (~12 billion total)
- **Physics:** Same as TNG300-1 (full IllustrisTNG galaxy formation model)
- **CPU-hours:** ~18 million core-hours (estimated from relative scaling)
- **Nodes/cores:** ~10,000 cores on Hazel Hen
- **Memory per node:** 128 GB per node
- **Storage:** Included in 500 TB combined data release
- **Wall-clock time:** Not separately reported
- **HPC system:** Hazel Hen (HLRS Stuttgart)
- **Notes:** Higher mass resolution than TNG300; baryon mass resolution ~1.4 x 10^6 Msun.

### MillenniumTNG MTNG740
- **Citation:** Pakmor et al. 2023 (arXiv:2210.10060)
- **Software:** AREPO (moving-mesh, IllustrisTNG galaxy formation model)
- **Box size:** 740 Mpc (500 Mpc/h)
- **Particle count:** 2 x 4320^3 (~161 billion); 80.6 billion gas cells
- **Physics:** Full IllustrisTNG physics: MHD, star formation, stellar/AGN feedback, radiative cooling, chemical enrichment
- **CPU-hours:** >100 million core-hours
- **Nodes/cores:** 2,560 SuperMUC-NG nodes; 122,880 cores
- **Memory per node:** 96 GB per node (SuperMUC-NG)
- **Storage:** Not explicitly reported
- **Wall-clock time:** Not explicitly reported
- **HPC system:** SuperMUC-NG (LRZ Garching)
- **Notes:** Largest high-resolution galaxy formation simulation at time of publication. Also ran matching DM-only box with 4320^3 particles.

---

## SWIFT Simulations

### FLAMINGO L2800N5040
- **Citation:** Schaye et al. 2023 (arXiv:2306.04024)
- **Software:** SWIFT
- **Box size:** 2800 Mpc (2.8 Gpc)
- **Particle count:** 2 x 5040^3 (~300 billion total)
- **Physics:** Hydrodynamic (SPH), star formation, stellar feedback, AGN feedback, neutrino particles, subgrid calibrated with machine learning
- **CPU-hours:** >50 million CPU-hours (entire FLAMINGO suite)
- **Nodes/cores:** Up to 65,000 CPU cores
- **Memory per node:** 512 GB per node (COSMA8)
- **Storage:** >1 PB (entire FLAMINGO suite)
- **Wall-clock time:** Not separately reported
- **HPC system:** COSMA8 (DiRAC, Durham)
- **Notes:** Largest cosmological hydro simulation by volume at publication. Baryonic particle mass ~1 x 10^9 Msun.

### FLAMINGO L1000N1800
- **Citation:** Schaye et al. 2023 (arXiv:2306.04024)
- **Software:** SWIFT
- **Box size:** 1000 Mpc (1.0 Gpc)
- **Particle count:** 2 x 1800^3 (~11.7 billion total)
- **Physics:** Same as L2800N5040 (full FLAMINGO subgrid model)
- **CPU-hours:** ~5 million CPU-hours (estimated from scaling)
- **Nodes/cores:** Subset of COSMA8
- **Memory per node:** 512 GB per node (COSMA8)
- **Storage:** Included in >1 PB suite total
- **Wall-clock time:** Not separately reported
- **HPC system:** COSMA8 (DiRAC, Durham)
- **Notes:** Higher resolution variant; baryonic particle mass ~1 x 10^8 Msun.

---

## GIZMO Simulations

### FIRE-2 Zoom Simulations
- **Citation:** Hopkins et al. 2018 (arXiv:1702.06148)
- **Software:** GIZMO (MFM - Meshless Finite Mass)
- **Box size:** Zoom-in; high-res region ~1-3 Mpc around target halo
- **Particle count:** Typically 10^7-10^8 particles in zoom region (MW-mass halo: ~50M effective particles)
- **Physics:** Explicit ISM physics: radiative cooling (10-10^10 K), star formation in self-gravitating gas, stellar feedback (SNe Ia/II, stellar winds, radiation pressure, photoionization, photoelectric heating)
- **CPU-hours:** ~1-20 million CPU-hours per MW-mass zoom (typical ~5-10M core-hours for m12 halos)
- **Nodes/cores:** 256-2048 cores typical
- **Memory per node:** ~4-8 GB per core needed
- **Storage:** ~1-10 TB per zoom simulation (600 snapshots)
- **Wall-clock time:** Weeks to months per zoom
- **HPC system:** XSEDE allocations (Stampede2, Frontera); Caltech Wheeler cluster
- **Notes:** Achieves parsec-scale resolution. Suite includes m10, m11, m12 (MW-mass), m13 halos. Cost scales steeply with halo mass.

### SIMBA m100n1024
- **Citation:** Dave et al. 2019 (arXiv:1901.10203)
- **Software:** GIZMO (MFM - Meshless Finite Mass)
- **Box size:** 100 Mpc/h (147 Mpc)
- **Particle count:** 2 x 1024^3 (~2.1 billion total)
- **Physics:** Meshless hydro, H2-based star formation, stellar feedback (decoupled winds), black hole growth (torque-limited + Bondi), AGN feedback (kinetic jets + X-ray), on-the-fly dust model
- **CPU-hours:** ~10 million CPU-hours (estimated from similar-scale MUFASA runs and GIZMO scaling)
- **Nodes/cores:** ~1000-2000 cores
- **Memory per node:** ~128 GB per node
- **Storage:** ~50 TB (151 snapshots)
- **Wall-clock time:** Not explicitly reported
- **HPC system:** DiRAC facility (UK); successor to MUFASA runs
- **Notes:** Evolved from MUFASA code. Includes novel kinetic AGN jet feedback and dust tracking.

---

## Gadget-2/3 Simulations

### Millennium
- **Citation:** Springel et al. 2005 (arXiv:astro-ph/0504097)
- **Software:** GADGET-2
- **Box size:** 500 Mpc/h (685 Mpc)
- **Particle count:** 2160^3 (~10.08 billion; DM-only)
- **Physics:** Dark matter only (gravity, TreePM)
- **CPU-hours:** ~343,000 CPU-hours (350k core-hours)
- **Nodes/cores:** 512 processors
- **Memory per node:** ~2 GB per core (~1 TB total)
- **Storage:** ~25 TB (64 snapshots)
- **Wall-clock time:** ~28 days
- **HPC system:** IBM p690 cluster at Max Planck Computing Centre (Garching)
- **Notes:** Landmark simulation; DM particle mass 8.6 x 10^8 Msun/h. Modest by modern standards.

### Millennium-XXL
- **Citation:** Angulo et al. 2012 (arXiv:1203.3216)
- **Software:** GADGET-3 (L-GADGET3)
- **Box size:** 3000 Mpc/h (4.1 Gpc)
- **Particle count:** 6720^3 (~303 billion; DM-only)
- **Physics:** Dark matter only (gravity, TreePM)
- **CPU-hours:** ~2.86 million CPU-hours (326 CPU-years)
- **Nodes/cores:** 12,000 cores
- **Memory per node:** ~30 TB total RAM
- **Storage:** >100 TB
- **Wall-clock time:** 9.3 days
- **HPC system:** JUROPA (Julich Supercomputing Centre)
- **Notes:** DM particle mass 6.17 x 10^9 Msun/h. Ran in summer 2010. 30x volume of original Millennium.

### EAGLE L100N1504
- **Citation:** Schaye et al. 2015 (arXiv:1407.7040)
- **Software:** GADGET-3 (heavily modified; ANARCHY SPH)
- **Box size:** 100 cMpc (67.77 Mpc/h)
- **Particle count:** 2 x 1504^3 (~6.8 billion total)
- **Physics:** Hydrodynamic (SPH), radiative cooling (element-by-element), star formation (pressure law), stellar feedback (thermal stochastic), AGN feedback (thermal), metal enrichment
- **CPU-hours:** ~4.5 million CPU-hours
- **Nodes/cores:** 4,096 cores
- **Memory per node:** ~32 TB total (8 GB per core)
- **Storage:** ~10 TB (29 snapshots + snipshots)
- **Wall-clock time:** ~45 days
- **HPC system:** DiRAC-2 COSMA (Durham)
- **Notes:** Subgrid physics <25% of CPU time. Baryon mass resolution 1.81 x 10^6 Msun.

### Magneticum Box2/hr
- **Citation:** Dolag et al. 2016 (various; see magneticum.org)
- **Software:** GADGET-3 (OpenGadget3)
- **Box size:** 500 Mpc/h (352 Mpc/h for Box2)
- **Particle count:** 2 x 1584^3 (~7.9 billion for Box2/hr)
- **Physics:** Hydrodynamic (SPH), radiative cooling, star formation, stellar feedback, AGN feedback, magnetic fields, thermal conduction, chemical enrichment (multiple elements)
- **CPU-hours:** ~25 million CPU-hours (entire Magneticum Pathfinder suite)
- **Nodes/cores:** 86,016 cores (full SuperMUC Phase 2)
- **Memory per node:** 155 TB total usable (out of 194 TB)
- **Storage:** 320 TB (entire suite)
- **Wall-clock time:** Not separately reported
- **HPC system:** SuperMUC Phase 2 (LRZ Garching)
- **Notes:** Includes magnetic field evolution and thermal conduction. Multiple box sizes in suite (Box0 through Box4).

---

## Dark Matter Only Reference Estimates

Scaling estimates for DM-only TreePM simulations (Gadget-like codes), assuming typical parameters and modern hardware.

### Small: 100 Mpc/h, 512^3
- **Particle count:** ~134 million
- **Estimated CPU-hours:** ~1,000-5,000 core-hours
- **Estimated memory:** ~10-20 GB (150 bytes/particle)
- **Estimated storage:** ~0.5-2 TB (100 snapshots, ~100 bytes/particle/snapshot)
- **Estimated wall-clock:** Hours on 128-256 cores
- **Notes:** Feasible on small clusters or workstations. Good for testing and calibration.

### Medium: 300 Mpc/h, 1024^3
- **Particle count:** ~1.07 billion
- **Estimated CPU-hours:** ~20,000-100,000 core-hours
- **Estimated memory:** ~100-200 GB (150-200 bytes/particle)
- **Estimated storage:** ~5-20 TB (100 snapshots)
- **Estimated wall-clock:** 1-3 days on 512-1024 cores
- **Notes:** Standard production-quality simulation. Requires moderate HPC allocation.

### Large: 1000 Mpc/h, 4096^3
- **Particle count:** ~68.7 billion
- **Estimated CPU-hours:** ~2-10 million core-hours
- **Estimated memory:** ~5-15 TB (100-200 bytes/particle)
- **Estimated storage:** ~200 TB-1 PB (100 snapshots)
- **Estimated wall-clock:** 1-4 weeks on 5000-20000 cores
- **Notes:** Requires Tier-0/Tier-1 HPC allocation. Comparable to Millennium-XXL class.

---

## Scaling Relations

### Memory Scaling

| Component | Bytes per particle | Notes |
|---|---|---|
| DM-only (minimal) | 50-100 bytes | Position (3x8), velocity (3x8), ID (8), mass (8), acceleration (3x8), tree overhead |
| DM-only (typical Gadget) | 100-200 bytes | Includes tree structure, domain decomposition buffers |
| DM-only (optimized, CUBE) | 6-13 bytes | Compressed fixed-point representation |
| Hydro (per gas particle) | 200-500 bytes | Additional: density, pressure, entropy, smoothing length, gradients |
| Hydro (Arepo moving-mesh) | 400-800 bytes | Mesh connectivity, gradient estimates, Riemann solver data |
| MHD (additional) | +50-100 bytes | Magnetic field vector (3x8) + divergence cleaning |
| Star/BH particles | 300-600 bytes | Additional metadata: formation time, metallicity, feedback state |
| Neutrino particles | 50-80 bytes | Lightweight; often use linear response or particle methods |

**Rule of thumb:**
- DM-only: ~150 bytes/particle (safe estimate for Gadget-family codes)
- Full hydro: ~500 bytes/particle (gas) + ~150 bytes/particle (DM)
- Peak memory = 1.5-3x base estimate (communication buffers, domain imbalance, tree rebuild)

### Compute Scaling

**Base scaling:** O(N log N) per timestep for TreePM methods.

| Factor | Scaling | Notes |
|---|---|---|
| Gravity (TreePM) | N log N per step | Dominates for DM-only; PM grid ~N, tree ~N log N |
| Gravity (FMM) | ~N per step | Used by some modern codes (SWIFT, PKDGRAV3) |
| SPH hydro | ~N_gas x N_ngb per step | N_ngb ~ 48-64 neighbors; ~25-50% overhead vs gravity-only |
| Moving mesh (Arepo) | ~N_cells per step | Voronoi mesh construction + Riemann solves |
| Timesteps (adaptive) | ~N_active per step | Hierarchical timestepping reduces cost 5-20x vs global |
| Total timesteps | ~1000-5000 for DM | Depends on force resolution and redshift range |
| Total timesteps | ~10,000-100,000 for hydro | Dense gas requires much shorter steps |

**Empirical cost formulas (Gadget-family, modern hardware):**
- DM-only: CPU-hours ~ 2e-5 x N_particles x N_steps / N_cores_effective
- Hydro (SPH): CPU-hours ~ 5e-5 x N_particles x N_steps / N_cores_effective
- Hydro (moving mesh): CPU-hours ~ 8e-5 x N_particles x N_steps / N_cores_effective

**Physics overhead multipliers (relative to DM-only gravity):**
| Physics module | Multiplier | Notes |
|---|---|---|
| Hydrodynamics (SPH) | 1.5-2.5x | Neighbor finding + SPH kernel evaluation |
| Hydrodynamics (Arepo mesh) | 2-4x | Voronoi + Riemann solver |
| Radiative cooling | 1.05-1.1x | Cheap per particle; table lookup |
| Star formation | 1.05-1.1x | Stochastic; applied to dense gas only |
| Stellar feedback (thermal) | 1.05-1.2x | Depends on implementation |
| Stellar feedback (kinetic/FIRE) | 1.2-2.0x | Explicit ISM resolution is expensive |
| AGN feedback | 1.05-1.2x | Applied to few particles but can drive short timesteps |
| MHD | 1.3-1.8x | Additional field solve per hydro step |
| Radiation transport (M1/OTVET) | 2-5x | Depends on number of frequency bins |
| Radiation (full RT, e.g., MCRT) | 5-50x | Extremely expensive; rarely done in large boxes |
| On-the-fly FOF/subfind | 1.1-1.3x | Periodic overhead for halo finding |

### Storage Scaling

| Data type | Bytes per particle per snapshot | Notes |
|---|---|---|
| DM-only (minimal) | 36 bytes | Position (3x4) + velocity (3x4) + ID (8) + mass (4) |
| DM-only (full) | 52-76 bytes | + potential, acceleration, group membership |
| Hydro gas (minimal) | 60-80 bytes | + density, temperature/entropy, SFR, smoothing length |
| Hydro gas (full) | 100-200 bytes | + metallicity (multiple elements), magnetic field, subgrid quantities |
| Star particles | 80-150 bytes | + formation time, initial mass, metallicity array |
| BH particles | 100-200 bytes | + accretion rate, feedback energy, progenitor info |

**Snapshot size estimates:**
- DM-only, N particles, minimal: ~40 x N bytes per snapshot
- Full hydro, N_total particles: ~100 x N_total bytes per snapshot
- Typical run: 50-200 snapshots (full) + 500-2000 mini-snapshots (subset of fields)

**Total storage rule of thumb:**
- DM-only: ~6 x N x 10^-9 TB per 100 full snapshots
- Full hydro: ~15 x N x 10^-9 TB per 100 full snapshots
- Add 2-5x for restart files, group catalogs, merger trees, and post-processing products

### Cross-Simulation Comparison Table

| Simulation | Year | Code | Box (Mpc/h) | N_particles | Physics | CPU-hours | Approx cost/particle (us/particle) |
|---|---|---|---|---|---|---|---|
| Millennium | 2005 | Gadget-2 | 500 | 10B | DM | 343K | 34 |
| Millennium-XXL | 2012 | Gadget-3 | 3000 | 303B | DM | 2.86M | 9.4 |
| EAGLE L100 | 2015 | Gadget-3 | 68 | 6.8B | Hydro+SF+AGN | 4.5M | 662 |
| BlueTides | 2015 | MP-Gadget | 400 | 700B | Hydro+SF+BH | ~50M node-hrs | ~1100 |
| IllustrisTNG TNG300 | 2018 | AREPO | 205 | 31B | MHD+SF+AGN | 35M | 1129 |
| IllustrisTNG TNG100 | 2018 | AREPO | 75 | 12B | MHD+SF+AGN | ~18M | 1500 |
| FIRE-2 (m12 zoom) | 2018 | GIZMO | zoom | ~50M | Explicit ISM | ~10M | 200,000 |
| SIMBA m100 | 2019 | GIZMO | 100 | 2.1B | Hydro+SF+AGN | ~10M | 4762 |
| ASTRID | 2022 | MP-Gadget | 250 | 332B | Hydro+SF+AGN+reion | 670M | 2018 |
| FLAMINGO L2800 | 2023 | SWIFT | 2800 | 300B | Hydro+SF+AGN+nu | >50M | >167 |
| MillenniumTNG | 2023 | AREPO | 500 | 161B | MHD+SF+AGN | >100M | >621 |
| Magneticum Box2 | 2016 | Gadget-3 | 352 | 7.9B | MHD+SF+AGN | ~25M | 3165 |

**Notes on the comparison table:**
- Cost/particle is total CPU-hours divided by total particle count (microseconds per particle integrated over entire run).
- FIRE-2 cost/particle is extremely high due to parsec-scale resolution in zoom regions.
- SWIFT (FLAMINGO) achieves lower cost/particle through algorithmic optimizations (task-based parallelism, FMM gravity).
- Costs are not directly comparable across hardware generations (factor ~2-4x improvement per decade).

---

## References

1. Feng, Y., et al. 2016, MNRAS, 455, 2778 (arXiv:1504.06619) - BlueTides
2. Bird, S., et al. 2022, MNRAS, 512, 3703 (arXiv:2111.01160) - ASTRID
3. Pillepich, A., et al. 2018, MNRAS, 475, 648 (arXiv:1703.02970) - TNG300/TNG100
4. Springel, V., et al. 2018, MNRAS, 475, 676 (arXiv:1707.03397) - IllustrisTNG methods
5. Nelson, D., et al. 2019, ComAC, 6, 2 (arXiv:1812.05609) - TNG data release
6. Pakmor, R., et al. 2023, MNRAS, 524, 2539 (arXiv:2210.10060) - MillenniumTNG
7. Schaye, J., et al. 2023, MNRAS, 526, 4978 (arXiv:2306.04024) - FLAMINGO
8. Hopkins, P., et al. 2018, MNRAS, 480, 800 (arXiv:1702.06148) - FIRE-2
9. Dave, R., et al. 2019, MNRAS, 486, 2827 (arXiv:1901.10203) - SIMBA
10. Springel, V., 2005, Nature, 435, 629 (arXiv:astro-ph/0504097) - Millennium
11. Angulo, R., et al. 2012, MNRAS, 426, 2046 (arXiv:1203.3216) - Millennium-XXL
12. Schaye, J., et al. 2015, MNRAS, 446, 521 (arXiv:1407.7040) - EAGLE
13. Dolag, K., et al. 2016 (magneticum.org) - Magneticum Pathfinder
14. Wetzel, A., et al. 2023, ApJS, 265, 44 (arXiv:2202.06969) - FIRE-2 data release
