# Playbook validation Makefile — see README.md §0.2

SHELL := /bin/bash
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: help lint validate-promql lint-k8s test-gateway-unit smoke-vllm bench-local deploy-kind \
        test-gateway test-cancel-stream test-tenant-quota test-kv-pressure test-brownout \
        test-gpu-xid-sim test-rollback test-unsigned-checkpoint test-guardrail-down \
        game-day all offline gpu staging record-validation fabric cost-model

help:
	@grep -E '^[a-zA-Z_-]+:' $(MAKEFILE_LIST) | sed 's/:.*//' | sort

offline: lint validate-promql lint-k8s test-gateway-unit bench-local-dry check-profile-drift
	@echo "offline: all CPU-safe checks passed"

lint: validate-promql lint-k8s test-gateway-unit

validate-promql:
	@bash ci/validate-promql.sh

lint-k8s:
	@bash ci/lint-k8s.sh

check-profile-drift:
	@bash ci/check-profile-drift.sh --offline

test-gateway-unit:
	@cd ci && python3 -m pytest test_gateway.py -q

bench-local-dry:
	@BENCH_DRY_RUN=1 bash benchmarks/bench_local.sh

smoke-vllm:
	@bash benchmarks/run_smoke.sh

bench-local:
	@bash benchmarks/bench_local.sh

deploy-kind:
	@bash ci/deploy-kind.sh

deploy-dry:
	@DEPLOY_DRY_RUN=1 bash ci/deploy-kind.sh

test-gateway:
	@python3 ci/test_gateway_load.py

test-cancel-stream:
	@bash ci/test_cancel_stream.sh

test-tenant-quota:
	@bash ci/test_tenant_quota.sh

test-kv-pressure:
	@bash ci/test_kv_pressure.sh

test-brownout:
	@bash ci/test_brownout.sh

test-gpu-xid-sim:
	@bash ci/test_gpu_xid_sim.sh

test-rollback:
	@bash ci/test_rollback.sh

test-unsigned-checkpoint:
	@bash ci/test_unsigned_checkpoint.sh

test-guardrail-down:
	@bash ci/test_guardrail_down.sh

fabric:
	@bash benchmarks/nccl/run_fabric_validation.sh

fabric-dry:
	@FABRIC_DRY_RUN=1 bash benchmarks/nccl/run_fabric_validation.sh

cost-model:
	@python3 calculators/cost_model.py benchmarks/runs/$$(ls -t benchmarks/runs 2>/dev/null | head -1)/report.yaml 2>/dev/null || \
	  (BENCH_DRY_RUN=1 bash benchmarks/bench_local.sh && \
	   python3 calculators/cost_model.py benchmarks/runs/$$(ls -t benchmarks/runs | head -1)/report.yaml)

game-day: test-gateway-unit test-gateway test-tenant-quota test-cancel-stream test-kv-pressure \
          test-brownout test-gpu-xid-sim test-rollback test-unsigned-checkpoint test-guardrail-down
	@echo "game-day: bundle finished (skipped hooks count as pass — wire STAGING hooks for full pass)"

gpu: smoke-vllm bench-local validate-promql
	@echo "gpu: targets completed"

staging: game-day deploy-kind
	@echo "staging: deploy + game-day bundle"

record-validation:
	@python3 ci/record_validation.py

all: offline
	@echo "all: offline complete; run 'make gpu STAGING_REQUIRE=1' on fleet for full validation"
