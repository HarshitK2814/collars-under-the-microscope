# Experiment log v2 (append-only)

Development = 2011-2016, validation = 2017-2019. 2020-2026 is a seen period (v1 reported it).

| ID | Date | Period | What changed | Why | Result |
|---|---|---|---|---|---|
| EXP-V2-000 | 2026-11-09 | - | Evidence file read; prereg v2 written and frozen before any v2 test. qcore vendor diff vs root checked: only `Splits.forward` differs (root superset), so P2 added to tools/vendor_sync.py and synced | plan 09 | Hash recorded in the freeze commit message |
