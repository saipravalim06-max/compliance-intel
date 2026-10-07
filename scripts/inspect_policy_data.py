from pathlib import Path
import pandas as pd

# Location of our policy corpus
POLICY_DIR = Path("data/policy_corpus")

print("=" * 60)
print("POLICY CORPUS")
print("=" * 60)

# Show all files in the policy folder
for file in sorted(POLICY_DIR.iterdir()):
    if file.is_file():
        print(file.name)

# Find the policy index
index_file = POLICY_DIR / "policy_index.csv"

print("\n" + "=" * 60)
print("POLICY INDEX")
print("=" * 60)

if index_file.exists():
    df = pd.read_csv(index_file)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nNumber of policies:", len(df))

    print("\nPolicy information:")
    print(df.to_string(index=False))

else:
    print("ERROR: policy_index.csv was not found.")