// Get the backlink summary of a domain with the Semust Backlinks API (Node.js 18+, no dependencies).
//
//   export SEMUST_API_USER=... SEMUST_API_PASSWORD=...
//   node backlinks.mjs nytimes.com

const API = "https://data.semust.com";
const HEADERS = {
  "Content-Type": "application/json",
  "SEMUST-API-USER": process.env.SEMUST_API_USER,
  "SEMUST-API-PASSWORD": process.env.SEMUST_API_PASSWORD,
};
const WAIT = 60; // seconds the API holds the request open before answering 202

const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));

// POST a request and return the final response, polling if the API answers 202.
async function call(path, payload) {
  let resp = await fetch(`${API}${path}?wait=${WAIT}`, {
    method: "POST",
    headers: HEADERS,
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout((WAIT + 30) * 1000),
  });
  while (resp.status === 202) {
    const task = await resp.json();
    await sleep(Number(resp.headers.get("Retry-After") ?? 5));
    resp = await fetch(task.poll_url, { headers: HEADERS });
  }
  return resp;
}

const target = process.argv[2] ?? "nytimes.com";
const resp = await call("/v1/backlinks", {
  type: "summary",
  target,
  scope: "domain",
  status: "live",
});

if (resp.status !== 200) {
  console.error(`Error ${resp.status}: ${await resp.text()}`);
  process.exit(1);
}

const { result: s, cost } = await resp.json();
console.log(`${s.target}  Semust Rate ${s.semust_rate}`);
console.log(`Backlinks          ${s.total_backlinks.toLocaleString("en-US")}`);
console.log(`  dofollow         ${s.dofollow_backlinks.toLocaleString("en-US")}`);
console.log(`Referring domains  ${s.referring_domains.toLocaleString("en-US")}`);
console.log(`Referring IPs      ${s.referring_ips.toLocaleString("en-US")}`);
console.log(`\nCost $${cost}`);
