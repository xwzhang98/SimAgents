# MP-Gadget GenIC (Initial Conditions) Reference

## Required GenIC Parameters

### Output
- **OutputDir**: Directory to write IC files. Required.
- **FileBase**: Base name for IC files. Required. Default: "IC".

### Box & Resolution
- **BoxSize**: Box side length in kpc/h. Required. Must match Gadget BoxSize.
- **Ngrid**: Number of grid cells per dimension for particle grid. Required. Total particles = Ngrid^3.
- **Nmesh**: FFT mesh size for IC generation. Required. Usually = Ngrid or 2*Ngrid.

### Cosmology
- **Omega0**: Total matter density. Required.
- **OmegaLambda**: Dark energy density. Required.
- **OmegaBaryon**: Baryon density. Required for hydro runs.
- **HubbleParam**: Hubble parameter h. Required.
- **Sigma8**: Power spectrum normalization sigma_8. Required if using power spectrum.
- **PrimordialIndex**: Scalar spectral index n_s. Default: 0.96.

### Initial Redshift
- **Redshift**: Starting redshift for the simulation. Required. Typical: 49–199.

### Power Spectrum
- **FileWithInputSpectrum**: Path to input power spectrum file. Optional — if not provided, uses internal CAMB.
- **FileWithTransferFunction**: Path to transfer function file. Optional.
- **WhichSpectrum**: Power spectrum type. 1 = read from file, 2 = Eisenstein & Hu.

### Particle Types
- **ProduceGas**: Whether to include gas particles. 0 = DM only, 1 = DM + gas.
- **RadiationOn**: Include radiation. Default: 0.

### Random Seed
- **Seed**: Random seed for IC generation. Required for reproducibility.
