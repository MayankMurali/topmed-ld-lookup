# TOPMed LD Lookup

A fast, local query tool for pre-computed TOPMed (EUR) LD data, built with DuckDB.

## 1. Setup

This process is run only once.

```bash
# 1. Clone the repo
git clone https://github.com/MayankMurali/topmed-ld-lookup.git
cd topmed-ld-lookup

# 2. Create the environment
conda env create -f environment.yml
conda activate topmed-ld-lookup

# 3. Download all TOP_LD data (This will take a long time)
./download_data.sh

# 4. Process data into Parquet database
python src/process_to_parquet.py
```

## 2. Usage

```bash
# 1. Activate the environment
conda activate topmed-ld-lookup

# 2. Run a query
python src/query_ld.py rs7412
```