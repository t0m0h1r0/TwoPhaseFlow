# **CURRENT STATE & HANDOVER**

*Note: This file should be continuously updated by the Orchestrator or human developer. Keep it to current status + pending items only — all resolved-issue history lives in `paper/CHANGELOG.md`.*

## **1. Project Status Summary**

* **Date/Update:** 2026-03-22
* **Code:** 39 tests passing (pytest src/twophase/tests). Architecture fully refactored to use SimulationBuilder and component injection. `DissipativeCCDAdvection` implemented (§5); code-paper gap CLOSED. config_loader YAML round-trip fixed; ε_factor<1.2 warning implemented; 3 dead-code removals (refactor).
* **Paper:** 12 sections + 5 appendices. **20 CRITIC passes + 29 EDITOR sweeps complete (2026-03-22).** Build pending recompile (last clean: 119 pages, 2026-03-21).

## **2. Completed (2026-03-22)**

5. ~~WENO5 → Dissipative CCD global paper sweep~~ — **Done (2026-03-22, commit 1f5d7ee).** 30+ WENO5 references replaced across 7 non-appendix files. WENO5 retained in appendix as reference scheme only.

6. ~~20th CRITIC pass (full review including appendix)~~ — **Done (2026-03-22, commit 24ee31a).** 4 clarity fixes: (A) Balanced-Force warnbox explicit note that Dissipative CCD ≠ standard CCD for NS terms; (B) H(π;0.05)=0.80 Nyquist damping calculated; (C) ψ clamp note in Step 1 of 09_full_algorithm.tex; (D) O(h⁵Δt) mass conservation derivation step completed.

7. ~~DissipativeCCDAdvection implementation~~ — **Done (2026-03-22).** `DissipativeCCDAdvection(ILevelSetAdvection)` added to `levelset/advection.py`. `advection_scheme` field added to `NumericsConfig` (default `"dissipative_ccd"`, alternative `"weno5"`). `SimulationBuilder` updated to select scheme from config. 2 new MMS tests added (spatial order ≥ 1.8 O(h²), full method order ≥ 1.8). **33 tests passing.** Code-paper gap CLOSED.

8. ~~§5 paper inserts (WENO5 critique + warn:adv_risks)~~ — **Done (2026-03-22).** Added `\subsubsection{移流スキーム選択の設計根拠}` (label: `sec:advection_weno5_critique`) and `warn:adv_risks` tcolorbox warnbox to `05_advection.tex`. Fixed cross-refs (`eq:Heps_def_preview`, `sec:ccd_bc`).

9. ~~Appendix D↔E reorder~~ — **Done (2026-03-22).** `appendix_numerics_schemes` (first-ref §5) moved before `appendix_numerics_solver` (first-ref §8) in `paper/main.tex`.

10. ~~config_loader YAML round-trip fix + ε_factor warning~~ — **Done (2026-03-22).** Added `advection_scheme` to `config_loader.py` load/`_known`/dump. Added `UserWarning` in `NumericsConfig.__post_init__` for `epsilon_factor < 1.2` with `dissipative_ccd`. Added `test_config.py` (6 tests). **39 tests passing.**

11. ~~Dead code refactor (SAFE_REMOVE)~~ — **Done (2026-03-22).** Removed 3 items: `_pad_zero` alias (0 call sites, `advection.py`), `Optional` unused import (`config_loader.py`), `TYPE_CHECKING` unused import (`_core.py`).

## **2. Completed (2026-03-21)**

4. ~~Mathematical audit §§6–11 + all appendices + EDITOR sweep 29~~ — **Done (2026-03-21).** 19 appendix sections + 6 main sections verified. Zero PAPER_ERROR. 5 documentation-level fixes applied: (1) §6 pseudocode comment "台形則"→"矩形則（前進型）", (2) §7 Balanced-Force algebra with incorrect κ-factoring removed, (3) §8b spectral radius formula 4a₂/[(1+2|β₂|)h²]=9.6≠3.43 clarified, (4) §10 O(h⁴) pre-asymptotic note added, (5) appendix capillary CFL "保守的に"→"近似的に".

## **3. Pending Action Items**

### **Code / Implementation**

1. Run benchmarks at higher resolution (N=128) and compare to reference values.
2. Verify GPU backend compatibility (CuPy).
3. Implement and test 3D cases.
4. Implement VTK output writer in io/.

### **Paper / Documentation**

1. ~~EDITOR sweep 27~~ — **Done (2026-03-20).** All CRITIC pass 18 issues fixed (5 FATAL + 5 GAP + 2 IMPL + 2 MAINT). Clean build: 116 pages, 0 undefined refs. Ready for submission review or further CRITIC pass.
2. ~~CCD block matrix A_L/A_R (2,1) sign error fix~~ — **Done (2026-03-20).** Fixed 3 locations in `05b_ccd_bc_matrix.tex` (defbox symbolic form, bullet derivation, numeric example). Paper had A_L(2,1)=+9/(8h) and A_R(2,1)=−9/(8h); correct values are A_L(2,1)=−9/(8h) and A_R(2,1)=+9/(8h). Code was already correct. Also fixed `ARCHITECTURE.md` "3×3 blocks" → "2×2 blocks".
3. ~~EDITOR sweep 28~~ — **Done (2026-03-21).** External reviewer found 1 CRITICAL math error + 1 terminology inconsistency in §§2.1, 3.2. Spurious `- ∫ψ(∇·u)dV` term removed from CLS volume-conservation formula; warnbox rewritten. "球状液滴" → "円形液滴（2次元）" in §2.1 warnbox.
