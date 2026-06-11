#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: 0 GB
# Estimated disk usage after extraction: 0 GB
#
# This reproduction has no external data dependency. If future variants add
# downloads, fetch them into data/downloads/ with idempotent guards.

set -e

cd /home/user

mkdir -p data/downloads
echo "No external datasets or pretrained models are required for this reproduction."
