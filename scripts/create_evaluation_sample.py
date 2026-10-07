from pathlib import Path
import pandas as pd

INPUT_FILE = Path("data/processed/final_candidate_clauses.csv")
OUTPUT_FILE = Path("data/processed/evaluation_sample.csv")

print("=" * 70)
print("CREATING BALANCED EVALUATION SAMPLE")
print("=" * 70)

# ------------------------------------------------------------
# LOAD FINAL CANDIDATES
# ------------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print("\nTotal candidate clauses:", len(df))


# ------------------------------------------------------------
# AVAILABLE CATEGORIES
# ------------------------------------------------------------

category_counts = df["cuad_category"].value_counts()

print("\nAvailable categories:")

for category, count in category_counts.items():
    print(f"  {category}: {count}")


# ------------------------------------------------------------
# BALANCED SAMPLE
# ------------------------------------------------------------

# Select up to 3 examples from every available category.
# This gives us a balanced pilot dataset instead of taking
# an arbitrary first 25 rows.

samples = []

for category in sorted(df["cuad_category"].unique()):

    category_df = df[
        df["cuad_category"] == category
    ]

    selected = category_df.head(3)

    samples.append(selected)


sample_df = pd.concat(
    samples,
    ignore_index=True
)


# ------------------------------------------------------------
# ADD MANUAL LABELING COLUMNS
# ------------------------------------------------------------

sample_df["label"] = ""
sample_df["reason"] = ""


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

sample_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("BALANCED EVALUATION SAMPLE CREATED")
print("=" * 70)

print("\nTotal evaluation samples:", len(sample_df))

print("\nSamples by category:")

print(
    sample_df["cuad_category"]
    .value_counts()
    .to_string()
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\nColumns:")

print(
    sample_df.columns.tolist()
)