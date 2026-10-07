from pathlib import Path
import pandas as pd

POLICY_DIR = Path("data/policy_corpus")
MAPPING_FILE = Path("data/processed/cuad_policy_mapping.csv")

mapping = pd.read_csv(MAPPING_FILE)

print("=" * 70)
print("MAPPED COMPANY POLICIES")
print("=" * 70)

policy_ids = mapping["policy_id"].drop_duplicates().tolist()

for policy_id in policy_ids:
    policy_row = mapping[mapping["policy_id"] == policy_id].iloc[0]
    policy_name = policy_row["policy_name"]

    matching_files = list(POLICY_DIR.glob(f"{policy_id}_*.txt"))

    print("\n" + "=" * 70)
    print(f"{policy_id} — {policy_name}")
    print("=" * 70)

    if not matching_files:
        print("ERROR: Policy file not found.")
        continue

    policy_file = matching_files[0]

    print(f"File: {policy_file.name}")
    print("\nPolicy text:\n")

    text = policy_file.read_text(encoding="utf-8")
    print(text)

print("\n" + "=" * 70)
print("CUAD CATEGORIES BEING MAPPED")
print("=" * 70)

for _, row in mapping.iterrows():
    print(
        f"{row['cuad_category']}"
        f"  -->  {row['policy_id']} — {row['policy_name']}"
    )