# %%
# simplest visualization
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from scipy.spatial import cKDTree as KDTree
from gaepsi2 import camera, painter, color
from bigfile import BigFile

# %%
def extract_particles(path, config):
    """
    Extract particles within a specified box region.
    
    This function filters particles inside a cuboid volume centered at a specified position.
    It handles periodic boundary conditions by wrapping particles across the simulation box.
    
    Parameters
    ----------
    part : BigFile object
        BigFile containing particle data
    tube : dict
        Dictionary with the following keys:
        - 'center': array-like, center of the region
        - 'Lbox': float, full simulation box size
        - 'Lx', 'Ly', 'Lz': float, dimensions of the cutout region
        
    Returns
    -------
    mask : ndarray of bool
        Boolean mask for particles inside the region
    ppos_ : ndarray
        Positions of particles inside the region, centered at tube["center"]
        
    Notes
    -----
    Position wrapping is applied to handle periodic boundary conditions when
    the region crosses the simulation box boundary.
    """
    # Load particle positions
    part = BigFile(path)
    ppos = np.float32(part.open("Position")[:])
    
    # Center positions around the target region
    ppos -= config["view_center"]
    boxsize = config["simulation_box_size"]
    
    # Apply periodic boundary conditions
    ppos[ppos < -boxsize / 2] += boxsize
    ppos[ppos > boxsize / 2] -= boxsize

    # Create mask for particles inside the cuboid
    mask = np.abs(ppos[:, 0]) < config["region_x"] * 0.5 
    mask &= np.abs(ppos[:, 1]) < config["region_y"] * 0.5
    mask &= np.abs(ppos[:, 2]) < config["region_z"] * 0.5
    
    # Filter positions using the mask
    ppos_ = ppos[mask]
    print(f"Selected {ppos_.shape[0]} particles from {ppos.shape[0]} ({ppos_.shape[0]/ppos.shape[0]*100:.2f}%)")
    
    return mask, ppos_

def smooth(pos, k=60):
    """
    Calculate smoothing lengths using k-nearest neighbors.
    
    This function estimates the local density environment of each particle by finding
    the distance to its kth nearest neighbor, which is then used as the smoothing length.
    
    Parameters
    ----------
    pos : ndarray, shape (N, 3)
        Particle positions in 3D space
    k : int, optional
        Number of nearest neighbors to use, default is 60
        
    Returns
    -------
    ndarray, shape (N,)
        Smoothing lengths for each particle, defined as the distance to the kth neighbor
        
    Notes
    -----
    Larger k values result in smoother density fields but lower resolution.
    For detailed features, use smaller k values (10-20).
    For large-scale structure, use larger k values (50+).
    """
    # Build KD-tree for efficient nearest neighbor queries
    tree = KDTree(pos)
    
    # Query the k nearest neighbors for each particle
    # Returns distances (d) and indices (i)
    d, i = tree.query(pos, k=k)
    
    # Return the distance to the kth neighbor as the smoothing length
    return d[:, -1].copy()

# %%
visualization_config = {
    "simulation_box_size": 100_000,  # Full simulation box size in simulation units
    "view_center": 100_000/2,        # Center position for the visualization
    "region_x": 100_000,         # Width (x-dimension) of region to visualize
    "region_y": 100_000,        # Height (y-dimension) of region to visualize
    "region_z": 100_000,         # Depth (z-dimension) of region to visualize
    "imsize": 1000,        # Output image resolution in pixels
    "particle_smoothing": 2,         # Smoothing length for particle rendering
    "particle_weight": 1 / 1024,   # Weight factor for each particle
}

# %%
path = "/hildafs/home/xzhangn/xzhangn/sim_output/dmo-100MPC/test-data/7_0/dmo-512/set3/output/PART_099/1"
mask, pos = extract_particles(path, visualization_config)
print("pos x range: ", np.min(pos[:, 0]), np.max(pos[:, 0]))
print("pos y range: ", np.min(pos[:, 1]), np.max(pos[:, 1]))
print("pos z range: ", np.min(pos[:, 2]), np.max(pos[:, 2]))
k = None
if k is None:
    sml = np.ones(len(pos)) * visualization_config['particle_smoothing'] # constant smoothing length
else:
    sml = smooth(pos, k=k) # calculate smoothing length based on number of nearby particles

# %%
theta = 30
theta = np.radians(theta)
r_xy = 1.5
z_scale = 0.2
volume_scale = 1.5
imsize = visualization_config["imsize"]
weight = np.ones(len(pos)) * visualization_config["particle_weight"]

# %%
def calc_matrix(config, theta, r_xy, z_scale, volume_scale):
    """
    Calculate the transformation matrix for the camera view.
    
    This function computes the transformation matrix that maps the simulation box
    into the camera's viewing frustum. It handles the rotation and translation
    of the camera based on the provided parameters.
    config: dict
        Configuration dictionary containing the following keys:
        - 'simulation_box_size': float, full simulation box size in simulation units
        - 'view_center': float, center position for the visualization
        - 'region_x': float, width (x-dimension) of region to visualize
        - 'region_y': float, height (y-dimension) of region to visualize
        - 'region_z': float, depth (z-dimension) of region to visualize
        - 'image_resolution': int, output image resolution in pixels
        - 'particle_smoothing': float, smoothing length for particle rendering
        - 'particle_weight': int, weight factor for each particle
    theta: float
        Rotation angle in radians
    r_xy: float
        radius of the circle in the x-y plane
    z_scale: float
        scale of the camera z coordinate
    volume_scale: float
        scale of the volume
    """
    x_scale = r_xy * np.cos(theta)
    y_scale = r_xy * np.sin(theta)
    if volume_scale < r_xy:
        volume_scale = r_xy
    
    half_region_x = config["region_x"] / 2
    half_region_y = config["region_y"] / 2
    half_region_z = config["region_z"] / 2
    
    scaled_half_region_x = config["region_x"] * volume_scale / 2
    scaled_half_region_y = config["region_y"] * volume_scale / 2
    scaled_half_region_z = config["region_z"] * volume_scale / 2
    
    camera_position = (x_scale*half_region_x, y_scale*half_region_y, z_scale*half_region_z)
    
    target_position = (0, 0, 0)
    up_vector = (0, 0, 1)

    # input for camera.ortho is (near, far, (left, right, bottom, top))
    ortho_matrix = camera.ortho(-scaled_half_region_x, scaled_half_region_x, (-scaled_half_region_y, scaled_half_region_y, -scaled_half_region_z, scaled_half_region_z)) # (near, far, (left, right, bottom, top))
    camera_matrix = camera.lookat(camera_position, target_position, up_vector)
    mat = camera.matrix(ortho_matrix, camera_matrix)
    
    return mat


# %%
matrix = calc_matrix(visualization_config, theta=theta, r_xy=r_xy, z_scale=z_scale, volume_scale=volume_scale)
dm2d = camera.apply(matrix, pos)
dmdev = camera.todevice(dm2d, extent=(imsize, imsize))
channels = painter.paint(dmdev, sml, [weight], (imsize, imsize), np=16)
img = channels[0].T

# %%
half_region_x = visualization_config["region_x"] / 2
half_region_y = visualization_config["region_y"] / 2
half_region_z = visualization_config["region_z"] / 2

corner = np.array([
    [-half_region_x,-half_region_y,-half_region_z], #0
    [-half_region_x,-half_region_y,+half_region_z], #1
    [-half_region_x,+half_region_y,-half_region_z], #2
    [-half_region_x,+half_region_y,+half_region_z], #3
    [+half_region_x,-half_region_y,-half_region_z], #4
    [+half_region_x,-half_region_y,+half_region_z], #5
    [+half_region_x,+half_region_y,-half_region_z], #6
    [+half_region_x,+half_region_y,+half_region_z]  #7
    ])
corner2d = camera.apply(matrix, corner)
cornerdev = camera.todevice(corner2d, extent=(imsize, imsize))

if (0 <= theta < np.pi / 2):
    dash_corner = cornerdev[0]
elif (np.pi / 2 <= theta < np.pi):
    dash_corner = cornerdev[4]
elif (np.pi <= theta < 1.5 * np.pi):
    dash_corner = cornerdev[6]
elif (1.5 * np.pi <= theta < 2 * np.pi):
    dash_corner = cornerdev[2]
    
cn2d = []
for i in range(0, len(cornerdev)):
    p = cornerdev[i]
    dr = corner - corner[i]
    # Find adjacent corners (differ by exactly one coordinate)
    msk = np.count_nonzero(dr, axis=-1) == 1
    for o in cornerdev[msk]:
        x, y = np.array([p[0], o[0]]), np.array([p[1], o[1]])
        r2 = np.linalg.norm(o - dash_corner, axis=0)
        r3 = np.linalg.norm(p - dash_corner, axis=0)
        # Determine line style based on visibility
        if (r2 < 1 or r3 < 1):
            cn2d.append([x, y, 0])  # Dashed line
        else:
            cn2d.append([x, y, 1])  # Solid line

# %%
figsize = (11 , 11)
plt.style.use('dark_background')
fig, ax = plt.subplots(1, 1, figsize=figsize)
ax.axis('off')
vmax = np.percentile(img, 99.99)
vmin = vmax / 1000
print("vmax: ", vmax)
print("vmin: ", vmin)

ax.imshow(img,
          norm=colors.LogNorm(vmin=vmin, vmax=vmax), 
          cmap='inferno',
          extent=[0, imsize, 0, imsize],
          origin='lower',
          )
# plot the corner
for d in cn2d:
    x, y, style = d
    if style == 0:
        ax.plot(x, y, c='grey', alpha=0.5, lw=2, linestyle='--')
    else:
        ax.plot(x, y, c='white', lw=1.5, alpha=0.7)
plt.show()

# %%



