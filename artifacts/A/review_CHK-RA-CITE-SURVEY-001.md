# CHK-RA-CITE-SURVEY-001 Citation Survey Record

## Scope

- Surveyed literature directly related to the manuscript's current methods:
  CLS/reinitialization, high-order compact CLS, balanced-force level-set
  surface tension, consistent mass-momentum transport, and variable-density
  pressure correction.
- Added only papers whose existence and content match were verified from DOI,
  publisher, university repository, or article metadata pages.
- No equation, numerical parameter, solver route, experiment result, or
  benchmark claim was changed.

## Added References

| Key | Verified paper | Evidence | Manuscript use |
|---|---|---|---|
| `OlssonKreissZahedi2007` | Olsson, Kreiss, and Zahedi, "A conservative level set method for two phase flow II", JCP 225(1), 785--807, DOI `10.1016/j.jcp.2006.12.027`. | ScienceDirect records it as the 2007 continuation of the 2005 CLS paper, with modified reinitialization and conservation analysis for incompressible two-phase flow with surface tension. | §1 roadmap and §3 CLS chapter now cite it for CLS conservation/reinitialization theory beyond the 2005 base paper. |
| `MoghadamShafieefarPanahi2016` | Mahmoudi Moghadam, Shafieefar, and Panahi, "Development of a high-order level set method: Compact Conservative Level Set (CCLS)", Computers & Fluids 129, 79--90, DOI `10.1016/j.compfluid.2016.02.002`. | ScienceDirect describes high-order compact transport of CLS and a CCD reinitialization equation for mass-conserving level set simulation. | §1 and §3 cite it as a close high-order compact CLS neighbor, while distinguishing this manuscript's later pressure/capillary ledger scope. |
| `Herrmann2008` | Herrmann, "A balanced force refined level set grid method for two-phase flows on unstructured flow solver grids", JCP 227(4), 2674--2706, DOI `10.1016/j.jcp.2007.11.002`. | The article metadata/abstract states that it extends balanced-force ideas to a refined level-set grid and reports reduced spurious currents. | §1 balanced-force related work now notes the level-set branch, not only the VOF branch. |
| `Rudman1998` | Rudman, "A volume-tracking method for incompressible multifluid flows and large density variations", IJNMF 28(2), 357--378, DOI `10.1002/(SICI)1097-0363(19980815)28:2<357::AID-FLD750>3.0.CO;2-D`. | Monash repository verifies publication metadata; later article abstracts identify Rudman's approach as coupling mass and momentum flux transport for high-density-ratio two-phase simulation. | §1 and §11 cite it as the VOF-side origin of the consistent mass-momentum transport problem. |
| `RaessiPitsch2012` | Raessi and Pitsch, "Consistent mass and momentum transport for simulating incompressible interfacial flows with large density ratios using the level set method", Computers & Fluids 63, 70--81, DOI `10.1016/j.compfluid.2012.04.002`. | RWTH verifies metadata; ScienceDirect abstract states that the method uses the same flux density for mass and momentum transport and tests density ratios 650--10^6. | §1 and §11 cite it as the level-set-side analogue for the common-flux ledger motivation. |
| `DoddFerrante2014` | Dodd and Ferrante, "A fast pressure-correction method for incompressible two-fluid flows", JCP 273, 416--434, DOI `10.1016/j.jcp.2014.05.024`. | ScienceDirect abstract states that splitting the variable-density pressure gradient reduces the variable-coefficient Poisson problem to a constant-coefficient one, with large density/viscosity ratio tests. | §9 split-PPE text cites it as shared pressure-correction motivation while distinguishing this manuscript's jump/HFE/DC focus from FFT acceleration. |

## Exclusion Notes

- Existing bibliography already covers the base LS/VOF/CSF/GFM/projection
  spine: Osher--Sethian, Sussman, Hirt--Nichols, Brackbill, François,
  Popinet, Fedkiw/Kang/LeVeque--Li, Chorin/van Kan/Guermond, Hysing, and
  benchmark references. These were not duplicated.
- Newer broad reviews and adjacent phase-field/CLSVOF papers were not added
  because the current manuscript claim sites are already supported by the
  closer primary sources above.

## Files Changed

- `paper/bibliography.bib`
- `paper/sections/01b_classification_roadmap.tex`
- `paper/sections/03_levelset.tex`
- `paper/sections/09b1_split_ppe.tex`
- `paper/sections/11_full_algorithm.tex`
- `docs/wiki/paper/WIKI-P-020.md`
- `docs/wiki/INDEX.md`

## Validation

- `git diff --check`: PASS.
- `make -B -C paper`: PASS; generated `paper/main.pdf`, 279 pages.
- Final `paper/main.log` diagnostic scan: PASS; no LaTeX/package/class
  warnings, overfull/underfull boxes, undefined citations/references/control
  sequences, emergency stops, fatal errors, or raw TeX errors.

## Verdict

The added citations are claim-local, source-verified, and limited to literature
that materially sharpens the manuscript's positioning. Main has not been
merged.
