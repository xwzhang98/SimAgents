# Arepo Parameter File Reference

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
- **SnapFormat**: Snapshot file format (1=default, 3=HDF5). Default: 3.

## Mesh Settings (Arepo-specific)
- **CellShapingSpeed**: Speed of cell regularization. Controls how aggressively cells return to regular shapes. Typical: 0.5.
- **ReferenceGasPartMass**: Target gas cell mass for refinement/derefinement. Required for mesh refinement.
- **TargetGasMassFactor**: Factor for target gas mass tolerance. Typical: 2.0.
- **CellMaxAngleFactor**: Maximum angle factor for cell shapes. Controls cell shape quality. Typical: 2.25.

## Softening
- **SofteningComovingClass0**: Comoving gravitational softening length for particle type 0.
- **SofteningMaxPhysClass0**: Maximum physical softening for particle type 0.

## Memory
- **MaxMemSize**: Maximum memory per MPI task in MB. Required.

## Force Accuracy
- **ErrTolTheta**: Opening angle for tree walk. Default: 0.7.
- **ErrTolForceAcc**: Force accuracy parameter. Default: 0.0025.

## Time Integration
- **MaxSizeTimestep**: Maximum allowed timestep. Default: 0.05.

## Unit System
- **UnitLength_in_cm**: Length unit in cm. Default: 3.085678e21 (1 kpc).
- **UnitMass_in_g**: Mass unit in grams. Default: 1.989e43 (1e10 Msun).
- **UnitVelocity_in_cm_per_s**: Velocity unit in cm/s. Default: 1e5 (1 km/s).
