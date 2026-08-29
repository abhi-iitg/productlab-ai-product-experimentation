# Security Policy

## Supported Versions

Only the latest release of this repository is supported with security fixes.

## Reporting a Vulnerability

If you believe you've found a security vulnerability in this project, please report it privately using [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) (Security tab → "Report a vulnerability") on this repository, rather than opening a public issue.

Please do not open a public GitHub issue for an undisclosed vulnerability — this gives time to assess and address the report before it's publicly visible.

## Handling Sensitive Data

This project never expects real secrets or personal participant data in the repository or in issue reports:

- Never include an OpenAI API key, `.env` file contents, or any other credential in a report, issue, or pull request.
- Never include real participant names, contact information, or other personally identifiable information — the platform is designed around anonymized, pseudonymous feedback only (see `docs/architecture.md`).
