"""
Compliance Intelligence Platform - Streamlit Application
A unified compliance and regulatory analysis platform:
1. State Fit Advisor (Tamil Nadu vs Karnataka for Startups)
2. Contract vs Internal Company Policy Checker
3. Contract vs State Statutory Regulations Audit Center
"""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pandas as pd
import streamlit as st

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.company_profile import CompanyProfile, Industry
from core.engine import ingest_document
from core.matching import PolicyMatcher
from core.profile_eval import load_state_requirements
from modules.contract_checker import (
    check_clause_against_state_requirements,
    check_contract_document_against_state_requirements,
    get_statutory_redline_advice,
)
from modules.state_fit import compare_states, rank_states
from modules.upload_checker import compare_uploaded_documents


st.set_page_config(
    page_title="Compliance Intelligence Platform",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Header & Global Styling
# ---------------------------------------------------------------------------
st.title("Compliance Intelligence Platform")
st.caption(
    "Automated Regulatory & Contract Compliance · State Startup Policy Advisor (TN vs KA) · Contract Risk Screening"
)

# Sidebar: Global Engine Settings
with st.sidebar:
    st.header("Engine Configuration")

    backend = st.selectbox(
        "Matching Backend",
        options=["hashing", "sentence-transformers"],
        index=0,
        help=(
            "Hashing works deterministically offline without downloading models. "
            "Sentence-transformers provides dense semantic embeddings if weights are cached."
        ),
    )

    similarity_threshold = st.slider(
        "Semantic Relevance Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.25 if backend == "hashing" else 0.35,
        step=0.05,
        help="Embeddings retrieve candidate requirements; structured rules determine conflict.",
    )

    top_k = st.number_input(
        "Candidate Matches per Clause",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )

    st.divider()
    st.markdown(
        """
        **About this System:**
        - **Macro Fit**: Evaluates startup profile against **93 state policies** across Tamil Nadu & Karnataka.
        - **Micro Compliance**: Compares vendor contracts against internal corporate policies & statutory laws.
        - **State Statutory Audit**: Screens contracts against MSMED Act (45-day payment cap), Indian Contract Act (Sec 27 non-compete voidness), Stamp Acts, and State Startup Policies.
        - **Deterministic Reasoning**: Numeric, modal, and authorization checks are mathematically evaluated—not hallucinated.
        """
    )

# ---------------------------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------------------------
tab_state, tab_contract, tab_state_contract = st.tabs([
    "State Fit Advisor (TN vs KA)",
    "Contract vs Company Policies",
    "Contract vs State Regulations Audit",
])


# ===========================================================================
# TAB 1: State Fit Advisor (Tamil Nadu vs Karnataka)
# ===========================================================================
with tab_state:
    st.subheader("Startup State Fit & Regulatory Policy Advisor")
    st.markdown(
        """
        Evaluate where a startup should establish its business to maximize government grants,
        tax reimbursements, and incubator perks between **Tamil Nadu** and **Karnataka**,
        while identifying mandatory incorporation and registration steps.
        """
    )

    col_demo, col_blank = st.columns([2, 3])
    with col_demo:
        demo_profiles = {
            "Select or Load a Demo Profile...": None,
            "AgriVision AI Pvt Ltd (Agritech, 3 yrs, ₹4 Cr turnover, Women-led, Patent)": "data/profiles/agrivision_ai.json",
            "Nirmaan Rural Foods LLP (Food Processing, 2 yrs, ₹1.2 Cr, Rural, SC/ST, LLP)": "data/profiles/nirmaan_rural_foods.json",
            "Kaveri Circular Tech Pvt Ltd (Circular Economy, Mysuru, 2 yrs, ₹0.8 Cr, Women-led, Patent)": "data/profiles/kaveri_circular_tech.json",
            "SteelForge Components Ltd (Auto Parts, 12 yrs, ₹120 Cr - Ineligible Startup)": "data/profiles/steelforge_components.json",
        }
        selected_demo_name = st.selectbox(
            "Quick Demo Profile:",
            options=list(demo_profiles.keys()),
            index=0,  # start on the placeholder: nothing is loaded or analysed until the user chooses
        )

    # Load the demo profile exactly as stored: unknown facts stay None (= UNKNOWN), never False.
    loaded_profile_data = {}
    base_profile = None
    if selected_demo_name and demo_profiles[selected_demo_name]:
        demo_path = ROOT_DIR / demo_profiles[selected_demo_name]
        if demo_path.is_file():
            loaded_profile_data = json.loads(demo_path.read_text(encoding="utf-8"))
            base_profile = CompanyProfile.from_dict(loaded_profile_data)

    # A profile the user saved earlier (JSON) takes precedence over the demo dropdown
    uploaded_profile = st.file_uploader(
        "Or load a profile you saved earlier (JSON)", type=["json"], key="profile_upload",
        help="Use the 'Download my profile' button below to save one. The demo dropdown stays available.",
    )
    wkey = (selected_demo_name or "custom")[:12]  # widget keys change with the demo, so the form resets cleanly
    if uploaded_profile is not None:
        try:
            _d = json.loads(uploaded_profile.getvalue().decode("utf-8"))
            _p = CompanyProfile.from_dict(_d)
            loaded_profile_data, base_profile = _d, _p
            import hashlib
            wkey = "up" + hashlib.md5(f"{uploaded_profile.name}{uploaded_profile.size}".encode()).hexdigest()[:8]
            st.success(f"Loaded saved profile: {_d.get('company_name', uploaded_profile.name)}")
        except Exception as exc:
            st.error(f"Could not read that profile file: {exc}. Using the selected demo profile instead.")
    TRI = ["Unknown", "Yes", "No"]

    from typing import get_args, get_type_hints
    _HINTS = get_type_hints(CompanyProfile)
    FORM_FACTS = {"has_patent", "has_innovation", "is_women_led", "has_rural_impact", "is_sc_st_led",
                  "located_beyond_bengaluru_urban", "is_manufacturing"}

    def _base_type(fact):
        if fact == "elevate_programme_recognised":
            return bool
        h = _HINTS.get(fact)
        args = [a for a in get_args(h) if a is not type(None)]
        t = args[0] if args else h
        return list if getattr(t, "__origin__", None) is list else t

    def _pretty(fact):
        return (fact.replace("_", " ").replace(" inr", " (INR)").replace(" pct", " (%)").capitalize()
                .replace("bengaluru", "Bengaluru").replace("govt", "government").replace(" years", " (years)"))

    def _parse_followup(fact, v):
        t = _base_type(fact)
        if v in (None, "", "Unknown"):
            return None
        if t is bool:
            return v == "Yes"
        if t in (int, float):
            try:
                return t(float(str(v).replace(",", "")))
            except ValueError:
                return None
        if t is list:
            return [x.strip() for x in str(v).split(",") if x.strip()] or None
        return v

    def _fact_input(fact, label, key):
        t = _base_type(fact)
        if t is bool:
            st.selectbox(label, TRI, key=key)
        elif fact == "patent_stage":
            st.selectbox(label, ["Unknown", "filed", "granted"], key=key)
        elif t in (int, float):
            st.text_input(label, placeholder="number, blank = unknown", key=key)
        elif t is list:
            st.text_input(label, placeholder="comma separated, blank = unknown", key=key)
        else:
            st.text_input(label, placeholder="blank = unknown", key=key)

    def tri(label, fact, help=None):
        v = loaded_profile_data.get(fact)
        ans = st.selectbox(label, TRI, index=0 if v is None else (1 if v else 2), key=f"{wkey}_{fact}", help=help)
        return None if ans == "Unknown" else ans == "Yes"

    # Interactive Profile Form
    with st.expander("Company Profile Details & Attributes", expanded=True):
        st.caption("Choose Unknown when a fact is not known: it is reported as missing information, never counted as a failure.")
        fcol1, fcol2, fcol3 = st.columns(3)

        with fcol1:
            company_name = st.text_input(
                "Company Name",
                value=loaded_profile_data.get("company_name", "My Startup Inc"),
                key=f"{wkey}_name",
            )
            industry_val = loaded_profile_data.get("industry", "software_saas")
            industry_list = [i.value for i in Industry]
            industry_idx = industry_list.index(industry_val) if industry_val in industry_list else 0
            industry = st.selectbox("Industry / Domain", options=industry_list, index=industry_idx, key=f"{wkey}_industry")
            legal_options = ["Private Limited", "LLP", "Partnership", "Sole Proprietorship", "Public Limited"]
            legal_val = loaded_profile_data.get("legal_form")
            if legal_val and legal_val not in legal_options:
                legal_options = legal_options + [legal_val]
            legal_form = st.selectbox(
                "Legal Entity Form",
                options=legal_options,
                index=legal_options.index(legal_val) if legal_val in legal_options else 0,
                key=f"{wkey}_legal",
            )
            age_years = st.number_input(
                "Startup Age (Years since incorporation)",
                min_value=0.0,
                max_value=100.0,
                value=float(loaded_profile_data.get("age_years") or 3),
                step=0.5,
                key=f"{wkey}_age",
            )

        with fcol2:
            turnover_inr = st.number_input(
                "Annual Turnover (INR)",
                min_value=0.0,
                max_value=100_000_000_000.0,
                value=float(loaded_profile_data.get("annual_turnover_inr") or 40_000_000.0),
                step=1_000_000.0,
                help="Absolute rupees. E.g. 4 Crore = 40,000,000 INR",
                key=f"{wkey}_turnover",
            )
            employee_count = st.number_input(
                "Employee Count",
                min_value=1,
                max_value=100000,
                value=int(loaded_profile_data.get("employee_count") or 25),
                step=1,
                key=f"{wkey}_emp",
            )
            has_patent = tri("Holds or Filed Patent", "has_patent")
            has_innovation = tri("Innovative / Novel Business Model", "has_innovation")

        with fcol3:
            st.markdown("**Diversity & Regional Factors**")
            is_women_led = tri("Women-Led (Founder / Majority owned)", "is_women_led")
            has_rural_impact = tri("Rural / Social Impact Focus", "has_rural_impact")
            is_sc_st_led = tri("SC / ST / Minority Leadership", "is_sc_st_led")
            located_beyond_bengaluru = tri("Located Beyond Bengaluru Urban (KA rural perks)", "located_beyond_bengaluru_urban")
            is_manufacturing = tri("Physical Manufacturing Component", "is_manufacturing")

    # ---- Full questionnaire: every other fact the state rules use. Defaults to Unknown. ----
    QUESTIONS = [
        ("Ownership & leadership", [
            ("is_trans_or_differently_abled_led", "Led by a transgender or differently-abled founder"),
            ("is_obc_or_minority_led", "OBC or minority-led"),
            ("women_ownership_pct", "Women's ownership (%)"),
            ("women_employment_pct", "Women in the workforce (%)"),
            ("has_women_night_shift_operations", "Women employed on night shifts")]),
        ("Stage & business model", [
            ("is_early_stage", "Idea / proof-of-concept stage"),
            ("is_growth_stage", "Growth stage"),
            ("has_scalable_model", "Scalable business model"),
            ("is_msme", "Registered as an MSME"),
            ("formed_by_split_or_reconstruction", "Formed by splitting or reconstructing an existing business"),
            ("is_green_tech", "Green / clean technology"),
            ("has_circular_economy_focus", "Circular-economy focus")]),
        ("IP & innovation", [
            ("patent_stage", "Patent stage"),
            ("has_foreign_patent", "Holds a foreign patent"),
            ("has_trademark", "Holds a trademark"),
            ("technology_areas", "Technology areas"),
            ("impact_areas", "Impact areas")]),
        ("Incubation & recognition", [
            ("incubated_in_govt_supported_incubator", "Incubated in a government-supported incubator"),
            ("incubation_age_years", "Years since entering the incubator"),
            ("startup_recognition_age_years", "Years since state startup recognition"),
            ("grand_challenge_winner", "Grand Challenge winner"),
            ("is_sandbox_operator", "Regulatory sandbox operator"),
            ("is_sandbox_participant", "Regulatory sandbox participant"),
            ("elevate_programme_recognised", "Recognised under Karnataka Elevate")]),
        ("Hiring & location", [
            ("hires_interns_from_beyond_bengaluru", "Hires interns from beyond Bengaluru"),
            ("intern_duration_months", "Internship duration (months)"),
            ("has_availed_rural_internship_subsidy", "Already availed the rural internship subsidy")]),
        ("Certifications & marketing", [
            ("quality_certification_count", "Number of quality certifications"),
            ("quality_certification_spend_inr", "Spend on quality certifications (INR)"),
            ("intl_marketing_spend_inr", "International marketing spend (INR)")]),
    ]
    QFACTS = [f for _, items in QUESTIONS for f, _ in items]

    def _default_raw(fact):
        if fact == "elevate_programme_recognised":
            v = ((loaded_profile_data.get("state_context") or {}).get("Karnataka") or {}).get(fact)
        else:
            v = loaded_profile_data.get(fact)
        t = _base_type(fact)
        if v is None:
            return "Unknown" if (t is bool or fact == "patent_stage") else ""
        if t is bool:
            return "Yes" if v else "No"
        if t is list:
            return ", ".join(v) if isinstance(v, list) else str(v)
        if t in (int, float):
            return str(int(v)) if float(v).is_integer() else str(v)
        return str(v)

    _qdef = st.session_state.setdefault("_q_defaults", {})
    for _f in QFACTS:
        _k = f"{wkey}_q_{_f}"
        if _k not in st.session_state:
            st.session_state[_k] = _default_raw(_f)
            _qdef[_k] = st.session_state[_k]
    _answered = sum(1 for _f in QFACTS if st.session_state.get(f"{wkey}_q_{_f}") not in ("", "Unknown", None))

    with st.expander(f"More facts about your company : {_answered} of {len(QFACTS)} answered", expanded=False):
        st.caption("Every rule is judged only on facts you give. Anything left on Unknown is reported as missing "
                   "information, never as a failure. The more you answer, the fewer rules stay undecided.")
        for _title, _items in QUESTIONS:
            st.markdown(f"**{_title}**")
            _cols = st.columns(3)
            for _i, (_f, _label) in enumerate(_items):
                with _cols[_i % 3]:
                    _fact_input(_f, _label, f"{wkey}_q_{_f}")

    btn_analyze_state = st.button("Analyze State Fit (TN vs KA)", type="primary", use_container_width=True)

    # Analyse only after the user clicks the button. The flag is remembered for this profile, so editing answers
    # afterwards re-evaluates live; switching to another profile hides the results until Analyze is clicked again.
    if btn_analyze_state:
        st.session_state["state_fit_ran_for"] = wkey
    if st.session_state.get("state_fit_ran_for") != wkey:
        st.caption("Pick a demo profile, load a saved one, or enter your company above, then click **Analyze State Fit**.")
    if st.session_state.get("state_fit_ran_for") == wkey:
        # Pre-load state requirements metadata lookup
        all_state_reqs = load_state_requirements()
        req_meta = {r["requirement_id"]: r for r in all_state_reqs}

        # Start from the stored profile (keeps every other fact and its UNKNOWN status), then apply the form values
        import copy
        profile = copy.deepcopy(base_profile) if base_profile else CompanyProfile(company_name=company_name)
        profile.company_name = company_name
        profile.industry = Industry(industry) if industry in [i.value for i in Industry] else Industry.OTHER
        profile.legal_form = legal_form
        profile.age_years = age_years
        profile.annual_turnover_inr = turnover_inr
        profile.employee_count = employee_count
        profile.has_patent = has_patent
        profile.has_innovation = has_innovation
        profile.has_rural_impact = has_rural_impact
        profile.is_sc_st_led = is_sc_st_led
        profile.located_beyond_bengaluru_urban = located_beyond_bengaluru
        profile.is_manufacturing = is_manufacturing
        if base_profile is None or is_women_led != base_profile.is_women_led:
            profile.is_women_led = is_women_led
            # Yes keeps any stored ownership figure; it is never assumed. It can be given in the questionnaire.
            profile.women_ownership_pct = 0.0 if is_women_led is False else (profile.women_ownership_pct if is_women_led else None)

        # Answers from the questionnaire (only the ones changed from their starting value)
        for _f in QFACTS:
            _k = f"{wkey}_q_{_f}"
            if _k in st.session_state and st.session_state[_k] != _qdef.get(_k):
                _val = _parse_followup(_f, st.session_state[_k])
                if _f == "elevate_programme_recognised":
                    _ctx = dict(profile.state_context.get("Karnataka") or {})
                    _ctx[_f] = _val
                    profile.state_context = {**profile.state_context, "Karnataka": _ctx}
                else:
                    setattr(profile, _f, _val)

        st.download_button(
            "Download my profile (JSON)",
            data=json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
            file_name=f"{(company_name or 'profile').lower().replace(' ', '_')}_profile.json",
            mime="application/json",
            help="Save this profile and load it again later, without re-entering the facts.",
        )

        with st.spinner("Evaluating profile against 93 state requirements and statutory rules..."):
            results = compare_states(profile, states=["Tamil Nadu", "Karnataka"], if_registered=True)
            ranked = rank_states(results)

        st.divider()

        # Reading-aid banner (not a score)
        best_state = ranked[0]["state"]
        best_summary = ranked[0]["summary"]
        second_state = ranked[1]["state"]
        second_summary = ranked[1]["summary"]

        if best_summary["eligible_as_startup"]:
            st.success(
                f"### Stronger match on the facts provided: **{best_state}**\n"
                f"{best_state}: **{best_summary['benefits_confirmed']}** confirmed benefits, **{best_summary['benefits_potential']}** potential, "
                f"**{len(best_summary['needs_information'])}** rules need more information.  \n"
                f"{second_state}: **{second_summary['benefits_confirmed']}** confirmed, **{second_summary['benefits_potential']}** potential, "
                f"**{len(second_summary['needs_information'])}** rules need more information.  \n"
                "This is a reading aid, not a score. Answer the questions below to improve it."
            )
        else:
            st.error(
                f"### Not eligible as a startup in the state(s) checked\n"
                f"Disqualifications: {', '.join(best_summary['eligibility_failures'] or second_summary['eligibility_failures'])}"
            )

        # ---- Hint: which unanswered questions would settle the most rules (read-only; answers go in the form / questionnaire) ----
        need = {}
        for res_ in results:
            for item in res_["summary"]["facts_to_provide"]:
                need[item["fact"]] = need.get(item["fact"], 0) + item["would_help"]
        total_unknown = sum(len(r_["summary"]["needs_information"]) for r_ in results)
        total_potential = sum(r_["summary"]["benefits_potential"] for r_ in results)
        if need and (total_unknown or total_potential):
            top = sorted(need.items(), key=lambda kv: -kv[1])[:6]
            lines = []
            for f_, n_ in top:
                internal = f_[6:] if f_.startswith("state.") else f_
                where = "profile form" if f_ in FORM_FACTS else "questionnaire"
                lines.append(f"- {_pretty(internal)}: settles {n_} rule{'s' if n_ != 1 else ''} ({where})")
            st.info(
                f"**{total_unknown} rules are undecided and {total_potential} potential benefits could be confirmed.** "
                "Answering these would help most. Use the profile form above or **More facts about your company**:\n"
                + "\n".join(lines)
            )

        # Side-by-Side Comparison
        col_tn, col_ka = st.columns(2)

        for col, res in zip([col_tn, col_ka], results):
            state_name = res["state"]
            summary = res["summary"]
            counts = summary["counts"]

            with col:
                st.subheader(f"{'' if state_name == 'Tamil Nadu' else ''} {state_name}")

                # Metric Cards
                m1, m2, m3 = st.columns(3)
                m1.metric("Confirmed Benefits", summary["benefits_confirmed"])
                m2.metric("Potential Grants", summary["benefits_potential"])
                m3.metric("Policy Allocations", counts.get("APPLIES", 0))

                # Eligibility Box
                if summary["eligible_as_startup"]:
                    st.success("**Eligible as a Recognized Startup**")
                else:
                    st.error(f"**Not Eligible as Startup:** {', '.join(summary['eligibility_failures'])}")

                # Actions Required
                if summary["actions_required"]:
                    st.info(f" **Mandatory Steps to Qualify:** {', '.join(summary['actions_required'])}")
                else:
                    st.caption("No pending registration steps required.")

                # Top Confirmed Subsidies / Incentives
                st.markdown("#####  Top Applicable Subsidies & Benefits")
                confirmed_checks = [c for c in res["checks"] if c.verdict in ("PASS", "APPLIES")]
                if confirmed_checks:
                    for c in confirmed_checks[:5]:
                        meta = req_meta.get(c.requirement_id, {})
                        req_name = meta.get("requirement_name") or c.requirement_id
                        benefit_txt = meta.get("benefit") or (c.evidence_text or "")[:120]
                        st.markdown(f"- **{req_name}** (`{c.requirement_id}`): {benefit_txt}")
                else:
                    st.caption("No confirmed direct benefits found for current profile.")

                # Missing Facts Checklist
                if summary["needs_information"]:
                    with st.expander(f" Missing Information Questionnaire ({len(summary['needs_information'])} items)"):
                        st.caption("Supplying these facts could unlock additional grants:")
                        for fact in summary["needs_information"]:
                            st.markdown(f"- `{fact}`")

        # Full Detailed Requirement Explorer
        st.divider()
        st.subheader("Explore All 93 State Regulatory Provisions")
        st.caption("Grounded in official state policy workbooks with source PDF pages and official government URLs.")

        # Flatten checks for table display
        all_table_data = []
        for res in results:
            for c in res["checks"]:
                meta = req_meta.get(c.requirement_id, {})
                req_name = meta.get("requirement_name") or c.requirement_id
                domain = meta.get("domain", "General")
                verdict_str = c.verdict.value if hasattr(c.verdict, "value") else str(c.verdict)
                all_table_data.append({
                    "State": res["state"],
                    "ID": c.requirement_id,
                    "Name": req_name,
                    "Domain": domain,
                    "Verdict": verdict_str,
                    "Evidence": c.evidence_text,
                    "Reasoning": c.reasoning,
                    "Page": str(c.page_number) if c.page_number else "N/A",
                    "Source URL": c.source_url or "",
                })

        df_state = pd.DataFrame(all_table_data)

        # Filters
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            selected_state_filter = st.multiselect(
                "Filter by State:",
                options=["Tamil Nadu", "Karnataka"],
                default=["Tamil Nadu", "Karnataka"],
            )
        with fcol2:
            verdict_options = sorted(list(df_state["Verdict"].unique()))
            selected_verdicts = st.multiselect("Filter by Verdict:", options=verdict_options, default=verdict_options)

        filtered_df = df_state[
            (df_state["State"].isin(selected_state_filter)) & (df_state["Verdict"].isin(selected_verdicts))
        ]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # Export CSV
        csv_state = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Download State Fit Analysis (CSV)",
            data=csv_state,
            file_name=f"{company_name.lower().replace(' ', '_')}_state_fit_report.csv",
            mime="text/csv",
        )


# ===========================================================================
# TAB 2: Contract vs Company Policies
# ===========================================================================
with tab_contract:
    st.subheader(" Vendor Contract vs Internal Company Policies")
    st.markdown(
        """
        Screen third-party vendor contracts against internal corporate policies.
        Identifies contradictions in notice periods, liability caps, warranties, payment terms, and authorization.
        """
    )

    col_btn_load, col_info = st.columns([2, 3])
    with col_btn_load:
        demo_choice = st.selectbox(
            "Load Pre-built Demo Documents:",
            [
                "None (Upload My Own Below)",
                "Northwind Policy vs Helix MSA (14 Policies · 19 Clauses)",
                "Standard Multi-Clause Baseline (4 Clauses)",
            ],
            index=1,
            key="demo_contract_choice",
        )

    c_file_col, p_file_col = st.columns(2)
    with c_file_col:
        contract_file = st.file_uploader(
            "Upload Vendor Contract Document",
            type=["pdf", "docx", "txt"],
            key="custom_contract",
            help="Upload one vendor agreement.",
        )
    with p_file_col:
        policy_files = st.file_uploader(
            "Upload Company Internal Policies",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="custom_policies",
            help="Upload one or more company policy documents.",
        )

    # Determine files to process
    has_demo = demo_choice != "None (Upload My Own Below)"
    if has_demo and not contract_file:
        st.info(f"Demo mode active: `{demo_choice}`. Click below to run.")

    run_contract_check = st.button(
        "⚡ Run Contract Compliance Check",
        type="primary",
        disabled=(not contract_file or not policy_files) and not has_demo,
        use_container_width=True,
    )

    if run_contract_check:
        try:
            with st.spinner("Extracting clauses and evaluating conflicts..."):
                with TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    if contract_file and policy_files:
                        contract_path = temp_path / Path(contract_file.name).name
                        contract_path.write_bytes(contract_file.getvalue())

                        policy_paths = []
                        for index, up in enumerate(policy_files):
                            safe_name = Path(up.name).name
                            saved_path = temp_path / f"policy_{index}_{safe_name}"
                            saved_path.write_bytes(up.getvalue())
                            policy_paths.append(str(saved_path))
                    elif "Northwind" in demo_choice:
                        contract_path = ROOT_DIR / "results" / "complex_tests" / "helix_master_services_agreement.txt"
                        policy_paths = [str(ROOT_DIR / "results" / "complex_tests" / "northwind_vendor_policy.txt")]
                    else:
                        contract_path = ROOT_DIR / "results" / "complex_tests" / "multi_contract.txt"
                        policy_paths = [str(ROOT_DIR / "results" / "complex_tests" / "multi_policy.txt")]

                    report = compare_uploaded_documents(
                        contract_path=str(contract_path),
                        policy_paths=policy_paths,
                        backend=backend,
                        similarity_threshold=similarity_threshold,
                        top_k=int(top_k),
                    )

            st.session_state["compliance_report"] = report

        except Exception as exc:
            st.error("The compliance check could not be completed.")
            st.exception(exc)

    report = st.session_state.get("compliance_report")
    if report:
        st.divider()
        st.subheader("Screening Findings & Evidence")
        st.caption(
            f"Contract: {report['contract_file']} · "
            f"Policies: {', '.join(report['policy_files'])}"
        )

        findings = report["findings"]
        conflicts = sum(f["label"] == "CONFLICT" for f in findings)
        partial = sum(f["label"] == "PARTIAL_CONFLICT" for f in findings)
        compatible = sum(f["label"] == "NO_CONFLICT" for f in findings)
        unmatched = sum(f["label"] == "NO_MATCH_FOUND" for f in findings)
        uncertain = sum(f["label"] == "UNCERTAIN" for f in findings)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Contract Clauses", report["contract_clause_count"])
        m2.metric("Conflicts Detected", conflicts, delta=f"{conflicts} clashing" if conflicts else "Clean", delta_color="inverse")
        m3.metric("Compatible / Satisfied", compatible)
        m4.metric("Uncertain", uncertain)
        m5.metric("Unmatched (Admin)", unmatched)

        if findings:
            filter_choice = st.radio(
                "Filter View:",
                [
                    f"All Clauses ({len(findings)})",
                    f"🚨 Conflicts Only ({conflicts + partial})",
                    f"✅ Compatible Only ({compatible})",
                    f"ℹ️ Unmatched Admin ({unmatched + uncertain})",
                ],
                horizontal=True,
                key="filter_findings_view",
            )

            filtered_findings = findings
            if "Conflicts Only" in filter_choice:
                filtered_findings = [f for f in findings if f["label"] in ("CONFLICT", "PARTIAL_CONFLICT")]
            elif "Compatible Only" in filter_choice:
                filtered_findings = [f for f in findings if f["label"] == "NO_CONFLICT"]
            elif "Unmatched Admin" in filter_choice:
                filtered_findings = [f for f in findings if f["label"] in ("NO_MATCH_FOUND", "UNCERTAIN")]

            table_rows = []
            for finding in filtered_findings:
                table_rows.append({
                    "Clause": finding["clause_number"],
                    "Result": finding["label"],
                    "Severity": finding.get("severity", "NONE"),
                    "Policy source": finding.get("policy_source") or "Not matched",
                    "Similarity": finding.get("similarity_score"),
                    "Explanation": finding.get("reason", ""),
                })

            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            csv_findings = pd.DataFrame(table_rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 Download Findings (CSV)",
                data=csv_findings,
                file_name="contract_policy_findings.csv",
                mime="text/csv",
            )

            st.markdown("##### Clause-by-Clause Evidence Breakdown")
            for index, finding in enumerate(filtered_findings, start=1):
                label = finding["label"]
                source = finding.get("policy_source") or "No policy matched"
                badge = (
                    "🚨" if label == "CONFLICT"
                    else ("⚠️" if label == "PARTIAL_CONFLICT"
                          else ("✅" if label == "NO_CONFLICT"
                                else ("ℹ️" if label == "NO_MATCH_FOUND" else "❓")))
                )

                with st.expander(f"{badge} Clause {finding['clause_number']} · {label} · {source}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Contract Clause Text:**")
                        st.info(finding["contract_clause"])
                    with c2:
                        st.markdown("**Matched Policy Requirement:**")
                        st.info(finding.get("policy_requirement") or "No direct policy requirement matched.")

                    st.markdown(f"**Explanation:** {finding.get('reason', '')}")
                    if finding.get("rules"):
                        st.caption(f"Triggered Rules: `{', '.join(finding['rules'])}`")


# ===========================================================================
# TAB 3: Contract vs State Statutory Regulations Audit Center
# ===========================================================================
with tab_state_contract:
    st.subheader(" Contract vs State Statutory Regulations Audit Center")
    st.markdown(
        """
        Audit vendor contracts against statutory business laws and state regulations in **Tamil Nadu** and **Karnataka**:
        - **MSMED Act 2006 (Section 15)**: Mandatory statutory payment cap of maximum 45 days.
        - **Indian Contract Act 1872 (Section 27)**: Restraint of trade / post-termination non-compete voidness.
        - **Commercial Notice Standards**: Minimum 30 days notice for convenience termination.
        - **State Startup Procurement Mandates**: Exemptions from prior turnover/experience and EMD waivers.
        - **State Stamp Acts (TN & KA)**: Statutory stamp duty formalities for court admissibility.
        - **CERT-In Directions & DPDP Framework**: Mandatory 6-hour cybersecurity incident reporting.
        """
    )

    jurisdiction = st.selectbox("Target Jurisdiction:", ["Tamil Nadu", "Karnataka"], key="state_audit_jurisdiction")

    audit_mode = st.radio(
        "Audit Mode:",
        options=[" Full Contract Document Audit", "Single Clause Quick Check"],
        horizontal=True,
    )

    if audit_mode == " Full Contract Document Audit":
        col_demo_audit, col_space = st.columns([2, 3])
        with col_demo_audit:
            if st.button(" Load Pre-built Commercial Contract (Sample)", use_container_width=True):
                st.session_state["use_demo_state_contract"] = True

        state_contract_file = st.file_uploader(
            "Upload Contract to Audit against State Regulations:",
            type=["pdf", "docx", "txt"],
            key="state_audit_file",
            help="Upload vendor contract, NDA, SLA, or commercial agreement.",
        )

        use_state_demo = st.session_state.get("use_demo_state_contract", False)
        if use_state_demo and not state_contract_file:
            st.info("Demo contract loaded: `sample_vendor_contract_state_audit.txt` (6 commercial clauses)")

        run_state_audit = st.button(
            " Run Full State Regulatory Audit",
            type="primary",
            disabled=not state_contract_file and not use_state_demo,
            use_container_width=True,
        )

        if run_state_audit:
            with st.spinner(f"Screening contract against {jurisdiction} statutory regulations and acts..."):
                try:
                    if state_contract_file:
                        with TemporaryDirectory() as tmp_dir:
                            tmp_file = Path(tmp_dir) / state_contract_file.name
                            tmp_file.write_bytes(state_contract_file.getvalue())
                            contract_text = ingest_document(str(tmp_file))
                    else:
                        demo_file = ROOT_DIR / "results" / "complex_tests" / "sample_vendor_contract_state_audit.txt"
                        contract_text = ingest_document(str(demo_file))

                    audit_results = check_contract_document_against_state_requirements(
                        contract_text=contract_text,
                        jurisdiction=jurisdiction,
                    )
                    st.session_state["state_audit_results"] = audit_results

                except Exception as exc:
                    st.error("State regulatory audit encountered an error.")
                    st.exception(exc)

        audit_data = st.session_state.get("state_audit_results")
        if audit_data:
            st.divider()
            st.subheader(f"State Statutory Audit Report — {audit_data['jurisdiction']}")

            c_count = audit_data["conflict_count"]
            p_count = audit_data["partial_count"]
            comp_count = audit_data["compatible_count"]
            findings = audit_data["findings"]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Clauses Analyzed", audit_data["clause_count"])
            m2.metric("Statutory Clashes", c_count, delta=f"{c_count} violations" if c_count else "Zero Clashes", delta_color="inverse")
            m3.metric("Statutory Advisories", len(findings) - c_count - comp_count)
            m4.metric("Compliances / Exemptions", comp_count)

            if c_count > 0:
                st.error(
                    f"**{c_count} statutory clash(es) detected** against mandatory state and central acts in {jurisdiction}. "
                    "Review the redline drafting amendments below before executing this contract."
                )
            else:
                st.success(" No direct statutory violations detected against core state regulations.")

            # Summary Table
            table_records = []
            for f in findings:
                table_records.append({
                    "Clause": f["clause_number"],
                    "Status": f["label"],
                    "Statutory Act / Policy": f.get("policy_name") or f.get("requirement_id"),
                    "Section / Page": f.get("page_number") or "N/A",
                    "Similarity": f.get("similarity_score"),
                    "Legal Explanation": f.get("reason", ""),
                    "Recommended Redline": f.get("redline_advice", ""),
                })

            st.dataframe(pd.DataFrame(table_records), use_container_width=True, hide_index=True)

            csv_audit = pd.DataFrame(table_records).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Download State Regulatory Audit Report (CSV)",
                data=csv_audit,
                file_name=f"state_regulatory_audit_{jurisdiction.lower().replace(' ', '_')}.csv",
                mime="text/csv",
            )

            st.markdown("#####  Clause-by-Clause Statutory Findings & Actionable Redlines")
            for idx, f in enumerate(findings, start=1):
                label = f["label"]
                badge = "" if label == "CONFLICT" else ("" if label in ("PARTIAL_CONFLICT", "UNCERTAIN") else "")
                title = f"{badge} Clause {f['clause_number']} · {f.get('requirement_id')} — {f.get('policy_name') or 'Statutory Provision'}"

                with st.expander(title, expanded=(label == "CONFLICT")):
                    col_c, col_s = st.columns(2)
                    with col_c:
                        st.markdown("**Contract Clause Text:**")
                        st.info(f["contract_clause"])
                    with col_s:
                        st.markdown("**Statutory Evidence & Mandate:**")
                        st.info(f.get("state_requirement_text", ""))

                    st.markdown(f"**Legal Explanation:** {f.get('reason', '')}")

                    # Redline advice box
                    if f.get("redline_advice"):
                        st.success(f" **Drafting Guidance & Redline Fix:**\n\n{f['redline_advice']}")

                    if f.get("source_url"):
                        st.markdown(f" [Official Act / Gazette Source Document]({f['source_url']}) (Section / Page: `{f.get('page_number')}`)")

    else:
        # Single Clause Quick Check Mode
        st.markdown("##### Test an Individual Contract Clause")
        sample_clauses = {
            "Custom Clause": "",
            "Payment: 90 days credit period (Violates MSMED Act Sec 15)": "The customer shall pay all undisputed vendor invoices within 90 days of receipt.",
            "Termination: 7 days notice for convenience (Clashes with 30-day standard)": "Either party may terminate this agreement for convenience upon 7 days written notice.",
            "Non-Compete: 2-year post-termination restraint (Void under Sec 27 Contract Act)": "The vendor agrees not to engage in or provide competing services in the state for 2 years following termination.",
            "Data Breach: 30-day notification timeline (Violates 6-hr CERT-In timeline)": "The supplier shall notify customer data security incidents and breaches within 30 days of discovery.",
            "Procurement: Tender requiring 50 Cr turnover from startup (Exempt under State Startup Policy)": "The vendor must possess an annual turnover exceeding 50 crore INR in each of the last three years to qualify.",
        }

        selected_sample = st.selectbox("Load Pre-set Scenario:", list(sample_clauses.keys()))
        default_text = sample_clauses[selected_sample] if selected_sample != "Custom Clause" else ""

        test_clause = st.text_area(
            "Contract Clause to Check:",
            value=default_text or "The customer shall pay all undisputed vendor invoices within 90 days of receipt.",
            height=100,
        )

        if st.button(" Screen Clause Against State Law", type="primary"):
            with st.spinner(f"Matching against {jurisdiction} statutory records..."):
                try:
                    state_matches = check_clause_against_state_requirements(
                        contract_text=test_clause,
                        jurisdiction=jurisdiction,
                        top_k=int(top_k),
                    )

                    if state_matches:
                        st.success(f"Retrieved {len(state_matches)} relevant state regulatory record(s).")
                        for m in state_matches:
                            badge = "" if m["label"] == "CONFLICT" else ("" if m["label"] in ("PARTIAL_CONFLICT", "UNCERTAIN") else "")
                            with st.expander(f"{badge} {m['label']} · {m['requirement_id']} — {m.get('policy_name') or 'Statutory Provision'}"):
                                st.write(f"**State Requirement Text:** {m['state_requirement_text']}")
                                st.write(f"**Legal Finding / Analysis:** {m.get('reason')}")
                                if m.get("redline_advice"):
                                    st.success(f" **Drafting Redline Fix:**\n\n{m['redline_advice']}")
                                if m.get("source_url"):
                                    st.markdown(f"[Official Act / Gazette Document]({m['source_url']}) (Section / Page: `{m.get('page_number')}`)")
                    else:
                        st.info(
                            f"No active statutory conflicts or obligations were found in the {jurisdiction} "
                            "regulatory dataset for this specific clause topic."
                        )
                except Exception as e:
                    st.error("Error evaluating clause against state requirements.")
                    st.exception(e)