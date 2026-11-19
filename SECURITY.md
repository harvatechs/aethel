# Security Policy

## Supported Versions

Only the latest release of `aethel-codex` receives security updates.

| Version | Supported |
|---|---|
| 0.1.x | :white_check_mark: |

## Reporting a Vulnerability

Please report security vulnerabilities through GitHub Private Vulnerability Reporting on the repository:
https://github.com/harvatechs/aethel/security/advisories

You can also reach out directly to the lead architect:
- **Harsha Vardhan**
  Founder at HarVa Groups
  Lead Architect at Archivist Labs (Init. of Aethel Codex)
  Email: `heyharva@gmail.com`

### Disclosure Timelines
- **Acknowledgment:** Within 72 hours.
- **Assessment & Plan:** Within 14 days.
- **Coordinated Disclosure:** 90 days from report, or sooner upon release of a patch.

Any flaw that could cause `verify` to accept an altered or malformed bundle, leak secret keys, or execute unauthorized network requests is treated as critical (Failure Class 4).
