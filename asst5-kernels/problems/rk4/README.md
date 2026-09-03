# 3D Heat Equation – RK4 Benchmark

This problem asks you to reproduce and accelerate a solver that combines a **high-order finite-difference Laplacian** with **RK4 time integration** for the 3D heat equation. You will start from **`reference.py`**, a pure-PyTorch implementation which we will compare your kernel against for performance and correctness. The README highlights the math, data layout, and numerical trade-offs so you can build an accelerated and accurate GPU kernel.

This is a **scientific computing benchmark** that exposes you to high-performance scientific computations, memory access optimization, and time-stepping schemes.

---

## Background

We solve the **3D heat equation**
$$
\frac{\partial u}{\partial t} = \alpha \nabla^2 u,
$$
on a uniform Cartesian grid, where:

- $u = u(t,x,y,z)$ is temperature (or any scalar field)
- $\alpha$ is the constant diffusion coefficient
- $\nabla^2 u = \frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2} + \frac{\partial^2 u}{\partial z^2}$ is the **Laplacian operator**, which measures how much the temperature at a point differs from its neighbors
- the discrete field has shape $(N_x, N_y, N_z)$ with spacings $(h_x, h_y, h_z)$

The initial field $u_0$ is provided as a PyTorch tensor, and the solver advances it for `n_steps` RK4 steps of size $\Delta t$ determined by a CFL-like criterion.

---

## Spatial discretization

The solver uses the **finite difference method** to approximate the Laplacian $\nabla^2 u$. Instead of solving the Laplacian analytically, we approximate each second derivative using a **stencil**—a pattern that accesses neighboring grid points, multiplies them by coefficients, and sums the results.

For this problem, we use an **8th-order accurate** stencil for computing **2nd-order derivatives** in **3D**. This means we access 4 neighbors in each direction (plus the center point), giving us a 25-point stencil total (1 center + 4 neighbors × 6 directions = 25 points).

<table>
<tr>
<td width="50%">
<img src="images/1_o_3d_fd.png" alt="1st order 3D stencil" width="100%">
<p><em>2nd-order 3D stencil: 7 points</em></p>
</td>
<td width="50%">
<img src="images/4o_3d.png" alt="4th order 3D stencil" width="100%">
<p><em>8th-order 3D stencil: 25 points</em></p>
</td>
</tr>
</table>
<p><em> Source: <a href="https://www.ness.music.ed.ac.uk/wp-content/uploads/2016/12/ICA2016-0561.pdf">ICA2016-0561.pdf</a></em></p>

> **Problem specification:** This kernel implements an **8th-order accurate** finite difference approximation for computing **2nd-order derivatives** in **3D**. 

The full Laplacian is $\nabla^2 u = \frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2} + \frac{\partial^2 u}{\partial z^2}$, which requires accessing **25 points total** (the center point plus 4 neighbors in each of the 6 directions: ±x, ±y, ±z). This is shown in the right panel of the diagram above.


The coefficients come from the standard radius-4, 8th-order central finite difference approximation ([Fornberg 1988 Table 1](https://doi.org/10.1090/S0025-5718-1988-0935077-0)). The notation $C_n$ indicates the coefficient for points at distance $n$ from the center: $C_0$ is the center point, $C_1$ is for neighbors at distance ±1, $C_2$ for distance ±2, and so on. 

| coefficient | value          |
|-------------|----------------|
| $C_0$       | $-205 / 72$    |
| $C_1$       | $+8 / 5$       |
| $C_2$       | $-1 / 5$       |
| $C_3$       | $+8 / 315$     |
| $C_4$       | $-1 / 560$     |



> **Note: Boundary Handling**
> 
> Points within 4 cells of any boundary (i.e., indices `< 4` or `>= N-4` in any dimension) are **not updated** during the time-stepping. These boundary regions are treated as fixed Dirichlet boundary conditions—their values are simply copied from the input and remain unchanged. 


---

## Time integration – classical RK4

To advance the solution from time $t$ to $t + \Delta t$, we need to integrate the heat equation. Since we've discretized space (using finite differences for the Laplacian), we now have an ordinary differential equation in time: at each grid point, the temperature changes according to $\frac{du}{dt} = \alpha \nabla^2 u$. To solve this numerically, we use the **classical 4-stage Runge-Kutta method (RK4)**, which evaluates the Laplacian at four different intermediate states during each time step to achieve high accuracy.

### Understanding RK4

RK4 is a method for solving ordinary differential equations by evaluating at four different "stages" during each time step to get a very accurate estimate of where the solution should be at the next time step.

The diagram below visualizes how RK4 works. The curve represents the true solution $u(t)$ over time. Starting at point $u_n$ (the leftmost point), RK4 evaluates the slope (rate of change) at four different points during the time step:

- **$k_1$**: The slope at the **beginning** of the interval, computed by evaluating the Laplacian at the current state $u_n$ (this is what Euler's method would use)
- **$k_2$**: The slope at the **midpoint** of the interval, computed by first taking a half-step forward using $k_1$ to create an intermediate stage, then evaluating the Laplacian at that stage
- **$k_3$**: The slope at the **midpoint** again, but this time computed by taking a half-step forward using $k_2$ (instead of $k_1$) to create a refined intermediate stage, then evaluating the Laplacian there
- **$k_4$**: The slope at the **end** of the interval, computed by taking a full step forward using $k_3$ to create a final stage, then evaluating the Laplacian at that endpoint

Notice that $k_2$ and $k_3$ both estimate the slope at the midpoint, but $k_3$ uses the refined estimate $k_2$ to get there, making it more accurate. By sampling the slope at the beginning, midpoint (twice with different estimates), and end, then combining them with weights (1, 2, 2, 1), RK4 achieves much higher accuracy than Euler's method (which only uses $k_1$).

![RK4 slopes visualization](images/Runge-Kutta_slopes.png)
*The four slope estimates $k_1$ through $k_4$ used by RK4, showing how they sample the solution at different points during the time step. Image by [HilberTraum](https://commons.wikimedia.org/wiki/User:HilberTraum) (CC BY-SA 4.0) from [Wikipedia](https://en.wikipedia.org/wiki/Runge%E2%80%93Kutta_methods).*

### The RK4 algorithm

For each time step, RK4 computes four slope estimates and combines them:

1. $k_1 = \alpha \, \nabla^2(u_n)$
2. $k_2 = \alpha \, \nabla^2(u_n + \tfrac{\Delta t}{2} k_1)$
3. $k_3 = \alpha \, \nabla^2(u_n + \tfrac{\Delta t}{2} k_2)$
4. $k_4 = \alpha \, \nabla^2(u_n + \Delta t \, k_3)$

Then the solution is updated with a weighted average:

$$u_{n+1} = u_n + \frac{\Delta t}{6}\left(k_1 + 2k_2 + 2k_3 + k_4\right)$$

The weights (1, 2, 2, 1) give RK4 its **4th-order accuracy**—error scales like $O(\Delta t^4)$.

---

## Performance baselines

The reference implementation (`reference.py`) uses PyTorch for optimization. The main benchmark timing that your CUDA kernel should aim to beat:

| Grid Size | Time Steps | PyTorch baseline (ms) | Naive Triton (ms) | Naive CUDA (ms) |
|-----------|------------|------------------------|-------------------|-----------------|
| 600       | 10         | 1458 ± 3ms               | 317 ± 3ms            | 148 ± 1ms           |

Your CUDA kernel should achieve significant speedups over this PyTorch baseline through custom memory access patterns, shared memory optimization, and kernel fusion. The naive CUDA and Triton implementations provide baselines for what straightforward translations achieve.

**Note on Accuracy requirement:** The harness checks for ≈1e-6 agreement in the final field with the reference (`rtol=1e-6`, `atol=1e-6`), so your CUDA kernel must reproduce this exactly.

