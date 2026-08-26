# 05 — api.md slimming boundary

Type: grilling
Status: resolved
Claimed by: claude
Blocked by: 01, 02

## Question

Which sections of `docs/api.md` stay and which go, now that docstrings become the canonical
per-method reference (Q5=a)? Decide the boundary:

- **Keep** the conceptual guide: the mental model (how dimensions/metrics/trends relate), the
  quickstart, and the import/cheatsheet orientation.
- **Remove** the per-method prose that the docstrings now hold authoritatively (the long
  Parameters/Examples blocks currently duplicated in `api.md`).
- **Link strategy** — how `api.md` points readers to the canonical reference (e.g. "full signature
  and examples in the docstring / source," possibly with a generated summary table).

HITL — the user weighs in on what stays, since `api.md` is the published docs site's most-read
page and the slimming is a judgment call. Resolving this is what stops the docstring ↔ `api.md`
drift permanently.

## Answer

The slimmed `api.md` becomes the **Python-surface orientation page**; the mental model stays on
`docs/concepts.md` (which already owns it). User signed off — all recommendations accepted across
two grilling rounds.

**Boundary (what stays / what goes):**

1. **Mental model → deferred to `concepts.md`.** One cross-link near the top replaces the duplicated
   lifecycle/primitives prose. api.md = "how you drive the Python API"; concepts.md = "why it works
   that way." Biggest drift-prevention lever, and it falls straight out of Q5=a.
2. **Per-method reference sections removed** (`## ⚙️ Configuration Methods` and `## 📊 Retrieval,
   Aggregation, Normalization & Visualization`). The duplicated `Parameters`/`Raises`/`Examples`
   blocks now live authoritatively in the docstrings. Replaced with a **one-line-per-method summary
   table** grouped by workflow stage (configure → retrieve/transform/visualize), each row:
   `name — one-line gist — "signature & examples: see source"`.
3. **`## 🏛️ The DataGen Class` section slimmed, not removed.** Keep the class intro + `__init__`
   signature + a one-line-each properties orientation map ("the knobs and the read-outs"). Drop the
   per-parameter prose (moves to the `__init__` docstring). Properties stay as `name — what it
   returns`, consistent with the style guide's getter-is-the-hover convention (ticket 02 §4).
4. **Lifecycle script trimmed to the core flow** the doctests already cover — construct →
   `add_dimension` → `add_metric` (trend composition) → `.data` → `.aggregate`. Dropped: multi_items,
   normalize, denormalize, plot (those live in their per-method illustrative examples). The full
   lifecycle, if wanted, belongs on a separate cookbook page — out of this ticket's scope.
5. **`## 🏗️ Internal Architecture` section removed.** Each entry is either conceptual (already in
   `concepts.md` — `MetricResult`/baseline-vs-signal, pipeline/seed model) or internal implementation
   (`SeedableRNG`, `Schema Parser`, `aggregate_dataframe` — out of scope per Q2=b). At most one
   sentence points to `concepts.md` for the pipeline/seed model.

**Link mechanism:** each table row's method name links to its **source file on GitHub** (blob URL,
path-only — no line numbers, which drift on every docstring edit; file paths rarely move). Most rows
share one URL (all `DataGen` methods → `data_gen.py`), so it's effectively a per-file link repeated —
hand-maintained, near-zero drift. Rejected: a bare "see source" note (too thin for a web reader); a
single section-level link (loses per-symbol navigability); any auto-generated link table (the
pipeline Q1=b ruled out).

**Summary-table scope: `DataGen`-only** (methods + properties). The per-area pages (`/trends`,
`/anomalies`, `/dimensions`) already carry reference for the other primitives and are linked from
`concepts.md`; expanding `api.md` to a full ~58-symbol index would duplicate that structure and
re-create the drift surface. Whether those per-area pages need the same slim treatment is out of
this effort's scope (see the map's Out of scope).

**Execution (deferred):** this ticket resolves the *decision* only; writing the slimmed `api.md` is
do-phase execution. The summary-table one-liners must be copied from finalized docstring summary
lines (inventing them now would re-introduce drift), so the populated table can only land at the end
of the docstring-writing bulk, sequenced after pilot 07 validates. Recorded as fog in the map's
Not-yet-specified; not a ticket yet (can't be sharply scoped until the bulk is sequenced).