from pathlib import Path
import zipfile
import json
import csv

# Location of the extracted CUAD folder
CUAD_DIR = Path("data/cuad/cuad-main-extracted/cuad-main")

DATA_ZIP = CUAD_DIR / "data.zip"
CATEGORY_FILE = CUAD_DIR / "category_descriptions.csv"


# ============================================================
# PART 1: CUAD CATEGORY LIST
# ============================================================

print("=" * 60)
print("CUAD CATEGORY DESCRIPTIONS")
print("=" * 60)

if CATEGORY_FILE.exists():

    with open(CATEGORY_FILE, "r", encoding="utf-8-sig") as f:

        reader = csv.reader(f)

        for row in reader:
            print(row)

else:
    print("ERROR: category_descriptions.csv not found.")


# ============================================================
# PART 2: READ CUAD DATA
# ============================================================

print("\n" + "=" * 60)
print("READING CUADv1.JSON")
print("=" * 60)

if not DATA_ZIP.exists():

    print("ERROR: data.zip not found.")
    print(f"Expected location: {DATA_ZIP}")
    exit()

with zipfile.ZipFile(DATA_ZIP, "r") as z:

    with z.open("CUADv1.json") as f:

        data = json.load(f)


articles = data.get("data", [])

print("\nNumber of contracts:", len(articles))


# ============================================================
# PART 3: INSPECT THE FIRST QUESTION
# ============================================================

print("\n" + "=" * 60)
print("FIRST CUAD QUESTION STRUCTURE")
print("=" * 60)

first_article = articles[0]

print("\nContract:")
print(first_article.get("title"))

first_paragraph = first_article.get("paragraphs", [])[0]

qas = first_paragraph.get("qas", [])

if qas:

    first_qa = qas[0]

    print("\nKeys stored in this annotation:")
    print(first_qa.keys())

    print("\nQuestion:")
    print(first_qa.get("question"))

    print("\nAnswers:")

    for answer in first_qa.get("answers", []):
        print("-", answer.get("text"))


# ============================================================
# PART 4: SHOW FIRST 10 QUESTIONS
# ============================================================

print("\n" + "=" * 60)
print("FIRST 10 CUAD QUESTIONS")
print("=" * 60)

count = 0

for article in articles:

    for paragraph in article.get("paragraphs", []):

        for qa in paragraph.get("qas", []):

            print("\nQuestion:")
            print(qa.get("question"))

            answers = qa.get("answers", [])

            if answers:
                print("Answer:")
                print(answers[0].get("text"))

            count += 1

            if count >= 10:
                break

        if count >= 10:
            break

    if count >= 10:
        break