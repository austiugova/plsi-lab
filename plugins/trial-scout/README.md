# Trial Scout

Ask the Cursor agent about clinical trials, for yourself or a patient, and it searches ClinicalTrials.gov:
- recruiting studies for a condition near a place, best fit first;
- age and sex checked against each study's limits, by code;
- the full eligibility criteria, sites and contacts of a study, explained in plain words with the registry link.

Commands: `/trials-find`, `/trial-show`. The registry client is the one PLSI uses.

## Your data

Only the search words (condition and place) go to ClinicalTrials.gov; age and sex are checked on your computer and
never sent. It runs on macOS and Linux (Windows through WSL) and needs Python 3.11+ with pydantic 2 and PyYAML; if
they are missing, the agent asks before setting up a private environment with uv.

## Moving to PLSI

[PLSI](https://longevitygrok.si/) matches trials against your own health record and tells you when new ones open.

Not medical advice: see [DISCLAIMER.md](DISCLAIMER.md). MIT License.
