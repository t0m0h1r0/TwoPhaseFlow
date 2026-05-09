# CHK-RA-CH14-BHODGE-001: Boundary Hodge Wall-Trace Validation

## Question

Can the small wall velocity residual in the rising-bubble face-native
projection be removed by a metric projection of the reconstructed wall trace
without violating the pressure Hodge divergence constraint?

## Implemented Object

The implemented diagnostic projection is

\[
  \min_{\hat f}\frac12\|\hat f-f\|_{M_f}^2
  \quad\text{subject to}\quad C_w\hat f=0,
\]

where \(C_w f\) is the wall trace of the production face-to-node
reconstruction \(R_h f\).  The Schur operator

\[
  C_w M_f^{-1} C_w^T
\]

is applied matrix-free and solved by backend CG.  The adjoint \(C_w^T\) is the
exact array adjoint of `reconstruct_nodes_from_faces`, including mixed
periodic-wall unique image handling.

## Unit Verification

Remote targeted tests:

```text
python -m pytest \
  twophase/tests/test_boundary_hodge.py \
  twophase/tests/test_config_io_fccd.py::test_ch14_rising_bubble_yaml_loads_execution_stack \
  twophase/tests/test_ns_pipeline_fccd.py::test_ch14_rising_bubble_yaml_builds_solver \
  -v --tb=short
```

Result:

```text
5 passed in 0.21s
```

Earlier full remote pytest during the same implementation pass:

```text
643 passed, 33 skipped in 42.88s
```

## Efficient Runtime Probe

Temporary rising-bubble probe, same numerical stack as
`ch14_rising_bubble.yaml`, with `Nx=32`, `Ny=64`, `max_steps=20`.

### Wall-Trace Projection Enabled

The diagnostic projection drove the wall trace to roundoff:

```text
boundary_hodge_wall_initial_linf: max 1.451986e-04
boundary_hodge_wall_linf:         max 1.974780e-11
boundary_hodge_reconstruct_delta: max 1.974780e-11
```

However, it destroyed the pressure-projected divergence:

```text
boundary_hodge_div_linf: max 4.314673e-02
step div_u:              about 3.870e-02
```

### Boundary Hodge Off

With the same probe and `boundary_hodge.mode: off`, the existing pressure
projection remained divergence-consistent:

```text
step 1 div_u: 7.073e-07
step 2 div_u: 2.988e-09
step 10 div_u: 9.691e-11
step 20 div_u: 8.915e-11
```

## Conclusion

The wall-trace-only projection is mathematically valid as the \(M_f\)-orthogonal
projection onto \(\ker C_w\), but it is not a production fix for the rising
bubble because the physical target is the intersection

\[
  K_h=\{f: D_h f=0,\ C_w f=0\}.
\]

Applying only \(P_{\ker C_w}\) after the pressure Hodge projection moves the
state out of \(\ker D_h\).  Therefore `ch14_rising_bubble.yaml` keeps the new
`boundary_hodge` UX block in `mode: off` with `gate: diagnostic`.  Enabling it
with `gate: fail_close` correctly fails if the divergence residual is large.

The next valid production direction is a properly preconditioned matrix-free
coupled \((D_h,C_w)\) KKT solve using the same homogeneous pressure operator as
the production affine-jump PPE, not a post-hoc wall clipping or wall-only
projection.
