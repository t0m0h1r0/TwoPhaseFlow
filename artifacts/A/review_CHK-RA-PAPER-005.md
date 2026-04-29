# CHK-RA-PAPER-005 — Caption Title/Note Separation Review

Date: 2026-04-29
Worktree: `.claude/worktrees/ra-paper-strict-review-20260429`
Branch: `ra-paper-strict-review-20260429`
Source commit: `a126a49` (`paper: separate caption titles from notes`)
Main merge: performed by no-ff merge commit `8964664`; continue in the retained worktree.

## Trigger

User request:

> 論文全般について、図表のタイトルに詳細な説明を述べるのはやめて。タイトルとして相応しい命名をして。詳細な説明は本文もしくは、図表に付随する形で記載して。

## Format Policy Applied

- Numbered `\caption{...}` is treated as the figure/table title.
- Titles are short noun phrases: object, experiment/result ID, and metric only.
- Titles do not contain explanatory sentences, result interpretation, panel-by-panel explanation, or long condition lists.
- Details are moved into `\PaperCaptionNote{...}` directly attached to the same figure/table.
- Captions with only a title should not end with Japanese sentence punctuation `．`.
- Conditions such as grid size, time step, panel mapping, and measured interpretation belong in the note unless they are essential to the short name.

## Findings and Fixes

| ID | Finding | Fix |
|---|---|---|
| F01 | Many captions combined a title and a paragraph of result interpretation. | Split title and explanatory text into `\caption{...}` + `\PaperCaptionNote{...}`. |
| F02 | Several titles included panel mapping or simulation conditions in parentheses. | Moved those conditions into the associated note. |
| F03 | Some titles were full sentences ending in `．`. | Converted them to title-like noun phrases without sentence punctuation. |
| F04 | There was no reusable note style for figure/table supplementary explanation. | Added `\PaperCaptionNote` in `paper/preamble.tex`. |

## Representative Changes

- `気液界面における密度・粘性のジャンプ（左：...）` → `気液界面における密度・粘性のジャンプ` + note.
- `V1：TGV 渦度場 ...（N=64, ...）` → `V1：TGV 渦度場スナップショット` + note.
- `U4-a：Godunov Eikonal ...（N=128, ...）` → `U4-a：Godunov Eikonal バンド勾配誤差` + note.
- `PPE 離散化方式の比較（静止液滴，N=64，200 ステップ）` → `PPE 離散化方式の比較` + note.

## Reproduction Commands

```bash
python3 - <<'PY'
from pathlib import Path
import re, sys
pat = re.compile(r'\\caption(?:\[[^\]]*\])?\{', re.S)
viol = []
for p in sorted(Path('paper/sections').glob('*.tex')):
    s = p.read_text()
    for m in pat.finditer(s):
        if s.startswith('\\caption*', m.start()):
            continue
        i = m.end()
        depth = 1
        j = i
        while j < len(s) and depth:
            if s[j] == '\\':
                j += 2
                continue
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
            j += 1
        cap = ' '.join(s[i:j-1].strip().split())
        line = s.count('\n', 0, m.start()) + 1
        if '．' in cap or len(cap) > 58:
            viol.append(f'{p}:{line}: long/period: {cap}')
        if '（' in cap and any(tok in cap for tok in ['N=', 'T=', 'ステップ', '固定', '共有', '境界', '格子', '左', '右', '円形', '比', '誤差']):
            viol.append(f'{p}:{line}: paren-detail: {cap}')
if viol:
    print('\n'.join(viol))
    sys.exit(1)
print('OK: caption titles are concise')
PY
(cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex)
rg -n 'LaTeX Warning|Package .* Warning|Overfull \\hbox|Underfull \\hbox|Missing character|Undefined control sequence|Emergency stop|Fatal error|^!' paper/main.log
git diff --check
make lint-ids
```

## Results

- Caption-title audit: OK.
- `\PaperCaptionNote{...}` occurrences after the pass: 79.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: OK.
- `paper/main.pdf`: 234 pages.
- Final `main.log` diagnostic grep: 0 hits.
- `git diff --check`: OK.
- `make lint-ids`: OK.

## SOLID-X

Paper and review documentation only. No `src/twophase/` or production class/module boundary change.
