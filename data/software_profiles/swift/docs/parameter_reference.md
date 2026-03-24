# SWIFT Parameter Reference

SWIFT uses YAML configuration files organized into sections.

## InternalUnitSystem
Defines the internal unit system for the simulation.
- **UnitMass_in_cgs**: Mass unit in grams. Example: 1.989e43 (1e10 Msun).
- **UnitLength_in_cgs**: Length unit in cm. Example: 3.085678e24 (1 Mpc).
- **UnitVelocity_in_cgs**: Velocity unit in cm/s. Example: 1e5 (1 km/s).
- **UnitCurrent_in_cgs**: Current unit in cgs. Example: 1.
- **UnitTemp_in_cgs**: Temperature unit in cgs. Example: 1.

## Cosmology
- **h**: Reduced Hubble parameter (H0 = 100*h km/s/Mpc). Required. Typical: 0.6774.
- **a_begin**: Starting scale factor. Required. Typical: 0.01 (z=99).
- **a_end**: Ending scale factor. Required. Typical: 1.0 (z=0).
- **Omega_cdm**: Cold dark matter density parameter. Required. Note: this is Omega_cdm, NOT Omega_m.
- **Omega_lambda**: Dark energy density parameter. Required.
- **Omega_b**: Baryon density parameter. Required.

## Gravity
- **eta**: Dimensionless time-step parameter for gravity. Default: 0.025.
- **MAC**: Multipole acceptance criterion. Options: geometric, adaptive. Default: adaptive.
- **theta_cr**: Opening angle for tree walk. Default: 0.7.
- **comoving_DM_softening**: Comoving softening for DM particles in internal units.
- **max_physical_DM_softening**: Maximum physical softening for DM particles.
- **comoving_baryon_softening**: Comoving softening for baryon particles.
- **max_physical_baryon_softening**: Maximum physical softening for baryon particles.
- **mesh_side_length**: Side length of PM mesh. Default: 256.

## SPH
- **resolution_eta**: Smoothing length resolution parameter. Default: 1.2348.
- **CFL_condition**: Courant condition number. Default: 0.1.
- **minimal_temperature**: Minimum temperature in Kelvin. Default: 100.
- **h_min_ratio**: Minimum smoothing length as fraction of softening. Default: 0.1.

## TimeIntegration
- **dt_min**: Minimum allowed timestep in internal units. Default: 1e-10.
- **dt_max**: Maximum allowed timestep in internal units. Default: 0.01.

## InitialConditions
- **file_name**: Path to IC file (HDF5). Required.
- **periodic**: Whether the box is periodic (1=yes). Default: 1.
- **cleanup_h_factors**: Remove h-factors from IC data. Default: 0.
- **cleanup_velocity_factors**: Remove sqrt(a) factors from velocities. Default: 0.

## Snapshots
- **basename**: Base name for snapshot files. Default: "snap".
- **output_list_on**: Whether to use an output list. Default: 0.
- **output_list**: Path to output time list file.
- **time_first**: Time of first snapshot if not using output list.
- **delta_time**: Time between snapshots if not using output list.

## Scheduler
- **max_top_level_cells**: Maximum number of top-level cells. Default: 12.
- **cell_split_size**: Particle count threshold for cell splitting. Default: 400.
