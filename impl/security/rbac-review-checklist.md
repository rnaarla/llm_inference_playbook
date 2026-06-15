# RBAC Review Checklist

Use this checklist before applying any cluster-scoped or privileged manifests.

## General

- [ ] Resource names are environment-specific and not placeholders.
- [ ] ServiceAccount is namespace-scoped unless cluster scope is explicitly required.
- [ ] Role/ClusterRole verbs are the minimum required.
- [ ] RoleBindings target only the intended namespace/service account.
- [ ] No wildcard `*` verbs/resources unless justified in writing.
- [ ] NetworkPolicy restricts ingress to expected callers.

## XID Watcher

- [ ] Node patch permission is limited to cordon/taint behavior.
- [ ] Pod delete/eviction permissions are restricted to inference workloads.
- [ ] Target pod selector cannot match non-inference workloads.
- [ ] Fatal XID drain command includes timeout and daemonset handling policy.
- [ ] Watcher does not request GPUs.

## Registry / Verification

- [ ] Model verification has read-only access to public verification keys.
- [ ] Registry credentials are read-only pull credentials at runtime.
- [ ] Signing keys are never mounted into serving pods.
- [ ] Verification failure keeps pod unready/fail-closed.

## Gateway / Admission

- [ ] Admission service is internal-only.
- [ ] Gateway forwards only bounded tenant/priority labels.
- [ ] Audit logs do not include prompt/response content unless an explicit policy exists.
