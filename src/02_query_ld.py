import duckdb
import argparse
import sys
from pathlib import Path

# --- Configuration ---
DATA_DIR = Path("data")
INFO_MASTER_FILE = DATA_DIR / "info_master.parquet"
LD_FILE_TEMPLATE = DATA_DIR / "{chr_num}.ld.parquet"
# ---------------------

def setup_argparse():
    """Sets up the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Fast query of TOPMed-EUR LD data."
    )
    parser.add_argument(
        "rsid", 
        type=str, 
        help="The rsID of the SNP to query (e.g., 'rs7412')."
    )
    parser.add_argument(
        "-r", "--r2_threshold", 
        type=float, 
        default=0.2, 
        help="Minimum r-squared value to report. Default: 0.2"
    )
    return parser.parse_args()

def find_snp_info(con, rsid):
    """
    Queries the master info file to find a SNP's chromosome and position.
    """
    print(f"Finding info for {rsid}...")
    try:
        # Use parameterized query to prevent SQL injection
        result = con.execute(
            f"SELECT Position, rsID, Uniq_ID FROM read_parquet('{INFO_MASTER_FILE}') WHERE rsID = ?", 
            [rsid]
        ).fetchone()
        
        if not result:
            print(f"Error: rsID '{rsid}' not found in the database.", file=sys.stderr)
            return None, None

        pos, found_rsid, uniq_id = result
        # The Uniq_ID has the format 'POS:REF:ALT'
        # We need the CHR from the LD file name.
        # But wait, the info file itself doesn't have CHR. We'll find it from the Uniq_ID.
        # Let's assume for now Uniq_ID is what we need to join.
        # The LD files use 'SNP1' (which is the position).
        return pos, found_rsid

    except Exception as e:
        print(f"Database error: {e}", file=sys.stderr)
        return None, None

def find_ld_pairs(con, pos, chr_num, r2_min):
    """
    Queries the correct chromosome LD file for matching pairs.
    """
    ld_file = Path(str(LD_FILE_TEMPLATE).format(chr_num=chr_num))
    if not ld_file.exists():
        print(f"Error: LD file not found for chromosome {chr_num}", file=sys.stderr)
        return None

    print(f"Querying LD pairs on chr{chr_num}...")
    
    # This query finds pairs where our SNP is either SNP1 or SNP2
    # It also joins back to the info file to get the rsIDs for the *other* SNPs
    query = f"""
    WITH AllPairs AS (
        -- Find pairs where our SNP is SNP1
        SELECT 
            SNP2 AS PairedPosition, 
            R2, 
            Dprime
        FROM read_parquet('{ld_file}')
        WHERE SNP1 = {pos} AND R2 >= {r2_min}
        
        UNION ALL
        
        -- Find pairs where our SNP is SNP2
        SELECT 
            SNP1 AS PairedPosition, 
            R2, 
            Dprime
        FROM read_parquet('{ld_file}')
        WHERE SNP2 = {pos} AND R2 >= {r2_min}
    )
    
    -- Join with the info file to get rsID and details for the paired SNPs
    SELECT 
        info.rsID AS Paired_rsID,
        info.Position AS Paired_Position,
        p.R2,
        p.Dprime,
        info.VEP_ensembl_Gene_Name AS Gene
    FROM AllPairs AS p
    LEFT JOIN read_parquet('{INFO_MASTER_FILE}') AS info
        ON p.PairedPosition = info.Position
    ORDER BY p.R2 DESC
    """
    
    try:
        results = con.execute(query).fetch_df()
        return results
    except Exception as e:
        print(f"Database error during LD query: {e}", file=sys.stderr)
        return None

def find_chr_from_rsid(con, rsid):

    pass 

def find_snp_info_and_chr(con, rsid):

    print(f"Finding info for {rsid}...")
    try:
        result = con.execute(
            f"""
            SELECT Position, rsID, CHR 
            FROM read_parquet('{INFO_MASTER_FILE}') 
            WHERE rsID = ?
            """, 
            [rsid]
        ).fetchone()
        
        if not result:
            print(f"Error: rsID '{rsid}' not found in the database.", file=sys.stderr)
            return None, None, None

        pos, found_rsid, chr_num = result
        return pos, found_rsid, chr_num

    except Exception as e:
        # This will fail if the CHR column doesn't exist.
        if "column CHR does not exist" in str(e):
            print("---")
            print("FATAL DESIGN ERROR: 'CHR' column not in info_master.parquet.", file=sys.stderr)
            print("You must re-run the 'src/process_to_parquet.py' script.", file=sys.stderr)
            print("Please see the updated script.", file=sys.stderr)
            print("---")
            sys.exit(1)
        print(f"Database error: {e}", file=sys.stderr)
        return None, None, None


def main():
    args = setup_argparse()
    
    # --- Check for data files ---
    if not INFO_MASTER_FILE.exists() or not list(DATA_DIR.glob("*.ld.parquet")):
        print(f"Error: Parquet files not found in '{DATA_DIR}'.", file=sys.stderr)
        print("Please run 'python src/process_to_parquet.py' first.", file=sys.stderr)
        sys.exit(1)

    # Use a persistent, in-memory database connection
    con = duckdb.connect()

    # 1. Find the SNP's position and chromosome
    pos, rsid, chr_num = find_snp_info_and_chr(con, args.rsid)
    
    if not pos:
        con.close()
        sys.exit(1)
        
    print(f"Found: {rsid} (Position: {pos}, CHR: {chr_num})")

    # 2. Find all LD pairs
    ld_results = find_ld_pairs(con, pos, chr_num, args.r2_threshold)
    
    con.close() # Close connection after all queries are done

    if ld_results is None:
        print("LD query failed.")
        sys.exit(1)

    # 3. Print the results
    if ld_results.empty:
        print(f"\nNo LD pairs found for {rsid} with r² >= {args.r2_threshold}")
    else:
        print(f"\n--- LD Proxies for {rsid} (r² >= {args.r2_threshold}) ---")
        print(ld_results.to_string(index=False))

if __name__ == "__main__":
    main()