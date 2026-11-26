# Visit Prep

Before a doctor's visit, the Cursor agent puts what matters on one printable page:
- the reason for the visit and what changed since the last one;
- recent results with their change since the last test (from the Lab Report plugin, or as you give them);
- current medicines and supplements, and 3-7 questions to ask;
- space for notes during the visit.

For patients ("For my visit") and physicians (a brief for one patient, by label, never a name). Command: `/visit-prep`.

## Your data

The page stays on your computer; nothing is sent anywhere. It runs on macOS and Linux (Windows through WSL) and needs
Python 3.11+ with pydantic 2 and PyYAML; if they are missing, the agent asks before setting up a private environment
with uv.

## Moving to PLSI

[PLSI](https://longevitygrok.si/) keeps the full record, gives physicians a clinic dashboard, and carries messages
between patient and physician.

Not medical advice: see [DISCLAIMER.md](DISCLAIMER.md). MIT License.
