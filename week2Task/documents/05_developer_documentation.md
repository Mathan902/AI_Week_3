# Acme SDK: API Client Reference

## Authentication
Create the client with an API token supplied through the ACME_API_TOKEN environment variable. Tokens must not be committed to source control. A missing token raises AuthenticationError before a network request is sent.

## Rate limits and retries
When the service returns HTTP 429, the SDK reads the Retry-After header and retries automatically. It makes a maximum of three retry attempts using exponential backoff. Automatic retries can be disabled by setting max_retries to zero when creating the client.

