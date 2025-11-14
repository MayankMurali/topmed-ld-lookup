import duckdb
from pathlib import Path
import sys

# Set the data directory
DATA_DIR = Path("data")

if not DATA_DIR.exists():
    print(f"Error: Data directory '{DATA_DIR}' not found.")
    print("Please run the download script first.")
    sys.exit(1)

print("--- Processing Info (Annotation) Files ---")
info_files = sorted(DATA_DIR.glob("EUR_chr*_info_annotation.csv.gz"))

for f in info_files:
    chr_name = f.name.split('_')[1] 
    out_file = DATA_DIR / f"{chr_name}.info.parquet"
    
    if out_file.exists():
        print(f"Skipping {f.name}, Parquet file already exists.")
        continue
        
    print(f"Converting {f.name} -> {out_file.name}")
    # <<< CHANGED: Add the chromosome as a new column
    duckdb.sql(f"""
        COPY (SELECT *, '{chr_name}' AS CHR FROM read_csv_auto('{f}')) 
        TO '{out_file}' (FORMAT 'PARQUET');
    """)

print("\n--- Processing LD Files ---")
ld_files = sorted(DATA_DIR.glob("EUR_chr*_LD.csv.gz"))

for f in ld_files:
    chr_name = f.name.split('_')[1]
    out_file = DATA_DIR / f"{chr_name}.ld.parquet"
    
    if out_file.exists():
        print(f"Skipping {f.name}, Parquet file already exists.")
        continue

    print(f"Converting {f.name} -> {out_file.name}")
    duckdb.sql(f"""
        COPY (SELECT * FROM read_csv_auto('{f}')) 
        TO '{out_file}' (FORMAT 'PARQUET');
    """)

print("\n--- Creating Master Info File ---")
master_info_file = DATA_DIR / "info_master.parquet"

if not master_info_file.exists():
    print(f"Creating {master_info_file}...")
    duckdb.sql(f"""
        COPY (SELECT * FROM read_parquet('{DATA_DIR}/*.info.parquet')) 
        TO '{master_info_file}' (FORMAT 'PARQUET');
    """)
    print(f"Created {master_info_file}")

    print("Cleaning up intermediate info files...")
    for f in DATA_DIR.glob("*.info.parquet"):
        if f.name != "info_master.parquet":
            f.unlink()
else:
    print(f"{master_info_file} already exists, skipping creation.")


print("\n--- All files converted to Parquet! ---")