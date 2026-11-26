"""The `labjournal` command table: the wet-lab journal (entries, plasmids, the page) and the bench calculators."""

from __future__ import annotations

from labjournal.cmdspec import FILE, MX, A, Cmd, V, iso_date
from labjournal.vocab import LivePage
from labjournal.vocab.journal import CalcKind, ExperimentKind

JOURNAL = LivePage.JOURNAL

ENTRY = A("--entry", required=True, help="the entry id")

COMMANDS: dict[str, Cmd] = {
    "template": Cmd("labjournal.journal.store:template", (A("--kind", required=True, choices=V(ExperimentKind)),),
                            "a starter entry for one kind of experiment, to fill in and save",
                            ("labjournal save --file <entry.json>",)),
    "save": Cmd("labjournal.journal.store:save", (FILE,),
                        "save an entry (EntryInput JSON): the first version, or the next of an unsigned one",
                        ("labjournal page",), refresh=JOURNAL),
    "list": Cmd("labjournal.journal.store:list_entries",
                        (A("--project"), A("--kind", choices=V(ExperimentKind))), "entries, newest first"),
    "show": Cmd("labjournal.journal.store:show", (ENTRY,), "one entry with its derived numbers, checks and history"),
    "sign": Cmd("labjournal.journal.store:sign",
                        (ENTRY, A("--by", required=True, help="the scientist's name, as they gave it"),
                         A("--witness", help="a second person's name, when one witnessed it")),
                        "sign an entry the user approved: it never changes again", ("labjournal page",), refresh=JOURNAL),
    "attach": Cmd("labjournal.journal.store:attach",
                          (ENTRY, A("--file", required=True, help="the file on this computer"),
                           A("--name", help="the name to keep it under")),
                          "keep a gel photo, micrograph, export or trace with an unsigned entry",
                          ("labjournal save --file <entry.json>",), refresh=JOURNAL),
    "calc": Cmd("labjournal.journal.calc:calc",
                        (A("--kind", required=True, choices=V(CalcKind)),
                         A("--set", dest="set_values", action="append", help="name=quantity, e.g. c1='10 mM' (repeatable)"),
                         A("--file", help="the inputs as JSON (lists: mastermix components, protein_load samples)")),
                        "bench arithmetic with its steps (writes nothing)"),
    "plasmid save": Cmd("labjournal.journal.plasmid:save",
                                (MX(A("--file", help="Plasmid JSON"), A("--genbank", help="a GenBank file (.gb, .gbk)")),
                                 A("--name", help="short lower-case name (with --genbank)")),
                                "save a plasmid: its map, features and restriction sites", ("labjournal page",), refresh=JOURNAL),
    "plasmid list": Cmd("labjournal.journal.plasmid:list_saved", (), "saved plasmids"),
    "plasmid show": Cmd("labjournal.journal.plasmid:show",
                                (A("--name", required=True),
                                 A("--region", help="start-end, e.g. 1984-2048: enzymes cutting once in the plasmid, inside it")),
                                "one plasmid with its features, the enzymes that cut it, their ends and overhangs"),
    "day save": Cmd("labjournal.journal.days:save", (FILE,),
                            "save the plan of one day (DayPlan JSON: items with time, entry, project, done); replaces it",
                            ("labjournal today",), refresh=JOURNAL),
    "today": Cmd("labjournal.journal.days:today", (A("--date", type=iso_date, help="YYYY-MM-DD (default today)"),),
                         "the day: its plan, running experiments and their next step, entries of the day, flags, the week ahead"),
    "bank": Cmd("labjournal.journal.inplsi:bank", (),
                        "the cell bank: every frozen vial at its latest record, by box and position; stock per line and passage"),
    "page": Cmd("labjournal.journal.page:page", (), "rewrite the lab journal page (one HTML file) in place"),
}
