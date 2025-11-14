#!/bin/bash
set -e

BASE_URL="http://topld.genetics.unc.edu/downloads/downloads/EUR/SNV/"
# -----------------

DATA_DIR="data"
mkdir -p $DATA_DIR

for chr in {1..22}; do
  echo "--- Processing Chromosome ${chr} ---"

  STEM="EUR_chr${chr}_no_filter_0.2_1000000"
  LD_FILE="${STEM}_LD.csv.gz"
  INFO_FILE="${STEM}_info_annotation.csv.gz"

  # 1. Download data and checksum files
  curl -L -C - -o $DATA_DIR/${LD_FILE} ${BASE_URL}/${LD_FILE}
  curl -L -C - -o $DATA_DIR/${LD_FILE}.md5sum ${BASE_URL}/${LD_FILE}.md5sum
  curl -L -C - -o $DATA_DIR/${INFO_FILE} ${BASE_URL}/${INFO_FILE}
  curl -L -C - -o $DATA_DIR/${INFO_FILE}.md5sum ${BASE_URL}/${INFO_FILE}.md5sum

  echo "Verifying Chr ${chr}..."

  # 2. Check the files
  (cd $DATA_DIR && md5sum -c ${LD_FILE}.md5sum)
  (cd $DATA_DIR && md5sum -c ${INFO_FILE}.md5sum)

done

echo "--- All files downloaded and verified successfully. ---"