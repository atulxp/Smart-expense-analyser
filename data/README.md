# Data directory

The public repository includes only `training_transactions.csv`, a synthetic seed dataset.

The reviewed real-transaction labels and PDF/bank-statement fixtures are intentionally excluded because they contain transaction-derived or banking data. The application falls back to the synthetic dataset when the private reviewed dataset is unavailable.

Human-confirmed merchant mappings are stored locally in `merchant_memory.json` and are intentionally ignored by Git. An empty memory is valid; mappings are created only by explicit user confirmation in the Streamlit review panel.

Explicit confirmations are also appended to `human_feedback.csv`, separately from merchant memory. This file is ignored by Git and is reserved for future batch retraining after enough human-confirmed entities have been collected.
