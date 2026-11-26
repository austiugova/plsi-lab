# Lab Report

Give the Cursor agent a blood test (a lab PDF, a photo or the values) and it reads it with tested code:
- units converted (mg/dL, g/dL, µmol/L and so on), each value against the lab's printed range;
- your **blood-test age** (PhenoAge, Levine 2018) from nine routine markers, next to your age;
- a one-page card to open, print or share.

Commands: `/lab-read`, `/lab-card`. The numbers come from the same code PLSI uses, checked by a self-test on install.

## Your data

Reports stay in `~/lab-report/` (or `$LABREPORT_HOME`). Only birth year and sex are asked; never a name. Nothing is
sent anywhere. It runs on macOS and Linux (Windows through WSL) and needs Python 3.11+ with pydantic 2 and PyYAML;
if they are missing, the agent asks before setting up a private environment with uv.

## Moving to PLSI

[PLSI](https://longevitygrok.si/) keeps all your reports in one record and shows where your values are heading, what
a change would do, and adds wearables. Saved reports are already in PLSI's import format.

Not medical advice: see [DISCLAIMER.md](DISCLAIMER.md). MIT License.
