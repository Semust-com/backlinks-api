#!/usr/bin/env bash
# Get the backlink summary of a domain with the Semust Backlinks API.
#   export SEMUST_API_USER=... SEMUST_API_PASSWORD=...
#   ./backlinks.sh
# A request still running after `wait` seconds answers 202; poll the task with the second command.
set -euo pipefail

curl -sS -X POST "https://data.semust.com/v1/backlinks?wait=60" \
  --max-time 90 \
  -H "Content-Type: application/json" \
  -H "SEMUST-API-USER: ${SEMUST_API_USER}" \
  -H "SEMUST-API-PASSWORD: ${SEMUST_API_PASSWORD}" \
  -d '{
    "type": "summary",
    "target": "nytimes.com",
    "scope": "domain",
    "status": "live"
  }'

# If you received 202, fetch the result with the task_id from the response:
# curl -sS "https://data.semust.com/v1/tasks/$TASK_ID" \
#   -H "SEMUST-API-USER: ${SEMUST_API_USER}" -H "SEMUST-API-PASSWORD: ${SEMUST_API_PASSWORD}"
