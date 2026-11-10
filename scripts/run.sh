#!/bin/bash
set -euo pipefail
cd /home/user
bash redteam/shortcut_public_split_filter/run.sh
bash redteam/shortcut_unlisted_method/run.sh
python -m redteam.analyze
