// Get the backlink summary of a domain with the Semust Backlinks API (Go 1.21+, standard library only).
//
//	export SEMUST_API_USER=... SEMUST_API_PASSWORD=...
//	go run . nytimes.com
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"time"
)

const (
	api  = "https://data.semust.com"
	wait = 60 // seconds the API holds the request open before answering 202
)

type summary struct {
	Target            string  `json:"target"`
	SemustRate        float64 `json:"semust_rate"`
	TotalBacklinks    int64   `json:"total_backlinks"`
	DofollowBacklinks int64   `json:"dofollow_backlinks"`
	ReferringDomains  int64   `json:"referring_domains"`
	ReferringIPs      int64   `json:"referring_ips"`
}

type summaryResponse struct {
	Result summary `json:"result"`
	Cost   float64 `json:"cost"`
}

var client = &http.Client{Timeout: (wait + 30) * time.Second}

func send(method, url string, body []byte) (*http.Response, []byte, error) {
	req, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		return nil, nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("SEMUST-API-USER", os.Getenv("SEMUST_API_USER"))
	req.Header.Set("SEMUST-API-PASSWORD", os.Getenv("SEMUST_API_PASSWORD"))
	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, err
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	return resp, data, err
}

// call POSTs a request and returns the final response, polling if the API answers 202.
func call(path string, payload any) (int, []byte, error) {
	body, _ := json.Marshal(payload)
	resp, data, err := send(http.MethodPost, fmt.Sprintf("%s%s?wait=%d", api, path, wait), body)
	for err == nil && resp.StatusCode == http.StatusAccepted {
		var task struct {
			PollURL string `json:"poll_url"`
		}
		if err = json.Unmarshal(data, &task); err != nil {
			break
		}
		retry, convErr := strconv.Atoi(resp.Header.Get("Retry-After"))
		if convErr != nil {
			retry = 5
		}
		time.Sleep(time.Duration(retry) * time.Second)
		resp, data, err = send(http.MethodGet, task.PollURL, nil)
	}
	if err != nil {
		return 0, nil, err
	}
	return resp.StatusCode, data, nil
}

func main() {
	target := "nytimes.com"
	if len(os.Args) > 1 {
		target = os.Args[1]
	}
	status, data, err := call("/v1/backlinks", map[string]any{
		"type":   "summary",
		"target": target,
		"scope":  "domain",
		"status": "live",
	})
	if err != nil {
		fmt.Fprintln(os.Stderr, "request failed:", err)
		os.Exit(1)
	}
	if status != http.StatusOK {
		fmt.Fprintf(os.Stderr, "Error %d: %s\n", status, data)
		os.Exit(1)
	}

	var result summaryResponse
	if err := json.Unmarshal(data, &result); err != nil {
		fmt.Fprintln(os.Stderr, "decode:", err)
		os.Exit(1)
	}
	s := result.Result
	fmt.Printf("%s  Semust Rate %.0f\n", s.Target, s.SemustRate)
	fmt.Printf("Backlinks          %d\n  dofollow         %d\n", s.TotalBacklinks, s.DofollowBacklinks)
	fmt.Printf("Referring domains  %d\nReferring IPs      %d\n", s.ReferringDomains, s.ReferringIPs)
	fmt.Printf("\nCost $%.5f\n", result.Cost)
}
