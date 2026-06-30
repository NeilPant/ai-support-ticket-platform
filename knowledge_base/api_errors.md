# API Error Support Playbook

## HTTP 500 and production failures

For API errors, collect request ID, endpoint, timestamp with timezone, response code, region, and a redacted payload sample.

HTTP 500 errors in production should be correlated with application logs and recent deployments before sending a final resolution.

If multiple customers are blocked, route the ticket to the on-call engineering queue and keep the customer updated with investigation status.

## Timeouts

Timeout reports should include latency samples, frequency, affected endpoint, and whether retries succeed.
