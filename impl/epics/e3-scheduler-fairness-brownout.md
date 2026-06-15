# E3 — Scheduler: Fairness, Brownout, and Isolation

## Objective

Prove the multi-tenant scheduler path in staging:

- weighted fair queueing dequeues by token-cost debt and tenant weight
- reserve accounting protects Critical capacity before engine dispatch
- per-tenant KV reservations reject noisy neighbors at admission time
- brownout rungs activate from fleet KV pressure with hysteresis
- heavy contexts route to an isolated pool instead of starving normal traffic
- queue, reserve, brownout, and routing decisions are visible in metrics

## Required configuration

Populate scheduler policy from:

- `impl/config/env.example.yaml`
- `impl/environments/values.example.yaml`
- `impl/scheduler/wfq/weights.example.yaml`

Minimum E3 values:

| Field / env var | Purpose |
|---|---|
| `REPLACE_WITH_CRITICAL_TENANT_ID` | Tenant receiving Critical reserve/weight |
| `REPLACE_WITH_STANDARD_TENANT_ID` | Tenant receiving Standard reserve/weight |
| `REPLACE_WITH_SHEDDABLE_TENANT_ID` | Tenant eligible for first brownout shedding |
| `REPLACE_WITH_GOODPUT_KNEE_CONCURRENCY` | Capacity input from the E1 benchmark report |
| `REPLACE_WITH_DEFAULT_TENANT_KV_TOKENS` | Default per-tenant KV reservation cap |
| `REPLACE_WITH_*_TENANT_KV_TOKENS` | Tenant-specific KV caps |
| `REPLACE_WITH_BROWNOUT_STANDARD_MAX_TOKENS` | Standard output-token cap for rung 2 |
| `REPLACE_WITH_BROWNOUT_FALLBACK_MODEL_ALIAS` | Fallback model alias for rung 3 |
| `REPLACE_WITH_HEAVY_CONTEXT_THRESHOLD_TOKENS` | Heavy-pool routing threshold |
| `REPLACE_WITH_CRITICAL_POOL_NAME` | Critical pool route/service key |
| `REPLACE_WITH_STANDARD_POOL_NAME` | Standard pool route/service key |
| `REPLACE_WITH_HEAVY_POOL_NAME` | Heavy-context pool route/service key |
| `PROMETHEUS_URL` | Source for live KV/cache and scheduler metrics |
| `BROWNOUT_HOOK` | Optional staging game-day command for brownout proof |
| `KV_PRESSURE_HOOK` | Optional staging game-day command for reserve/isolation proof |

See `impl/config/README.md` for source, format, and example values. Real tenant
ids, model aliases, and pool names must come from environment-specific overlays
or parameter store output, not from committed source.

## Preflight

```bash
cd impl
python3 ci/validate_values.py environments/<env>.local.yaml
python3 -m compileall scheduler
```

Confirm E1/E2 prerequisites are already deployed:

```bash
export INFERENCE_NAMESPACE=<namespace>
export INFERENCE_GATEWAY_RELEASE=<gateway-release>
export ADMISSION_DEPLOYMENT_NAME=<admission-deployment-name>
export PROMETHEUS_URL=https://<prometheus-url>
```

## Integrate

Wire the scheduler primitives into the gateway or EPP request path in this
order:

1. Load scheduler policy from the environment overlay.
2. Run `CostClassifier` before admission dispatch to select `critical`,
   `standard`, or `heavy` pool.
3. Run `ReserveLedger.admit(...)` before enqueue and call `release(...)` on
   success, error, timeout, or downstream cancellation.
4. Enqueue accepted shared-pool requests with `WeightedFairQueue` and reconcile
   actual token cost after completion.
5. Feed live `kv_cache_usage_perc` and preemption-storm signals into
   `BrownoutController.evaluate(...)`.
6. Apply returned brownout actions through gateway/EPP policy flags:
   `shed_sheddable`, `cap_standard_max_tokens`,
   `disable_speculative_decoding`, `route_standard_to_fallback_model`,
   `shed_standard`, and `critical_only`.

The scaffold intentionally leaves controller-specific policy mapping to the
deployed gateway/EPP implementation. Document that mapping beside
`impl/gateway/POLICY_INTEGRATION.md` when the controller is selected.

## Deploy

```bash
cd impl
make deploy-gateway
```

Redeploy the gateway/admission image or EPP plugin that embeds the scheduler
library. If your controller consumes scheduler policy from a ConfigMap, roll the
gateway deployment after updating the ConfigMap:

```bash
kubectl -n <namespace> rollout restart deployment/<gateway-or-admission-deployment>
kubectl -n <namespace> rollout status deployment/<gateway-or-admission-deployment>
```

## Runtime metrics

The integration should export at least:

- `scheduler_wfq_debt_tokens{tenant}`
- `scheduler_wfq_queue_depth{tenant,priority_class}`
- `scheduler_reserve_admission_total{tenant,priority_class,outcome,reason}`
- `scheduler_tenant_kv_tokens{tenant}`
- `scheduler_brownout_rung`
- `scheduler_brownout_action_total{action}`
- `scheduler_route_decision_total{tenant,priority_class,pool,reason}`

Metric names are the expected scaffold contract; adjust only if your
organization already has a naming convention, and document the translation in
the observability overlay.

## Validate

No new validation harness is added by E3. Use the existing playbook hooks only
after the gateway/EPP integration is deployed:

```bash
export STAGING_GATEWAY_URL=https://<gateway-hostname>
export STAGING_REQUIRE=1
export KV_PRESSURE_HOOK='bash ops/game-day/kv-pressure.sh'
export BROWNOUT_HOOK='bash ops/game-day/brownout.sh'

make -C playbook test-tenant-quota
make -C playbook test-kv-pressure
make -C playbook test-brownout
```

Expected results:

- weighted tenants continue to receive service under bursty shared-pool load
- Critical requests admit while Sheddable traffic sheds under KV pressure
- heavy contexts route to the heavy pool
- brownout rungs increase in order and recover one tier per stable interval
- metrics show queue debt, reserve decisions, brownout rung, and route decisions

## E3 Done Definition

E3 is complete only when:

- scheduler config validates with no unresolved placeholders
- gateway/EPP request path loads the scheduler policy
- WFQ, reserve, brownout, and heavy-routing decisions are fail-closed or
  explicitly audited
- scheduler metrics are scraped by Prometheus
- `test-kv-pressure` and `test-brownout` pass with `STAGING_REQUIRE=1` using
  real hooks
- residual policy assumptions are documented in the environment overlay

## Gaps and assumptions

- The current scaffold is library/config only; it does not run a standalone
  scheduler Deployment.
- Live brownout requires E4 Prometheus/DCGM/vLLM KV metrics.
- `REPLACE_WITH_GOODPUT_KNEE_CONCURRENCY` must come from a real E1 benchmark
  report before reserve limits are production-ready.
- Controller-specific policy mutation remains an integration task for the
  selected gateway/EPP implementation.
