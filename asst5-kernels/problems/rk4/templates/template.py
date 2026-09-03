from task import input_t, output_t

def custom_kernel(data: input_t) -> output_t:
    """
    Args:
        data:
            Tuple of (u0, alpha, hx, hy, hz, n_steps) where:
                u0:      Tensor of shape (Nz, Ny, Nx), containing initial field values (float32)
                alpha:   Diffusion coefficient (float)
                hx:      Grid spacing in x direction (float)
                hy:      Grid spacing in y direction (float)
                hz:      Grid spacing in z direction (float)
                n_steps: Number of RK4 time steps (int)
    Returns:
        u:
            Tensor of shape (Nz, Ny, Nx), containing the field after n_steps RK4 updates
            of the 3D heat equation: u_t = alpha * Laplacian(u)
    """
    u0, alpha, hx, hy, hz, n_steps = data
    
    pass
