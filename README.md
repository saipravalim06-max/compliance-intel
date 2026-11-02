# Compliance Intelligence Platform

A unified regulatory and contract compliance platform that solves two interconnected compliance challenges:
1. **Macro Fit (State Startup Policy Advisor)**: Evaluates a startup's profile against **93 state policies** across Tamil Nadu and Karnataka to determine the best-fit state for incentives, subsidies, incubator access, and statutory eligibility.
2. **Micro Compliance (Contract Risk & Clashes)**: Screens third-party vendor contracts against internal corporate policies and statutory state regulations to catch liability, notice period, payment, and authorization conflicts.

| Module | Compares | Status |
|---|---|---|
| **1. State Fit Advisor** | Company Profile ⟷ State Startup Policies (TN vs KA) | ✅ Complete (93 rules, UI + Backend) |
| **2. Contract Checker** | Contract Clause ⟷ Company Internal Policies | ✅ Complete (UI + Backend + Test Suite) |
| **3. Contract vs State Law** | Contract Clause ⟷ Sourced State Statutory Candidates | ✅ Complete (UI + Backend) |
| **4. Drift Monitor** | Contract/Policy ⟷ Amended Regulations | ⏳ Roadmap |

---

## Quickstart: Launch the Web Application

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

### What You Can Do in the Web App
- **Tab 1: 🏛️ State Fit Advisor (Tamil Nadu vs Karnataka)**:
  - 1-click load real demo profiles (`AgriVision AI`, `Nirmaan Rural Foods`, `SteelForge Components`) or enter a custom startup profile.
  - Compares eligibility, confirmed grants/subsidies (e.g., TANSEED, Idea2PoC, SGST reimbursement), actionable registration steps, and missing facts questionnaire.
  - Interactive filterable explorer for all 93 state requirements with source PDF pages and official government URLs.
  - One-click CSV export of the state evaluation.
- **Tab 2: 📄 Contract vs Company Policies**:
  - 1-click load pre-built demo contract and policies or upload your own PDF, DOCX, or TXT documents.
  - Detects numeric mismatches, authorization omissions, and modality prohibitions.
  - Displays clause-by-clause evidence cards with rules triggered and similarity scores.
- **Tab 3: ⚖️ Contract vs State Regulations**:
  - Checks specific contract terms (notice periods, procurement criteria) against state statutory candidate rules in Tamil Nadu or Karnataka.

---

## Foundation & Datasets
- `data/state_policies/` — 93 canonical state requirements across Tamil Nadu and Karnataka with page numbers and official source URLs.
- `data/policy_corpus/` — 21 canonical company policies with quantifiable thresholds and unambiguous directional bounds.
- `data/profiles/` — Tri-state profiles (`True` / `False` / `None = UNKNOWN`), ensuring missing facts never trigger false rejections.
- `core/` — Unified schemas, taxonomy, mathematical quantity comparison, and deterministic conflict reasoning.

---

## Run Automated Tests & Evaluations

Run the 80 automated unit tests:
```bash
python -B -m pytest -p no:cacheprovider
```

Run Module 1 profile evaluation report:
```bash
python scripts/evaluate_profile.py --report results/profile_eval_report.md
```

Run Module 2 contract evaluation benchmark:
```bash
python scripts/evaluate.py --report results/eval_report.md
```
