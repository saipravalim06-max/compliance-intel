# Evaluation report

Cases: 81 (all synthetic) | accuracy: 81/81 = 100.0%

## Per-label precision / recall / F1

| label | support | precision | recall | F1 |
|---|---|---|---|---|
| CONFLICT | 38 | 1.00 | 1.00 | 1.00 |
| PARTIAL_CONFLICT | 1 | 1.00 | 1.00 | 1.00 |
| NO_CONFLICT | 35 | 1.00 | 1.00 | 1.00 |
| UNCERTAIN | 7 | 1.00 | 1.00 | 1.00 |

## Confusion matrix (rows = gold, columns = predicted)

| gold \ predicted | CONFLICT | PARTIAL_CONFLICT | NO_CONFLICT | UNCERTAIN |
|---|---|---|---|---|
| CONFLICT | 38 | 0 | 0 | 0 |
| PARTIAL_CONFLICT | 0 | 1 | 0 | 0 |
| NO_CONFLICT | 0 | 0 | 35 | 0 |
| UNCERTAIN | 0 | 0 | 0 | 7 |

## Accuracy by category

| category | correct / total |
|---|---|
| advance payment | 2/2 |
| assignment | 2/2 |
| audit notice | 2/2 |
| backup purge | 1/1 |
| breach notification | 3/3 |
| change-of-control notice | 3/3 |
| confidentiality survival | 2/2 |
| cure period | 2/2 |
| data deletion | 2/2 |
| data sharing | 4/4 |
| environmental incident | 2/2 |
| exclusivity | 2/2 |
| force majeure notice | 2/2 |
| force majeure termination | 2/2 |
| insurance | 4/4 |
| late fee | 3/3 |
| liability cap | 4/4 |
| negotiation period | 2/2 |
| non-compete | 2/2 |
| non-solicit | 2/2 |
| payment term | 2/2 |
| price escalation | 2/2 |
| record retention | 2/2 |
| renewal notice | 2/2 |
| renewal price increase | 2/2 |
| return/destroy | 2/2 |
| sub-processing | 2/2 |
| termination notice | 12/12 |
| trap: different quantity | 1/1 |
| trap: different topic | 1/1 |
| trap: substring | 1/1 |
| vulnerability remediation | 2/2 |
| warranty | 2/2 |

## Failures (0)

None.

## Retrieval (hashing, 93 policy lines)

- gold line in top-5: 54/81 = 66.7%
- mean reciprocal rank: 0.584
