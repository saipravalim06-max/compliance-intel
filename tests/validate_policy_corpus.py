from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "data" / "policy_corpus"
INDEX_FILE = POLICY_DIR / "policy_index.csv"

def main():
    assert INDEX_FILE.exists(), f"Missing policy index: {INDEX_FILE}"

    with INDEX_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print("Index columns:", reader.fieldnames)

    assert rows, "Policy index is empty"

    ids = [row.get("policy_id", "").strip() for row in rows]
    duplicates = sorted({pid for pid in ids if pid and ids.count(pid) > 1})
    missing_ids = [i + 1 for i, pid in enumerate(ids) if not pid]

    print(f"Policies in index: {len(rows)}")
    print("Duplicate policy IDs:", duplicates or "None")
    print("Rows missing policy IDs:", missing_ids or "None")

    files = sorted(POLICY_DIR.glob("POL-*.txt"))
    print(f"Policy text files found: {len(files)}")

    file_ids = [p.stem.split("_")[0] for p in files]
    duplicate_file_ids = sorted(
        {pid for pid in file_ids if file_ids.count(pid) > 1}
    )
    print("Duplicate IDs in filenames:", duplicate_file_ids or "None")

    missing_files = sorted(set(ids) - set(file_ids))
    unindexed_files = sorted(set(file_ids) - set(ids))
    print("Policies without text files:", missing_files or "None")
    print("Files absent from index:", unindexed_files or "None")

    for path in files:
        text = path.read_text(encoding="utf-8")
        requirement_lines = [
            line.strip()
            for line in text.splitlines()
            if re.match(r"^\s*(?:\d+[\.\)]|[-*])\s+", line)
        ]
        print(f"{path.name}: {len(requirement_lines)} numbered/bulleted lines")

    problems = duplicates or missing_ids or duplicate_file_ids or missing_files or unindexed_files
    if problems:
        raise SystemExit("\nValidation found issues. Review the output above.")

    print("\nBasic policy corpus validation passed.")

if __name__ == "__main__":
    main()