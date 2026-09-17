# Processed data

Run the following command after downloading the raw HEMOBP files:

```bash
python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed
```

This creates `hemobp_session_level.csv.gz` and `cohort_flow.json`. Processed patient-level records are not tracked in Git. The complete transformation logic is in `src/build_session_dataset.py`.

