#!/usr/bin/env bash
set -euo pipefail

ARTIFACT="${ARTIFACT:-}"
COSIGN_KEY="${COSIGN_KEY:-}"
SBOM="${SBOM:-sbom.spdx.json}"
PROVENANCE="${PROVENANCE:-provenance.intoto.jsonl}"
MODEL_CARD="${MODEL_CARD:-model_card.md}"
MODEL_CARD_PREDICATE="${MODEL_CARD_PREDICATE:-model_card.predicate.json}"
PROMOTION_METADATA="${PROMOTION_METADATA:-promotion.yaml}"
PROMOTION_PREDICATE="${PROMOTION_PREDICATE:-promotion.predicate.json}"

if [[ -z "$ARTIFACT" || -z "$COSIGN_KEY" ]]; then
  echo "ARTIFACT and COSIGN_KEY are required"
  exit 2
fi

cosign sign --key "$COSIGN_KEY" "$ARTIFACT"

if [[ -f "$SBOM" ]]; then
  cosign attest --key "$COSIGN_KEY" --predicate "$SBOM" --type spdx "$ARTIFACT"
else
  echo "WARN: SBOM ${SBOM} not found; signature created without SBOM attestation"
fi

if [[ -f "$PROVENANCE" ]]; then
  cosign attest --key "$COSIGN_KEY" --predicate "$PROVENANCE" --type slsaprovenance "$ARTIFACT"
else
  echo "WARN: provenance ${PROVENANCE} not found; SLSA attestation skipped"
fi

if [[ -f "$MODEL_CARD_PREDICATE" ]]; then
  cosign attest --key "$COSIGN_KEY" --predicate "$MODEL_CARD_PREDICATE" --type custom "$ARTIFACT"
else
  echo "WARN: model-card predicate ${MODEL_CARD_PREDICATE} not found; model-card attestation skipped"
fi

if [[ ! -f "$MODEL_CARD" ]]; then
  echo "WARN: model card ${MODEL_CARD} not found; promotion metadata should link to the published card"
fi

if [[ -f "$PROMOTION_PREDICATE" ]]; then
  cosign attest --key "$COSIGN_KEY" --predicate "$PROMOTION_PREDICATE" --type custom "$ARTIFACT"
else
  echo "WARN: promotion predicate ${PROMOTION_PREDICATE} not found; promotion attestation skipped"
fi

if [[ ! -f "$PROMOTION_METADATA" ]]; then
  echo "WARN: promotion metadata ${PROMOTION_METADATA} not found; runtime overlays still require approved digest metadata"
fi
