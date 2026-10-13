#!/bin/sh
# Keep retrying the sequential downloader until every PDF is present (the Internet Archive stalls at times).
cd "$(dirname "$0")/.."
for round in $(seq 1 60); do
  python3 scripts/download.py > _work/download.log 2>&1
  grep -q "FAILED\|curl:" _work/download.log || { echo "all downloaded"; exit 0; }
  sleep 180
done
echo "gave up"; grep FAILED _work/download.log
