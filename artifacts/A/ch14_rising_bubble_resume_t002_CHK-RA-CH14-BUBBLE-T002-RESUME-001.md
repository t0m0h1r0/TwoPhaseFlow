# CHK-RA-CH14-BUBBLE-T002-RESUME-001: rising bubble continuation to T=0.02

## Request

Continue the 10 mm x 20 mm, 32 x 64 water-air rising-bubble run from the
previous `T=0.01` result and advance toward `T=0.02`.

## Reproducibility YAML

```text
experiment/ch14/config/_tmp_ch14_rising_bubble_n32_t002_resume.yaml
```

This YAML keeps the same numerical and physical stack as the `T=0.01` probe:

```text
domain        = 10 mm x 20 mm
grid          = 32 x 64
rho_l/rho_g   = 1000.0 / 1.2
mu_l/mu_g     = 1.0e-3 / 1.8e-5
sigma         = 0.072
gravity       = 9.81
momentum_form = primitive_velocity
final time    = 0.02 s
```

The restart command used the pre-step continuation checkpoint, not the
post-step final checkpoint:

```text
make cycle EXP=experiment/run.py \
  ARGS="--config _tmp_ch14_rising_bubble_n32_t002_resume \
        --resume-from /root/TwoPhaseFlow/experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/checkpoint_continuation.npz"
```

Attempting to restart from `checkpoint_final.npz` was correctly rejected:

```text
--resume-from requires a pre-step continuation checkpoint; post-step
checkpoints are analysis artifacts and may include a terminally shortened
timestep
```

This confirms that the restart guard follows the prior design rule: restart
from the last input frame, not the terminal output frame.

## Outcome

The restart was accepted:

```text
[resume] loaded ... checkpoint_continuation.npz at step=1358
t=0.0099952543 phase=pre_step
```

The run did not reach `T=0.02`.  It tripped the blow-up guard at:

```text
step = 2470
t    = 0.018033000472938543
```

The code saved:

```text
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t002_resume/data.npz
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t002_resume/checkpoint_pre_blowup_input.npz
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t002_resume/checkpoint_continuation.npz
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t002_resume/checkpoint_final.npz
```

## Final Metrics

```text
t_final_saved                 1.8033000472938543e-02
volume_conservation_final     4.4367822130070515e-03
yc_final                      5.6893607696381920e-03
mean_rise_velocity_final      5.7701327692647530e-01
deformation_final             3.1860804355372620e-01
kinetic_energy_final          1.7451694892515037e+06
div_u_max_final               4.9532638257369400e-01
kappa_max_final               2.7163222260292973e+03
ppe_rhs_max_final             4.8299429895844104e+16
bf_residual_max_final         4.7079653005083331e+14
dt_advective_final            1.7233282179751407e-09
dt_capillary_final            7.2485999329241760e-06
capillary_contract_gate_code  0
```

The kinetic energy remained small through about `t=0.0180`, then grew
catastrophically:

```text
KE > 1e-3 at t=0.018002600052937603
KE > 1e-2 at t=0.018017042196463183
KE > 1e-1 at t=0.018028937729434900
KE > 1    at t=0.018030835407344643
KE > 1e3  at t=0.018032888628203823
```

The last eight recorded steps show collapse of the advective time scale and a
rapid pressure/balanced-force residual explosion:

```text
t             KE          dt_adv      ppe_rhs      bf_res      div_u
0.018032954   9.875e+03   2.551e-08   2.181e+14   2.227e+12   6.015e-02
0.018032970   2.246e+04   1.630e-08   5.256e+14   5.387e+12   4.072e-02
0.018032981   5.083e+04   1.078e-08   1.213e+15   1.225e+13   1.431e-01
0.018032988   1.079e+05   7.184e-09   2.715e+15   2.734e+13   1.004e-01
0.018032993   2.240e+05   4.919e-09   5.814e+15   5.767e+13   1.328e-01
0.018032996   4.587e+05   3.423e-09   1.211e+16   1.199e+14   2.299e-01
0.018032999   8.839e+05   2.386e-09   2.456e+16   2.414e+14   2.975e-01
0.018033000   1.745e+06   1.723e-09   4.830e+16   4.708e+14   4.953e-01
```

## Interpretation

The continuation/restart mechanism worked.  The failure is not a checkpoint
loading failure and not the old "resume from terminal output frame" problem.

The short-run interpretation is:

```text
1. T=0.01 is stable.
2. Restart from the pre-step continuation frame is accepted.
3. The same physical/numerical stack fails near t=0.01803 before T=0.02.
4. The saved checkpoint_pre_blowup_input.npz is the correct next RCA input.
```

The capillary contract gate did not fail (`gate_code = 0`), and the capillary
pressure-adjoint residual stayed around `0.35`.  The immediate numerical
signature is instead a coupled acceleration / pressure RHS / balanced-force
residual blow-up with rapidly shrinking advective time scale.  This should be
studied from `checkpoint_pre_blowup_input.npz`, preferably by replaying one
step with individual term budgets and conservative-common-flux momentum
diagnostics.
