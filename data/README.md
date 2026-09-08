# FraudLens Data

## Directory Structure

```text
data/
├── raw/          # Immutable source data (not tracked in Git)
├── staging/      # Cleaned and validated data
└── processed/    # Feature-engineered data
```

## Primary Dataset

**Nigerian Financial Transactions and Fraud Detection Dataset — V1**

| Property | Value |
| --- | --- |
| Provider | Electric Sheep Africa |
| Source | [HuggingFace](https://huggingface.co/datasets/electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset) |
| Type | Synthetic |
| Rows | 5,000,000 |
| Columns | 21 |
| File size | ~924 MB |
| SHA256 | `ed7753fbd7da6d775ce1cd0a339c15abdcc304dae6f668643d15f7e9427cbe09` |
| Fraud rate | 3.5911% (179,553 fraud transactions) |
| License | "other" (non-standard; requires manual review) |

See `dataset_metadata.yml` for detailed metadata.

## Download Instructions

The raw dataset is **intentionally excluded from Git** due to its size (~924 MB).

### Option 1: HuggingFace CLI

```bash
pip install huggingface_hub
huggingface-cli download electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv --repo-type dataset --local-dir data/raw/
```

### Option 2: Manual Download

1. Visit https://huggingface.co/datasets/electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset
2. Download `V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv`
3. Place it in `data/raw/`

### Verify Checksum

```bash
shasum -a 256 data/raw/V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv
```

Expected: `ed7753fbd7da6d775ce1cd0a339c15abdcc304dae6f668643d15f7e9427cbe09`

## Data Provenance

Raw data in `data/raw/` must remain immutable.

All transformations occur in `data/staging/` and `data/processed/`.

## License

The primary dataset uses a non-standard license ("other").

License must be verified before any public distribution.

The FraudLens project source code is MIT licensed (see `LICENSE`).

## Important

* Do not commit large datasets to Git.
* Do not commit credentials, API keys, or connection strings.
* The raw dataset is synthetic — document this clearly in all outputs.
* Multiple pre-computed features have been validated as unreliable — compute features from raw fields only.
