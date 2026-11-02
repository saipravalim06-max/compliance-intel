"""
scripts/build_state_requirements.py

Reads the state workbooks (Sreeja's source of truth) and writes
data/state_policies/state_requirements_canonical.csv — every row converted to
the shared Requirement schema with taxonomy-mapped domain/type/operator and
numeric threshold_value + unit. GENERATED FILE: edit the workbooks, re-run this.

    python scripts/build_state_requirements.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import Requirement  # noqa: E402

SOURCES = [
    ("data/state_policies/tamil_nadu_state_fit.xlsx", "TN_Regulatory_Data"),
    ("data/state_policies/karnataka_state_fit.xlsx", "KA_Regulatory_Data"),
]

rows = []
for path, sheet in SOURCES:
    df = pd.read_excel(path, sheet_name=sheet)
    for rec in df.to_dict("records"):
        r = Requirement.from_state_row(rec)
        d = r.model_dump() if hasattr(r, "model_dump") else r.dict()
        d["source_type"] = getattr(d["source_type"], "value", d["source_type"])
        rows.append(d)

out = pd.DataFrame(rows)
out.to_csv("data/state_policies/state_requirements_canonical.csv", index=False)
print(f"{len(out)} requirements -> data/state_policies/state_requirements_canonical.csv")
print(out.groupby("jurisdiction").size().to_string())
print("\nrequirements with a numeric threshold:", int(out.threshold_value.notna().sum()))
print("operator blank:", int(out.operator.isna().sum()), "| effective_from blank:", int(out.effective_from.isna().sum()))
print("\ndomains:", out.domain.value_counts().to_dict())
