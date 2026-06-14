# Minimum contract — these targets passing IS the definition of "validated" in docs §0.1.
# See README.md §0.2 for the section map.

.PHONY: smoke-vllm deploy-kind bench-local validate-promql lint-k8s test-gateway \
        test-brownout test-cancel-stream test-tenant-quota test-gpu-xid-sim \
        test-kv-pressure test-rollback test-gateway-unit

smoke-vllm:       ## §1.2 — serve small model, run smoke test, assert TTFT bound
	@echo "TODO: implement — see playbook/benchmarks/smoke_test.sh"
	@bash benchmarks/smoke_test.sh

deploy-kind:      ## §5.2 — full manifest set on kind/minikube (CPU mock ok)
	@echo "TODO: implement — render playbook/helm and apply to kind"

bench-local:      ## §2.5 — warmup + steady-state + sweep, emit benchmark report schema
	@echo "TODO: implement — see playbook/benchmarks/"

validate-promql:  ## §2.4 — every PromQL query parses and returns against a live scrape
	@echo "TODO: implement — see playbook/dashboards/"

lint-k8s:         ## §5.2 — kubeconform/kube-linter over helm output
	@echo "TODO: implement — lint playbook/helm/*.yaml"

test-gateway:     ## §1.3, §5.6 — alias translation, 429 paths, cancellation propagation
	@echo "TODO: implement — load-level gateway tests"

test-gateway-unit: ## §1.3 — unit tests for learning-artifact gateway
	@cd ci && python -m pytest test_gateway.py -q

test-brownout:       ## §6.5 — KV pressure ladder actions + hysteresis
	@echo "TODO: implement — game-day target"

test-cancel-stream:  ## §6.2 — client disconnect; engine abort + delta recorded
	@echo "TODO: implement — game-day target"

test-tenant-quota:   ## §6.1 — over-budget tenant; 400/429 at admission
	@echo "TODO: implement — game-day target"

test-gpu-xid-sim:    ## §5.2 — simulated XID; watcher cordons + drains
	@echo "TODO: implement — game-day target"

test-kv-pressure:    ## §6.2 — heavy-context flood; heavy-pool + Critical reserve
	@echo "TODO: implement — game-day target"

test-rollback:       ## §6.10 — canary eval regression triggers rollback
	@echo "TODO: implement — game-day target"
