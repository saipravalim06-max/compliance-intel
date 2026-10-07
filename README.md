# Compliance Intelligence — Dataset & Evaluation

This workspace contains the dataset preparation and evaluation work for the Compliance Intelligence project.

## Purpose

The project compares contractual clauses with company policies to identify potential policy conflicts and compliance issues.

This workspace focuses on:

- Company policy corpus preparation
- CUAD contract dataset preparation
- CUAD-to-policy category mapping
- Candidate clause extraction
- Evaluation dataset construction

## Dataset Sources

### Company Policy Corpus

The project uses a synthetic company policy corpus containing 17 policies covering areas such as:

- Vendor Management
- Data Privacy
- Payment Terms
- Confidentiality
- Termination
- Liability
- Information Security
- Data Retention
- Third-Party Data Sharing
- Insurance
- Intellectual Property
- Dispute Resolution
- Audit Rights
- Indemnification
- Renewal
- Environmental Compliance
- Warranty

### CUAD

The Contract Understanding Atticus Dataset (CUAD) is used as the contractual clause source.

The current CUAD dataset contains 510 contracts.

## Current Processing Pipeline

```text
Company Policy Corpus
        |
        v
policy_index.csv
        |
        v
CUAD → Company Policy Mapping
        |
        v
Mapped CUAD Categories
        |
        v
Candidate Clause Extraction
        |
        v
Clause + Policy Pair
        |
        v
Evaluation Dataset