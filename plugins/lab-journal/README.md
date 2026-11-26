# Lab Journal

A wet-lab notebook that the Cursor agent keeps on your computer. Each experiment is one entry with versions and
signing. It includes plasmid maps with restriction sites, a cell bank, day plans and one page to open in a browser.
Bench numbers come from tested code, not the model's arithmetic: dilutions, molarity, master mixes, seeding,
RT-qPCR ΔΔCt with flags, gel sizes, western ratios and standard curves.

## Use

Ask in Agent chat ("log my qPCR", "how much stock for 100 µM in 1 mL?"), or use the commands `/journal-today`,
`/journal-log`, `/journal-page`, `/journal-calc` and `/journal-export`. Before signing, the `bench-reviewer`
agent reads the entry and asks about missing controls and flags.

On first use the agent installs the code to `~/lab-journal/` (or `$LABJOURNAL_HOME`). It checks every file and runs
a self-test before keeping any record. It runs on macOS and Linux (Windows through WSL) and needs Python 3.11+ with
pydantic 2. If you don't have it, the agent asks before setting up a private environment with uv.

## Your data

Entries stay in `~/lab-journal/journal/` and are never sent anywhere unless you ask. While the plugin is
installed, the agent cannot edit or delete journal files directly: changes go through the journal's commands, and
signed entries never change.

## Moving to PLSI

[PLSI](https://longevitygrok.si/) keeps the same journal in the same format and adds flow cytometry
gating, animal studies, the lab's cell bank, research projects, bioinformatics and write-ups with checked
citations. Records of FCS files, animals and frozen vials are kept here as you write them, ready for PLSI. `/journal-export` packs your journal so you can bring it over.

MIT License.
