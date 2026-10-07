from pathlib import Path
import zipfile
import json
import re
import csv
import pandas as pd

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

CUAD_DIR = Path("data/cuad/cuad-main-extracted/cuad-main")
DATA_ZIP = CUAD_DIR / "data.zip"

MAPPING_FILE = Path("data/processed/cuad_policy_mapping.csv")
POLICY_DIR = Path("data/policy_corpus")

OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "final_candidate_clauses.csv"


# ------------------------------------------------------------
# READ CUAD CATEGORY FROM QUESTION
# ------------------------------------------------------------

def get_category_from_question(question):
    match = re.search(r'related to "([^"]+)"', question)

    if match:
        category = match.group(1)

        # Normalize a few CUAD naming variations
        category = category.replace("AgreementDate", "Agreement Date")
        category = category.replace("EffectiveDate", "Effective Date")
        category = category.replace("GoverningLaw", "Governing Law")

        return category

    return None


# ------------------------------------------------------------
# LOAD MAPPING
# ------------------------------------------------------------

print("=" * 70)
print("FINAL CUAD CANDIDATE EXTRACTION")
print("=" * 70)

if not MAPPING_FILE.exists():
    print("ERROR: Mapping file not found:")
    print(MAPPING_FILE)
    raise SystemExit

mapping_df = pd.read_csv(MAPPING_FILE)

print("\nMappings found in CSV:", len(mapping_df))

# ------------------------------------------------------------
# EXCLUDE QUESTIONABLE MAPPING
# ------------------------------------------------------------

# We are leaving your CSV untouched.
# This mapping is excluded from the evaluation dataset because
# Third Party Beneficiary does not directly correspond to
# Third-Party Data Sharing Policy.

EXCLUDED_CATEGORIES = {
    "Third Party Beneficiary"
}

mapping_df = mapping_df[
    ~mapping_df["cuad_category"].isin(EXCLUDED_CATEGORIES)
].copy()

print("Mappings used for extraction:", len(mapping_df))

# Create:
# CUAD category -> policy ID
category_to_policy = dict(
    zip(
        mapping_df["cuad_category"],
        mapping_df["policy_id"]
    )
)

# Create:
# Policy ID -> policy name
policy_names = dict(
    zip(
        mapping_df["policy_id"],
        mapping_df["policy_name"]
    )
)

print("\nCategories being used:")

for category, policy_id in category_to_policy.items():
    print(
        f"  {category} --> "
        f"{policy_id} — {policy_names[policy_id]}"
    )


# ------------------------------------------------------------
# LOAD POLICY TEXT
# ------------------------------------------------------------

policy_texts = {}

for policy_id in mapping_df["policy_id"].unique():

    matching_files = list(
        POLICY_DIR.glob(f"{policy_id}_*.txt")
    )

    if not matching_files:
        print(
            f"\nWARNING: Policy file not found for {policy_id}"
        )
        continue

    policy_file = matching_files[0]

    policy_texts[policy_id] = policy_file.read_text(
        encoding="utf-8"
    ).strip()


# ------------------------------------------------------------
# LOAD CUAD
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("LOADING CUAD")
print("=" * 70)

if not DATA_ZIP.exists():
    print("ERROR: CUAD data.zip not found:")
    print(DATA_ZIP)
    raise SystemExit

rows = []

with zipfile.ZipFile(DATA_ZIP, "r") as z:

    with z.open("CUADv1.json") as f:
        data = json.load(f)

articles = data["data"]

print("Contracts found:", len(articles))


# ------------------------------------------------------------
# EXTRACT MATCHED CLAUSES
# ------------------------------------------------------------

for article in articles:

    contract_id = article.get("title", "")

    for paragraph in article.get("paragraphs", []):

        context = paragraph.get("context", "")

        for qa in paragraph.get("qas", []):

            question = qa.get("question", "")

            category = get_category_from_question(question)

            # Ignore CUAD categories that are not mapped
            if category not in category_to_policy:
                continue

            policy_id = category_to_policy[category]

            policy_name = policy_names[policy_id]

            answers = qa.get("answers", [])

            # Only keep questions with actual CUAD answers
            if not answers:
                continue

            for answer in answers:

                clause_text = answer.get(
                    "text",
                    ""
                ).strip()

                if not clause_text:
                    continue

                rows.append({
                    "contract_id": contract_id,
                    "cuad_category": category,
                    "clause_text": clause_text,
                    "policy_id": policy_id,
                    "policy_name": policy_name,
                    "policy_text": policy_texts.get(
                        policy_id,
                        ""
                    )
                })


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

fieldnames = [
    "contract_id",
    "cuad_category",
    "clause_text",
    "policy_id",
    "policy_name",
    "policy_text"
]

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(rows)


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("EXTRACTION COMPLETE")
print("=" * 70)

print("\nFinal candidate clauses:", len(rows))

print("\nSaved to:")
print(OUTPUT_FILE)

print("\nCandidates by CUAD category:")

if rows:
    summary = pd.DataFrame(rows)

    print(
        summary["cuad_category"]
        .value_counts()
        .to_string()
    )

print("\nFirst 5 candidates:")

for row in rows[:5]:

    print("\n" + "-" * 70)

    print("Contract:")
    print(row["contract_id"])

    print("\nCUAD category:")
    print(row["cuad_category"])

    print("\nPolicy:")
    print(
        f"{row['policy_id']} — "
        f"{row['policy_name']}"
    )

    print("\nClause:")
    print(row["clause_text"])

    print("\nPolicy text:")
    print(row["policy_text"])