SHELL := /bin/bash

PROFILE ?= h100-vllm-kserve
NAMESPACE ?= $(INFERENCE_NAMESPACE)
MONITORING_NAMESPACE ?= $(OBSERVABILITY_NAMESPACE)
ENGINE_RELEASE ?= $(INFERENCE_ENGINE_RELEASE)
GATEWAY_RELEASE ?= $(INFERENCE_GATEWAY_RELEASE)
PREREQS_RELEASE ?= $(CLUSTER_PREREQS_RELEASE)
PROM_STACK_RELEASE ?= $(PROMETHEUS_STACK_RELEASE)
OBSERVABILITY_RELEASE ?= $(INFERENCE_OBSERVABILITY_RELEASE)
ENGINE_DEPLOYMENT_NAME ?= $(INFERENCE_ENGINE_DEPLOYMENT)
ENGINE_SERVICE_NAME ?= $(INFERENCE_ENGINE_SERVICE)
ENGINE_VALUES ?= engine/values-$(PROFILE).yaml
PROM_STACK_VALUES ?= observability/values-kube-prometheus-stack.yaml
OBSERVABILITY_VALUES ?= charts/observability/values.yaml
OBSERVABILITY_EXTRA_VALUES ?=
ENV_VALUES ?=

require-%:
	@if [[ -z "$($*)" ]]; then echo "Missing required configuration: $*"; exit 2; fi

help:
	@grep -E "^[a-zA-Z_-]+:" $(MAKEFILE_LIST) | sed "s/:.*//" | sort

.PHONY: help prereqs render-engine render-observability deploy-engine deploy-gateway deploy-observability up validate-engine validate-config model-cache test-admission test-python uninstall

prereqs: require-NAMESPACE require-PREREQS_RELEASE
	helm dependency update charts/cluster-prereqs
	helm upgrade --install $(PREREQS_RELEASE) charts/cluster-prereqs \
		--namespace $(NAMESPACE) --create-namespace

render-engine: require-NAMESPACE require-ENGINE_RELEASE
	helm template $(ENGINE_RELEASE) charts/inference-engine \
		--namespace $(NAMESPACE) \
		-f charts/inference-engine/values.yaml \
		-f $(ENGINE_VALUES)

render-observability: require-MONITORING_NAMESPACE require-OBSERVABILITY_RELEASE
	helm template $(OBSERVABILITY_RELEASE) charts/observability \
		--namespace $(MONITORING_NAMESPACE) \
		-f $(OBSERVABILITY_VALUES) \
		$(if $(OBSERVABILITY_EXTRA_VALUES),-f $(OBSERVABILITY_EXTRA_VALUES),)

validate-config:
	@if [[ -z "$(ENV_VALUES)" ]]; then echo "Missing required configuration: ENV_VALUES"; exit 2; fi
	python3 ci/validate_values.py "$(ENV_VALUES)"

deploy-engine: require-NAMESPACE require-ENGINE_RELEASE require-ENGINE_DEPLOYMENT_NAME
	helm upgrade --install $(ENGINE_RELEASE) charts/inference-engine \
		--namespace $(NAMESPACE) --create-namespace \
		-f charts/inference-engine/values.yaml \
		-f $(ENGINE_VALUES)
	kubectl rollout status deployment/$(ENGINE_DEPLOYMENT_NAME) -n $(NAMESPACE) --timeout=900s

deploy-gateway: require-NAMESPACE require-GATEWAY_RELEASE
	helm upgrade --install $(GATEWAY_RELEASE) charts/gateway \
		--namespace $(NAMESPACE) --create-namespace \
		-f charts/gateway/values.yaml
	kubectl rollout status deployment/$${ADMISSION_DEPLOYMENT_NAME:?ADMISSION_DEPLOYMENT_NAME required} -n $(NAMESPACE) --timeout=300s

deploy-observability: require-MONITORING_NAMESPACE require-PROM_STACK_RELEASE require-OBSERVABILITY_RELEASE
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
	helm repo update
	helm upgrade --install $(PROM_STACK_RELEASE) prometheus-community/kube-prometheus-stack \
		--namespace $(MONITORING_NAMESPACE) --create-namespace \
		-f $(PROM_STACK_VALUES)
	helm upgrade --install $(OBSERVABILITY_RELEASE) charts/observability \
		--namespace $(MONITORING_NAMESPACE) --create-namespace \
		-f $(OBSERVABILITY_VALUES) \
		$(if $(OBSERVABILITY_EXTRA_VALUES),-f $(OBSERVABILITY_EXTRA_VALUES),)

up: prereqs deploy-engine deploy-gateway deploy-observability

validate-engine: require-NAMESPACE require-ENGINE_SERVICE_NAME
	VLLM_BASE_URL=$${VLLM_BASE_URL:-http://$$(kubectl get svc -n $(NAMESPACE) $(ENGINE_SERVICE_NAME) -o jsonpath='{.spec.clusterIP}'):8000} \
	SMOKE_REQUIRE_SERVER=1 \
	make -C ../playbook smoke-vllm

model-cache:
	bash engine/model-cache/push_model_artifact.sh

test-admission:
	cd gateway/admission && python3 -m pytest test_app.py -q

test-python:
	python3 -m pytest ../impl/tests gateway/admission/test_app.py -q --cov=../impl --cov-report=term-missing --cov-fail-under=60

uninstall: require-NAMESPACE require-ENGINE_RELEASE
	helm uninstall $(ENGINE_RELEASE) -n $(NAMESPACE) || true
