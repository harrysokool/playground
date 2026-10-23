# Diagnosis comment detection (separate from the six-field scores)

| | rules_paddle_light | rules_azure_di | aoai_v2 |
|---|---|---|---|
| Receipts | 13 | 13 | 13 |
| **Correct** | 13 | 13 | 13 |
| **Accuracy %** | 100.0 | 100.0 | 100.0 |
| Needs review | 0 | 0 | 0 |
| False missing (comment there, flagged) | 0 | 0 | 0 |
| False present (no comment, not flagged) | 0 | 0 | 0 |
| No result | 0 | 0 | 0 |

## Detail

| set | receipt | truth | rules_paddle_light | rules_azure_di | aoai_v2 |
|---|---|---|---|---|---|
| v2 | receipt1 | missing | missing | missing | missing |
| v2 | receipt2 | missing | missing | missing | missing |
| v2 | receipt3 | missing | missing | missing | missing |
| v2 | receipt4 | missing | missing | missing | missing |
| v2 | receipt5 | missing | missing | missing | missing |
| v2 | receipt6 | missing | missing | missing | missing |
| v2 | receipt8 | missing | missing | missing | missing |
| v2 | receipt9 | present | present | present | present |
| v2 | receipt10 | missing | missing | missing | missing |
| v1 | receipt1 | present | present | present | present |
| v1 | receipt2 | missing | missing | missing | missing |
| v1 | receipt3 | present | present | present | present |
| v1 | receipt5 | missing | missing | missing | missing |
