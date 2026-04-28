# ID Namespace v7.1.0 — Worktree並列時のチケットID衝突を構造的に防ぐ

**Date**: 2026-04-28
**Branch**: `worktree-ra-meta-id-namespace`
**Session prefix**: `RA-META` (dogfood: CHK-RA-META-001)
**Meta version**: 7.0.0 → 7.1.0 (additive minor bump)
**Scope**: CHK + ASM + KL families (SP/WIKIは別タスク)

## Problem statement

`git worktree`で並列セッションを走らせると、`docs/02_ACTIVE_LEDGER.md`のCHK-NNN番号を各worktreeが独立に「現在max+1」で採番するため、main へのマージ時に同一番号が衝突する。`docs/02_ACTIVE_LEDGER.md`はgit追跡下にあり、各worktreeが独自のコピーを保持するため、O_EXCLによる排他は別物理パスになり機能しない。

### Empirical evidence

| Incident | Outcome |
|----------|---------|
| **CHK-246** (2026-04-28) | merge `02a7cfe` と `3967d7a` が両方CHK-246を主張、未renumber、CHK-247欠番 |
| **CHK-161 → CHK-167** (2026-04-21) | commit `714cc96` で post-merge手動renumber |
| **CHK-225 → CHK-226** | `git reset --soft HEAD~2` + recommit |
| **CHK-115** | ledgerに「ID reused by 2 parallel worktrees」と明記 |
| **5/14** ledger touching merges (4月以降) | `Conflicts: docs/02_ACTIVE_LEDGER.md` |
| **SP-H → SP-N** | 同pattern (短論文ID) |

### Root cause

- `chk_id?: string;    // pattern: ^CHK-[0-9]{3,}$` が **任意** field (`prompts/meta/kernel-roles.md` L44)
- 採番は「ledger読んで+1」の暗黙慣習; agent promptに明文規定なし
- `BRANCH_LOCK_REGISTRY` は branch書き込みのみ保護、ID counterは保護せず
- `docs/locks/*.lock.json` は scaffold commit以来一度も実運用で生成されていない

## Decision: Option A — Worktree-Namespaced ID

### Why this option

| 基準 | A (採用) | B (atomic counter) | C (deferred) | D (B+C) |
|------|---------|------------------|--------------|---------|
| 衝突防止 | 構造的に不可能 | script依存・skipで崩壊 | placeholder衝突可 | Bの弱点を継承 |
| 実装 | meta-md ~10行 + 0 script | wrapper + flock + 全launcher改修 | merge側にrenumber pass | B+C両方 |
| LLM-friendliness | 純テキストで完結 | 外部script必須 | テキストで完結 | 外部script必須 |
| 後方互換 | 高 (regex拡張) | 高 | 高 | 高 |

決定打: 既存 `scripts/lock.py` ([`prompts/meta/kernel-ops.md`](../../prompts/meta/kernel-ops.md) L343 で参照) が一度も実装されず使われていない事実が、Bが現実的でないことを示す。

### ID format

```
CHK-{prefix}-{NNN}    # 新形式 (v7.1.0+)
CHK-NNN               # 旧形式 (legacy; 既存entryはそのまま有効)
ASM-{prefix}-{NNN}
KL-{prefix}-{NNN}
```

- `{prefix}`: branch名から決定論的に導出
- `{NNN}`: worktree-local counter, zero-padded 3桁, 各族独立
- 各worktreeは自分のprefixのみ使用、global counter不要

### Prefix derivation rule (§ID-NAMESPACE-DERIVE)

入力: branch名 (例: `worktree-ra-ch9-review`)

手順:
1. 先頭の `worktree-` または `wt-` セグメントを削除
2. ハイフン分割で先頭2トークンを取得
3. 英数とハイフンのみ残し、大文字化
4. 全長が9文字を超えるなら2トークン目を切詰めて9文字以内に収める
5. ledger §4で同prefixが**他の active session_id**と衝突する場合は3トークン目まで延伸

例:
| Branch | Prefix |
|--------|--------|
| `worktree-ra-ch9-review` | `RA-CH9` |
| `worktree-ra-ch11-review` | `RA-CH11` |
| `worktree-ch14-benchmark-bootstrap` | `CH14-BEN` |
| `worktree-ra-paper-ch4-rewrite` | `RA-PAPER` |
| `researcharchitect-src-refactor-plan` | `RESEARCH` (1トークン目で9文字到達) |
| `worktree-ra-meta-id-namespace` | `RA-META` (本セッション; dogfood CHK-RA-META-001) |

## Implementation Steps

このworktreeで段階的にコミットしながら以下を実施。**main マージはユーザー指示まで実行しない** (no-ff前提)。

| Step | Target | Commit subject |
|------|--------|----------------|
| 1 | `artifacts/A/id_namespace_v710_design.md` | `docs(meta): id-namespace v7.1.0 design summary` |
| 2 | `prompts/meta/kernel-ops.md` §ID NAMESPACE OPERATIONS 追加 | `meta(ops): add §ID NAMESPACE OPERATIONS` |
| 3 | `prompts/meta/kernel-roles.md` §SCHEMA EXTENSIONS v7.1.0 + ResearchArchitect step 1.5 | `meta(roles): v7.1.0 schema extensions for id_prefix` |
| 4 | `prompts/meta/kernel-deploy.md` BRANCH_LOCK_REGISTRY 拡張 | `meta(deploy): BRANCH_LOCK_REGISTRY gains id_prefix` |
| 5 | `prompts/agents-claude/_base.yaml` + codex版 | `meta(base): bump to v7.1.0; bind id_prefix at session start` |
| 6 | agent prompts regen (Claude + Codex) | `prompts(agents): regen for v7.1.0` |
| 7 | `Makefile` lint-ids / lint-id-refs target | `chore(make): add lint-ids and lint-id-refs targets` |
| 8 | 2-worktree merge test, log → `artifacts/A/id_namespace_v710_test_log.md` | `test(meta): two-worktree CHK collision-free verification` |
| 9 | `docs/02_ACTIVE_LEDGER.md` CHK-RA-META-001 entry | `ledger(active): CHK-RA-META-001 v7.1.0 id-namespace meta evolution` |
| 10 | STOP — await user approval | (no commit) |

## Risks and edge cases

| Risk | Mitigation |
|------|-----------|
| Agent が prefix を忘れて legacy `CHK-NNN` を emit | HAND-03 C7 schema validation で reject (extended regex に hit すれば pass; legacy form は v7.1.0以降の worktree session では reject) |
| Branch名変更 mid-session | `id_prefix` は ledger §4 BRANCH_LOCK_REGISTRY に session 開始時に固定書込み → mutable禁止 |
| 2 worktrees が同 prefix を導出 | step 1.5 で ledger §4 を読み、active同prefix存在時に3トークン目まで延伸 |
| main 自体が直接書込 | main は概念的に `id_prefix=MAIN` 固定。ただし worktree-first parallelism A8.1 に従い直接採番非推奨 |
| Legacy CHK refs (例: `kernel-constitution.md` L160 の CHK-114) | 拡張regex は legacy form も accept ⇒ 既存参照そのまま有効 |

## Out of Scope

- **CHK-246 retroactive renumber**: 永久 legacy collision として ledgerに注記、放置
- **CHK-247欠番**: 永久欠番のまま
- **SP-{letter}, WIKI-{T/L/E/A/X/P}-NNN**: 別schemeが必要、次タスクで対応
- **`scripts/lock.py` / `scripts/atomic_push.py` 実装**: 別問題 (branch write exclusion)
- **Legacy entries の retroactive prefix annotation**: forward-only migration

## Verification

### 2-worktree merge test (Step 8)

```bash
git checkout -b test-scratch-main main
git worktree add /tmp/wt-test-a -b test-id-a test-scratch-main
git worktree add /tmp/wt-test-b -b test-id-b test-scratch-main

# A: prefix=TEST-A
cd /tmp/wt-test-a
echo "| CHK-TEST-A-001 | $(date -u) | scratch | id_prefix collision test A |" >> docs/02_ACTIVE_LEDGER.md
git add docs/02_ACTIVE_LEDGER.md && git commit -m "test: CHK-TEST-A-001"

# B: prefix=TEST-B
cd /tmp/wt-test-b
echo "| CHK-TEST-B-001 | $(date -u) | scratch | id_prefix collision test B |" >> docs/02_ACTIVE_LEDGER.md
git add docs/02_ACTIVE_LEDGER.md && git commit -m "test: CHK-TEST-B-001"

# 両方 no-ff merge
git checkout test-scratch-main
git merge --no-ff test-id-a -m "merge A"
git merge --no-ff test-id-b -m "merge B"  # 期待: conflict 0

make lint-ids  # 期待: exit 0
```

### Lint targets

- `make lint-ids` — ledgerのCHK/ASM/KL重複検出
- `make lint-id-refs` — 全docs/promptsの参照IDがledger定義済みかcheck

## References

- Plan file: `/Users/tomohiro/.claude/plans/execute-researcharchitect-mutable-mitten.md`
- Existing schema extension pattern: [`prompts/meta/kernel-roles.md`](../../prompts/meta/kernel-roles.md) §SCHEMA EXTENSIONS v6.0.0 (L81+)
- Lock protocol: [`docs/locks/README.md`](../../docs/locks/README.md)
- Constitution §A8.1 Worktree-First Parallelism
