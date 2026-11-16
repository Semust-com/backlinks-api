<?php
// Get the backlink summary of a domain with the Semust Backlinks API (PHP 7.4+ with the curl extension).
//
//   export SEMUST_API_USER=... SEMUST_API_PASSWORD=...
//   php backlinks.php nytimes.com

const API = "https://data.semust.com";
const WAIT = 60; // seconds the API holds the request open before answering 202

function request(string $method, string $url, ?array $payload = null): array
{
    $ch = curl_init($url);
    $headers = [];
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => WAIT + 30,
        CURLOPT_HTTPHEADER => [
            "Content-Type: application/json",
            "SEMUST-API-USER: " . getenv("SEMUST_API_USER"),
            "SEMUST-API-PASSWORD: " . getenv("SEMUST_API_PASSWORD"),
        ],
        CURLOPT_HEADERFUNCTION => function ($ch, $line) use (&$headers) {
            $parts = explode(":", $line, 2);
            if (count($parts) === 2) {
                $headers[strtolower(trim($parts[0]))] = trim($parts[1]);
            }
            return strlen($line);
        },
    ]);
    if ($payload !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    }
    $body = curl_exec($ch);
    if ($body === false) {
        fwrite(STDERR, "Request failed: " . curl_error($ch) . "\n");
        exit(1);
    }
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return [$status, $headers, $body];
}

// POST a request and return the final response, polling if the API answers 202.
function call(string $path, array $payload): array
{
    [$status, $headers, $body] = request("POST", API . $path . "?wait=" . WAIT, $payload);
    while ($status === 202) {
        $task = json_decode($body, true);
        sleep((int)($headers["retry-after"] ?? 5));
        [$status, $headers, $body] = request("GET", $task["poll_url"]);
    }
    return [$status, $body];
}

$target = $argv[1] ?? "nytimes.com";
[$status, $body] = call("/v1/backlinks", [
    "type" => "summary",
    "target" => $target,
    "scope" => "domain",
    "status" => "live",
]);

if ($status !== 200) {
    fwrite(STDERR, "Error {$status}: {$body}\n");
    exit(1);
}

$data = json_decode($body, true);
$s = $data["result"];
printf("%s  Semust Rate %s\n", $s["target"], $s["semust_rate"]);
printf("Backlinks          %s\n", number_format($s["total_backlinks"]));
printf("  dofollow         %s\n", number_format($s["dofollow_backlinks"]));
printf("Referring domains  %s\n", number_format($s["referring_domains"]));
printf("Referring IPs      %s\n", number_format($s["referring_ips"]));
printf("\nCost $%s\n", $data["cost"]);
