# Security Policy

## Reporting a Vulnerability

Please report vulnerabilities privately through GitHub's private vulnerability
reporting feature if available, or by contacting the repository maintainers.

Do **not** open a public issue containing:

- credentials, tokens, keys, or certificates
- kubeconfigs
- private registry hosts
- cloud account/project/subscription IDs
- production hostnames
- tenant data
- exploit details for an unpatched issue

## Scope

In scope:

- unsafe defaults in this repository
- secret leakage in examples or scaffolds
- admission, policy, or validation logic defects in scaffold code
- documentation that could cause insecure deployment when followed

Out of scope:

- vulnerabilities in infrastructure operated by users of this repo
- issues caused by user-supplied private overlays or secrets
- third-party service outages
- model behavior or safety failures outside the provided guardrail scaffold

## Supported Versions

This repository is pre-1.0. Security fixes target the latest `main` branch until
versioned releases are introduced.

## Secret Handling

This project must not contain real secrets or environment-specific deployment
values. Use placeholders, Kubernetes Secrets, External Secrets, cloud secret
managers, or private GitOps overlays.
