# labjournal.journal

The wet-lab journal of the Lab Journal plugin (`lj`, skill `lab-journal`). Everything lives under
`<home>/journal/`:

```
entries/<id>/entry.json      the current version: the entry, its version, hash and signature
entries/<id>/history.jsonl   one line per save and per signature (version, time, status, hash)
entries/<id>/files/          gel photos, micrographs, plate exports, traces, FCS files (`lj attach`)
plasmids/<name>.json         a plasmid: length, features, sequence when known
days/<date>.json             the day's plan (`lj day save`), shown by `lj today` and on the Today tab
journal.html                 the page (`lj page`), rebuilt after every command that changes the journal
```

| Module | Role |
|---|---|
| `home` | where everything above lives |
| `models` | `EntryInput` (what the agent writes): aim, protocol, reagents, samples, plate, observations, record |
| `results` | the typed results per kind (Cts, lanes, bands, cell index, readings, images, passages, vessels, gates, animals) |
| `store` | entries: save (next version, history line), list, show with `derived`, sign, attach; the status (signed once signed) |
| `analysis` | numbers derived from raw results: 2^-ΔΔCt, band ÷ loading control, blank and standard curve, normalised cell index, gates from exported counts, doubling time; well roles; each block with its checks |
| `animals` | animal studies run in PLSI: groups, animals and weights are kept as recorded |
| `flow` | flow gating runs in PLSI: FCS files and gates are kept as recorded |
| `plasmid` | plasmids on disk, GenBank import, and where the enzymes of `enzymes.csv` cut, with ends and overhangs |
| `ladders` | DNA ladders by product name (`ladders.csv`): standard band sizes for a ladder lane recorded without sizes; an ambiguous or unknown name is a check |
| `cellbank` | an entry's flasks, plates and vials (the lab-wide cell bank runs in PLSI) |
| `days` | the bench planner: one plan per day, and `lj today` |
| `calc` | bench calculators (`lj calc`) |
| `stats`, `tuning` | the statistics the checks use; every threshold, display limit and file cap in one place |
| `templates` | a starter entry per experiment kind (`lj template`) |
| `inplsi` | the line and link for features that run in PLSI |
| `page` | the payload and the page: `journal.html` (the frame and its CSP) filled with `page/journal.css` and the script parts of `page/` in `page.SCRIPT` order: `core` (DOM, icons, colours, cards), one part per area of views, `shell` (sidebar, overview) and `app` (routing, reload) |

Rules: code computes and flags; the conclusion is the scientist's. A signed entry is never saved again: a correction
is a new entry with `amends`. Nothing in the journal leaves the computer.
