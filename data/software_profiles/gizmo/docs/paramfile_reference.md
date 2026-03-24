# GIZMO Parameter File Reference

## Cosmological Parameters
- **Omega0**: Total matter density parameter. Required. Range: 0.0-1.0.
- **OmegaLambda**: Dark energy density parameter. Required. Range: 0.0-1.0.
- **OmegaBaryon**: Baryon density parameter. Required for hydrodynamic runs.
- **HubbleParam**: Hubble parameter h (H0 = 100*h km/s/Mpc). Required. Typical: 0.67-0.72.

## Simulation Box
- **BoxSize**: Simulation box side length in code units (kpc). Required.
- **TimeBegin**: Scale factor at start of simulation. Typical: 0.01 (z=99).
- **TimeMax**: Scale factor at end of simulation. Required. Typical: 1.0 (z=0).

## Input/Output
- **InitCondFile**: Path to initial conditions file. Required.
- **OutputDir**: Directory for simulation output. Required.
- **OutputListFilename**: File containing list of output times.
- **SnapFormat**: Snapshot file format (1=Gadget-1, 3=HDF5). Default: 3.

## Softening (Gadget-2 Style)
- **SofteningHalo**: Gravitational softening for halo (DM) particles in code units.
- **SofteningGas**: Gravitational softening for gas particles.
- **SofteningDisk**: Gravitational softening for disk particles.
- **SofteningBulge**: Gravitational softening for bulge particles.
- **SofteningStars**: Gravitational softening for star particles.
- **SofteningBndry**: Gravitational softening for boundary particles.
- **SofteningHaloMaxPhys**: Maximum physical softening for halo particles.
- **SofteningGasMaxPhys**: Maximum physical softening for gas particles.

## Hydro Method
- **HydroMethod**: Hydrodynamic solver to use. Options include MFM (meshless finite-mass), MFV (meshless finite-volume), SPH.

## Force Accuracy
- **ErrTolTheta**: Opening angle for tree walk. Default: 0.7.
- **ErrTolForceAcc**: Force accuracy parameter. Default: 0.005.

## Time Integration
- **MaxSizeTimestep**: Maximum allowed timestep. Default: 0.1.
- **MinSizeTimestep**: Minimum allowed timestep. Default: 1e-12.

## Memory
- **PartAllocFactor**: Memory allocation factor. Default: 1.5.
- **BufferSize**: Communication buffer in MB. Default: 100.

## Unit System
- **UnitLength_in_cm**: Length unit in cm. Default: 3.085678e21 (1 kpc).
- **UnitMass_in_g**: Mass unit in grams. Default: 1.989e43 (1e10 Msun).
- **UnitVelocity_in_cm_per_s**: Velocity unit in cm/s. Default: 1e5 (1 km/s).
