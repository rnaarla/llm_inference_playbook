# Branch Protection

Recommended GitHub settings for `main` before public release:

- require pull requests before merging
- require CODEOWNERS review
- require status checks:
  - `lint`
  - `unit`
  - `charts`
  - `links`
  - `secrets`
- require branches to be up to date before merge
- require linear history
- disallow force pushes and branch deletion
- require signed commits if your organization mandates them

Release tags (`v*.*.*`) should be created only after CI is green and
`CHANGELOG.md` is updated.
