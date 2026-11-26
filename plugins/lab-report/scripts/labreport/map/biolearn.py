"""biolearn adapter: every biolearn aging clock through one generic path.

A clock is a gallery model of a supported type whose output is measured in years ("Age (Years)",
"Aging Rate (Years/Year)"). `run` imputes missing CpGs once per imputation reference (each model's biolearn
default) and then evaluates every requested clock on the imputed sample, so a projection loads each
reference once instead of once per clock.

biolearn imports torch at module import, although only its deep models use it; when torch is not installed,
an inert stand-in is registered so the linear clocks load without the multi-hundred-MB dependency.
"""

from __future__ import annotations

import contextlib
import importlib.util
import re
import sys
import types
import warnings
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from labreport.errors import CLOCKS_EXTRA, DependencyMissing
from labreport.vocab import Sex

SUPPORTED_TYPES = frozenset({"LinearMethylationModel", "GrimageModel"})
_YEARS = re.compile(r"\(years(?:/year)?\)", re.I)
_REFERENCES = {"sesame_450k": ("sesame_450k_median.csv", "median"), "dunedin": ("DunedinPACE_Gold_Means.csv", "mean")}
_SEX = {Sex.F: 0, Sex.M: 1}


@contextlib.contextmanager
def _quiet() -> Iterator[None]:
    """biolearn prints and warns; stdout carries the CLI envelope."""
    with warnings.catch_warnings(), contextlib.redirect_stdout(sys.stderr):
        warnings.simplefilter("ignore")
        yield


def _torch_standin() -> None:
    if "torch" in sys.modules or importlib.util.find_spec("torch") is not None:
        return
    torch = types.ModuleType("torch")
    torch.Tensor = type("Tensor", (), {})  # type: ignore[attr-defined]
    nn = types.ModuleType("torch.nn")
    nn.Module = type("Module", (), {})  # type: ignore[attr-defined]
    nn.functional = types.ModuleType("torch.nn.functional")  # type: ignore[attr-defined]
    torch.nn = nn  # type: ignore[attr-defined]
    sys.modules.update({"torch": torch, "torch.nn": nn, "torch.nn.functional": nn.functional})  # type: ignore[attr-defined]


@lru_cache(maxsize=1)
def _gallery() -> Any:
    try:
        _torch_standin()
        with _quiet():
            from biolearn.model_gallery import ModelGallery

            return ModelGallery()
    except (ImportError, OSError) as exc:  # OSError: a broken numpy binary
        raise DependencyMissing(f"biolearn is not importable: {exc}", hint=CLOCKS_EXTRA) from None


def available() -> bool:
    try:
        _gallery()
        return True
    except DependencyMissing:
        return False


@lru_cache(maxsize=1)
def clocks() -> list[dict[str, Any]]:
    """[{name, year, tissue, output, unit, source, usage_note}] for every biolearn aging clock, sorted by name."""
    out = []
    for name, d in _gallery().model_definitions.items():
        output = str(d.get("output") or "")
        if d["model"]["type"] in SUPPORTED_TYPES and _YEARS.search(output):
            out.append({"name": name, "year": d.get("year"), "tissue": d.get("tissue"), "output": output,
                        "unit": "a/a" if "/year" in output.lower() else "a", "source": d.get("source"),
                        "usage_note": (d.get("usage") or {}).get("commercial")})
    return sorted(out, key=lambda c: c["name"].lower())


@lru_cache(maxsize=4)
def _reference(method: str) -> Any:
    import pandas as pd
    from biolearn.util import get_data_file

    file, column = _REFERENCES[method]
    return pd.read_csv(get_data_file(file), index_col=0)[column]


