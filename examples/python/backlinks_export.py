"""Export a domain's backlinks to CSV, paging with next_cursor.

    pip install requests
    export SEMUST_API_USER=... SEMUST_API_PASSWORD=...
    python backlinks_export.py example.com --one-per-domain --dofollow --max-rows 5000 --out links.csv

--one-per-domain returns one backlink per referring domain (group_by: domain), which turns the
export into a referring-domains list with an example link for each. Every page of up to 1,000
rows costs $0.0264 + $0.0396 per 1,000 rows, so --max-rows caps the cost.
"""
import argparse
import csv
import os
import sys
import time

import requests

API = "https://data.semust.com"
HEADERS = {
    "SEMUST-API-USER": os.environ["SEMUST_API_USER"],
    "SEMUST-API-PASSWORD": os.environ["SEMUST_API_PASSWORD"],
}
WAIT = 60
PAGE = 1000  # maximum rows per request

COLUMNS = ["source_domain", "source_url", "target_url", "anchor_text", "anchor_type", "is_dofollow",
           "link_type", "link_position", "source_domain_rate", "source_page_rate", "source_spam_score",
           "source_type", "source_country", "first_seen", "last_seen"]


def call(path, payload):
    resp = requests.post(f"{API}{path}", params={"wait": WAIT}, json=payload,
                         headers=HEADERS, timeout=WAIT + 30)
    while resp.status_code == 202:
        task = resp.json()
        time.sleep(int(resp.headers.get("Retry-After", 5)))
        resp = requests.get(task["poll_url"], headers=HEADERS, timeout=30)
    return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="domain, subdomain or URL")
    ap.add_argument("--one-per-domain", action="store_true", help="one backlink per referring domain")
    ap.add_argument("--dofollow", action="store_true", help="dofollow links only")
    ap.add_argument("--min-rate", type=int, help="minimum source_domain_rate, 0-100")
    ap.add_argument("--max-rows", type=int, default=2000, help="stop after this many rows")
    ap.add_argument("--out", default="backlinks.csv")
    args = ap.parse_args()

    conditions = []
    if args.dofollow:
        conditions.append(["is_dofollow", "=", True])
    if args.min_rate is not None:
        conditions.append(["source_domain_rate", ">=", args.min_rate])
    filters = conditions[0] if len(conditions) == 1 else [conditions[0], "and", conditions[1]] if conditions else None

    body = {
        "type": "backlinks",
        "target": args.target,
        "status": "live",
        "group_by": "domain" if args.one_per_domain else "none",
        "order_by": ["source_domain_rate,desc"],
    }
    if filters:
        body["filters"] = filters

    written, cost, cursor, f, writer = 0, 0.0, None, None, None
    try:
        while written < args.max_rows:
            page = {**body, "limit": min(PAGE, args.max_rows - written)}
            if cursor:
                page["cursor"] = cursor  # never combined with offset; expires after 30 minutes
            resp = call("/v1/backlinks", page)
            if resp.status_code != 200:
                sys.exit(f"Error {resp.status_code}: {resp.text}")
            data = resp.json()
            if writer is None:  # open the file once the first page has arrived
                f = open(args.out, "w", newline="", encoding="utf-8")
                writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
                writer.writeheader()
            cost += data["cost"]
            writer.writerows(data["results"])
            written += data["count"]
            print(f"{written:,} of ~{data['total']:,} rows")
            cursor = data.get("next_cursor")
            if not cursor or data["count"] == 0:
                break
    finally:
        if f:
            f.close()

    print(f"{written:,} backlinks written to {args.out}. Cost ${cost:.4f}")


if __name__ == "__main__":
    main()
