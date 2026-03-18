# MP-Gadget Parameter File Reference

## Required Gadget Parameters

### Cosmological Parameters
- **Omega0**: Matter density parameter (Omega_m). Required. Range: 0.0–1.0.
- **OmegaLambda**: Dark energy density parameter. Required. Range: 0.0–1.0.
- **OmegaBaryon**: Baryon density parameter. Required for hydrodynamic runs.
- **HubbleParam**: Hubble parameter h (H0 = 100*h km/s/Mpc). Required. Typical: 0.67–0.72.
- **CMBTemperature**: CMB temperature in Kelvin. Default: 2.7255.

### Simulation Box
- **BoxSize**: Simulation box side length in kpc/h. Required. Note: papers often quote in Mpc/h — multiply by 1000.
- **TimeMax**: Scale factor at end of simulation. Required. Typical: 1.0 (z=0).

### Input/Output
- **InitCondFile**: Path to initial conditions file. Required.
- **OutputDir**: Directory for simulation output. Required.
- **OutputList**: Comma-separated list of scale factors for snapshot output. Required.

### Time Integration
- **MaxSizeTimestep**: Maximum timestep. Default: 0.1.
- **MinSizeTimestep**: Minimum timestep. Default: 0.0.

### Force Accuracy
- **ErrTolForceAcc**: Force accuracy parameter. Default: 0.005.
- **TreeDomainUpdateFrequency**: How often to update domain decomposition. Default: 0.025.

### Memory
- **PartAllocFactor**: Memory allocation factor. Default: 1.5.
- **BufferSize**: Communication buffer in MB. Default: 100.

### Gravity
- **Asmth**: Force softening scale in mesh cells. Default: 1.25.
- **Nmesh**: PM grid size. Must match or exceed particle grid.

## Unit Conventions
- Length: kpc/h (internal) — convert from Mpc/h by multiplying by 1000
- Mass: 10^10 M_sun/h
- Velocity: km/s
