"""Get the backlink summary of a domain with the Semust Backlinks API.

    pip install requests
    export SEMUST_API_USER=... SEMUST_API_PASSWORD=...
    python backlinks.py nytimes.com
"""
import json
import os
import sys
import time

import requests

API = "https://data.semust.com"
HEADERS = {
    "SEMUST-API-USER": os.environ["SEMUST_API_USER"],
    "SEMUST-API-PASSWORD": os.environ["SEMUST_API_PASSWORD"],
}
WAIT = 60  # seconds the API holds the request open before answering 202


def call(path, payload):
    """POST a request and return the final response, polling if the API answers 202."""
    resp = requests.post(f"{API}{path}", params={"wait": WAIT}, json=payload,
                         headers=HEADERS, timeout=WAIT + 30)
    while resp.status_code == 202:
        task = resp.json()
        time.sleep(int(resp.headers.get("Retry-After", 5)))
        resp = requests.get(task["poll_url"], headers=HEADERS, timeout=30)
    return resp


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "nytimes.com"
    resp = call("/v1/backlinks", {
        "type": "summary",   # summary | backlinks | referring_domains | anchors | pages | competitors | history | timeseries
        "target": target,
        "scope": "domain",   # domain (with subdomains) | host | url
        "status": "live",    # live | lost | all
    })
    if resp.status_code != 200:
        sys.exit(f"Error {resp.status_code}: {resp.text}")

    data = resp.json()
    s = data["result"]
    print(f"{s['target']}  Semust Rate {s['semust_rate']}")
    for label, key in [("Backlinks", "total_backlinks"), ("  dofollow", "dofollow_backlinks"),
                       ("  nofollow", "nofollow_backlinks"), ("Referring domains", "referring_domains"),
                       ("Referring IPs", "referring_ips"), ("Broken backlinks", "broken_backlinks")]:
        print(f"{label:<20} {s[key]:>15,}")

    top_tlds = sorted(s["links_by_tld"].items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("Top TLDs:", ", ".join(f"{tld} {n:,}" for tld, n in top_tlds))

    with open("backlinks_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nCost ${data['cost']}. Full response saved to backlinks_result.json")


if __name__ == "__main__":
    main()
