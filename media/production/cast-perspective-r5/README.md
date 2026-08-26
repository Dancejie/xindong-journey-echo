# Cast Perspective R5 — archived full-coverage planning package

> **ARCHIVED / DO NOT SUBMIT.** The product scope changed to the smaller 480p gender-rotation plan. This 198-job package is retained only as a reproducible planning artifact. It has no budget or rights approval and must not be converted into a paid batch.
>
> Project budget policy: [../BUDGET_POLICY.md](../BUDGET_POLICY.md). Any projected or cumulative external-generation spend above CNY 200 requires a fresh manual approval that names the maximum amount.

This directory is a **zero-network, fail-closed planning and approval gate**. It now contains the complete local production inputs; no provider task has been submitted from it.

## Authoritative scope

`runtime-variant-matrix.json` is the runtime authority. The gate binds its exact SHA-256 and derives paid work only from masters whose `status` is `requiresGeneration`:

- Runtime semantic masters: **188**
- Existing masters safe for strict reuse: **10**
- Semantic-master gaps: **178**
- Actual provider jobs: **198**
- Planned local current-eight composites: **4**
- Routing composition of the 178 gaps:
  - `perspective`: 58
  - `current-eight`: 4
  - `participant-pov`: 32
  - `unordered-pair`: 81
  - `fixed-cast`: 3
- All 8 `day1.introductions` masters are new voiced `character-speech` jobs. The old Jiangmi clip has no intelligible self-introduction dialogue and is not reusable.
- Direct eight-face provider generations are forbidden because two pilots produced missing/repeated identities.
- `D1-A3B-cast-first-impressions--group-current-eight` is assembled locally from the eight already-required voiced introductions, so it adds no provider job.
- The other three `current-eight` masters each use eight single-identity provider atoms, then one local eight-person edit: **24 provider jobs** and **3 local composites**.
- Therefore: `178 - 4 direct group jobs + 24 single-person atoms = 198 provider jobs`; final runtime semantic masters remain **188**.

Fixed provider contract:

- Exact model: `seedance-2.0-mini`
- `9:16`, `15s`, `720p`, `generate_audio=true`, `watermark=false`
- Concurrency exactly 2; automatic API retry exactly 0
- Total base provider duration: **2,970 seconds**

`task-matrix.json` binds the runtime matrix SHA, describes the `requiresGeneration` derivation, records route counts and the eight voiced-introduction targets. The validator independently loads the runtime matrix and rejects any changed SHA, stale count, missing semantic master, extra job or altered routing semantics.

## Files

- `runtime-variant-matrix.json` — authoritative runtime-master coverage and reuse verdicts; this gate only reads it.
- `task-matrix.json` — immutable derivation/binding contract for the paid gap.
- `build_production_inputs.py` — deterministic zero-network builder for prompts, identity boards, provider manifest and local-composite contracts.
- `validate_production_inputs.py` — exact `178/178` semantic, `198/198` provider-job and `4/4` local-composite validator.
- `manifest.r5.json` — complete local provider plan with `doNotSubmit=true`.
- `prompts-r5/` — 198 director-grade, five-window 15-second prompts; includes eight natural voiced introductions.
- `refs-r5/` — 27 text-free pair boards; single-person jobs reuse the eight approved portraits directly.
- `manifest.template.json` — empty, intentionally blocked provider-manifest template.
- `batch-approval.schema.json` — strict approval contract.
- `batch-approval.template.json` — intentionally unapproved, zero-budget template.
- `validate_batch_gate.py` — standard-library-only offline validator.
- `run-gated.zsh` — validation-first wrapper; only `--execute` can reach the provider.

## Production shot contract

Every `manifest.shots[]` row binds one provider job to an exact semantic master. Direct jobs use the semantic cast; current-eight atoms set `semanticIdentityCast` to all eight and `identityCast` to exactly one person. IDs and outputs are deterministic:

```json
{
  "id": "D1-A3-cast-introductions--p-shenmo--r5",
  "kind": "self-introduction",
  "targetAssetId": "D1-A3-cast-introductions--p-shenmo",
  "semanticTargetAssetId": "D1-A3-cast-introductions--p-shenmo",
  "targetRuntimeAssetId": "D1-A3-cast-introductions--p-shenmo",
  "eventId": "day1.introductions",
  "servedEventIds": ["day1.introductions"],
  "routingMode": "perspective",
  "perspectiveCharacterId": "shenmo",
  "applicablePerspectiveCharacterIds": ["shenmo"],
  "participantIds": [],
  "identityCast": ["shenmo"],
  "semanticIdentityCast": ["shenmo"],
  "reference_image": "../../../frontend/public/media/portraits/shenmo.jpg",
  "referenceImageSha256": "64-lowercase-hex",
  "referenceImageRole": "single-identity-anchor",
  "prompt_file": "prompts-r5/D1-A3-cast-introductions--p-shenmo--r5.txt",
  "promptSha256": "64-lowercase-hex",
  "generationModel": "seedance-2.0-mini",
  "audioMode": "character-speech",
  "rightsStatus": "pending",
  "rightsRefIds": [],
  "likenessConsentRefIds": [],
  "voiceConsentRefIds": [],
  "stateIn": "Exact visible scene entry state.",
  "stateOut": "Exact visible scene exit state.",
  "identityNotes": "沈墨 is the only recognizable face and speaking character.",
  "output_name": "D1-A3-cast-introductions--p-shenmo--r5-candidate.mp4"
}
```

For non-perspective masters, `perspectiveCharacterId` is `null`; semantic fields still match the runtime matrix. Every recognizable provider cast member must appear by Chinese name in the prompt. Pair jobs use reviewed text-free composite boards. No provider job contains more than two recognizable faces; current-eight outputs are deterministic local edits from eight QA-approved single-person sources.

A local motion reference is optional, but it must be hashed, declared `referenceVideoRole: "motion-only"`, and covered by `referenceVideoRightsRefIds`. Remote/signed `reference_video_url` inputs are rejected. Introductions must use `character-speech`; other semantic masters may use `character-speech` or `ambient-only`, while `generate_audio` remains true.

## Offline validation

Check the bound runtime matrix and intentionally blocked templates:

```bash
cd media/production/cast-perspective-r5
./run-gated.zsh --template-check
```

Check a filled but still blocked plan. This verifies all 198 local provider prompt/reference hashes, exact 178-gap semantic coverage, four local-composite contracts, identity anchors, rights coverage, unit price, base/retry/hard budget ceilings, reviewers and timestamps without making an HTTP request:

```bash
python3 build_production_inputs.py
python3 validate_production_inputs.py
python3 /absolute/path/to/seedance_fumin_batch.py manifest.r5.json --validate-only

./run-gated.zsh --validate-only \
  --manifest manifest.r5.json \
  --approval batch-approval.r5.json
```

Useful local hash command:

```bash
shasum -a 256 runtime-variant-matrix.json task-matrix.json manifest.r5.json prompts-r5/FILE.txt refs-r5/FILE.jpg
```

## Price and authorization boundary

The current Fumin model-list response identifies `seedance-2.0-mini` but exposes no price, credit, billing or cost field. Price must come from the current Fumin billing dashboard or provider quote, never a guess. Complete:

- currency, unit amount, `per-task` or `per-second` basis, evidence reference, verifier and time;
- base generation maximum ≥ calculated 198-job cost;
- explicit retry task cap and retry budget, both allowed to be zero;
- hard total maximum ≥ base cap + retry cap;
- `retryRequiresNewApproval=true` — there is never an automatic paid retry;
- technical reviewer, rights reviewer, budget owner, scope/ticket reference and timezone-qualified times;
- commercial/public use, likeness, voice and any motion-reference rights.

Approval binds three hashes: provider manifest, task matrix, and runtime variant matrix. Changing any semantic route, prompt, reference, model/spec, budget or rights input requires review again.

## Paid execution — permanently disabled

This 198-job plan is an archived comparison artifact and can never be submitted. `run-gated.zsh --execute` exits with status `4` before credentials, adapters or provider calls are inspected. Do not flip `doNotSubmit`, create an executable approval, or copy these prompts into a replacement batch.

The only active media direction is the smaller 480p R6 gender-rotation plan. It has its own scope, rights review and CNY 200 cumulative-project manual budget gate. Provider `succeeded` would still mean candidate only; identity, speech/ASR, audio, continuity, framing, runtime and mobile QA decide whether a candidate can become an approved runtime asset.
