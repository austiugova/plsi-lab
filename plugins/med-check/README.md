# Med & Supplement Check

Give the Cursor agent your list of medicines and supplements and it reads each medicine's official FDA label
(openFDA, with the active ingredient found through NIH RxNav):
- warnings, contraindications and interaction sections that name your other medicines, supplements, conditions or
  allergies, quoted with the label link;
- boxed warnings, and the most serious mentions (contraindications) first.

Command: `/med-check`. The label screening is the one PLSI uses.

This is not a full interaction database: a label can be silent about a real interaction, and supplements have no FDA
label. Always check with your pharmacist or prescriber.

## Your data

Only the names of the items go to RxNav and openFDA; conditions are matched on your computer. Without a key, openFDA allows
1,000 label lookups a day; set `OPENFDA_API_KEY` for more. It runs on macOS and
Linux (Windows through WSL) and needs Python 3.11+ with pydantic 2 and PyYAML; if they are missing, the agent asks
before setting up a private environment with uv.

## Moving to PLSI

[PLSI](https://longevitygrok.si/) checks a whole plan before any change, against your full health record.

Not medical advice: see [DISCLAIMER.md](DISCLAIMER.md). MIT License.
