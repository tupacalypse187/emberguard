# EmberGuard Default Security Pack

The bundled policy pack, used when a repo does not carry its own
`.emberguard/policy.md`. It covers the findings that actually hurt small
projects. Only rules marked blocking can fail a review; advisory rules
are reported in the comment and never block a merge.

## Rule: hardcoded-secrets
- Severity: blocking
- Category: Hardcoded secrets
- Patterns: api_key, secret_key, password, private_key, access_token, sk_live_
- Guidance: Credentials, API keys, passwords, and private keys must never be written directly in source code. They belong in environment variables or a secrets manager, and any credential that reaches a commit has to be rotated.

## Rule: injection
- Severity: blocking
- Category: Injection
- Patterns: execute(, format(, %s, subprocess, shell=True, eval(, innerHTML
- Guidance: User-controlled input must never be concatenated into SQL queries, shell commands, or HTML output. Use parameterized queries, argument arrays instead of shell strings, and framework escaping for rendered output.

## Rule: missing-auth
- Severity: blocking
- Category: Missing authentication checks
- Patterns: require_auth, login_required, authenticate, authorize
- Guidance: New or changed endpoints that read or modify account or user data must sit behind an authentication and authorization check. Removing an existing check, or adding an endpoint without one, is a finding.

## Rule: unsafe-deserialization
- Severity: blocking
- Category: Unsafe deserialization
- Patterns: pickle.loads, yaml.load(, marshal.loads, unserialize(, ObjectInputStream
- Guidance: Never deserialize untrusted data with formats that can construct arbitrary objects. Use safe loaders (for example yaml.safe_load) or plain data formats such as JSON.

## Rule: disabled-tls-verification
- Severity: blocking
- Category: Disabled TLS verification
- Patterns: verify=False, verify = False, InsecureSkipVerify, CERT_NONE, rejectUnauthorized: false
- Guidance: TLS certificate verification must stay on. Disabling it removes the protection HTTPS is there to provide and allows man-in-the-middle interception of the connection.

## Rule: broad-permissions
- Severity: advisory
- Category: Overly broad permissions
- Patterns: chmod 777, 0.0.0.0/0, "*", AllowAny, public-read
- Guidance: Permissions, network rules, and access policies should grant the minimum access the code actually needs. Wildcards and world-open settings are flagged for a human to confirm they are intentional.
