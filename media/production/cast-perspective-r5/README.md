# Cast Perspective R5 — semantic-gap paid batch gate

This directory is a **zero-network, fail-closed planning and approval gate**. It does not contain production prompts/reference boards, and no provider task has been submitted from it.

## Authoritative scope

`runtime-variant-matrix.json` is the runtime authority. The gate binds its exact SHA-256 and derives paid work only from masters whose `status` is `requiresGeneration`:

- Runtime semantic masters: **188**
- Existing masters safe for strict reuse: **10**
- New provider candidates: **178**
- Routing composition of the 178 gaps:
  - `perspective`: 58
  - `current-eight`: 4
  - `participant-pov`: 32
  - `unordered-pair`: 81
  - `fixed-cast`: 3
- All 8 `day1.introductions` masters are new voiced `character-speech` jobs. The old Jiangmi clip has no intelligible self-introduction dialogue and is not reusable.
- `D1-A3B-cast-first-impressions--group-current-eight` is itself a required generated eight-person master. It is not treated as a free local assembly.

Fixed provider contract:

- Exact model: `seedance-2.0-mini`
- `9:16`, `15s`, `720p`, `generate_audio=true`, `watermark=false`
- Concurrency exactly 2; automatic API retry exactly 0
- Total base duration: **2,670 seconds**

`task-matrix.json` binds the runtime matrix SHA, describes the `requiresGeneration` derivation, records route counts and the eight voiced-introduction targets. The validator independently loads the runtime matrix and rejects any changed SHA, stale count, missing semantic master, extra job or altered routing semantics.

## Files

- `runtime-variant-matrix.json` — authoritative runtime-master coverage and reuse verdicts; this gate only reads it.
- `task-matrix.json` — immutable derivation/binding contract for the paid gap.
- `manifest.template.json` — empty, intentionally blocked provider-manifest template.
- `batch-approval.schema.json` — strict approval contract.
- `batch-approval.template.json` — intentionally unapproved, zero-budget template.
- `validate_batch_gate.py` — standard-library-only offline validator.
- `run-gated.zsh` — validation-first wrapper; only `--execute` can reach the provider.

## Production shot contract

Every `manifest.shots[]` row must copy the semantic fields for one exact `requiresGeneration` master. IDs and output names are deterministic from `targetAssetId`:

```json
{
  "id": "D1-A3-cast-introductions--p-shenmo--r5",
  "kind": "self-introduction",
  "targetAssetId": "D1-A3-cast-introductions--p-shenmo",
  "targetRuntimeAssetId": "D1-A3-cast-introductions--p-shenmo",
  "eventId": "day1.introductions",
  "servedEventIds": ["day1.introductions"],
  "routingMode": "perspective",
  "perspectiveCharacterId": "shenmo",
  "applicablePerspectiveCharacterIds": ["shenmo"],
  "participantIds": [],
  "identityCast": ["shenmo"],
  "reference_image": "refs/D1-A3-cast-introductions--p-shenmo.jpg",
  "referenceImageSha256": "64-lowercase-hex",
  "referenceImageRole": "single-identity-anchor",
  "prompt_file": "prompts/D1-A3-cast-introductions--p-shenmo-r5.txt",
  "promptSha256": "64-lowercase-hex",
  "generationModel": "seedance-2.0-mini",
  "audioMode": "character-speech",
  "rightsStatus": "approved",
  "rightsRefIds": ["PRODUCTION-RIGHTS-REF"],
  "likenessConsentRefIds": ["SHENMO-LIKENESS-CONSENT"],
  "voiceConsentRefIds": ["SHENMO-VOICE-CONSENT"],
  "stateIn": "Exact visible scene entry state.",
  "stateOut": "Exact visible scene exit state.",
  "identityNotes": "沈墨 is the only recognizable face and speaking character.",
  "output_name": "D1-A3-cast-introductions--p-shenmo--r5-candidate.mp4"
}
```

For non-perspective masters, `perspectiveCharacterId` is `null`; `participantIds`, `applicablePerspectiveCharacterIds`, `identityCast`, `servedEventIds` and `routingMode` must still exactly match the runtime matrix. More than one recognizable person requires one reviewed composite identity board. Every recognizable cast display name must appear in the prompt.

A local motion reference is optional, but it must be hashed, declared `referenceVideoRole: "motion-only"`, and covered by `referenceVideoRightsRefIds`. Remote/signed `reference_video_url` inputs are rejected. Introductions must use `character-speech`; other semantic masters may use `character-speech` or `ambient-only`, while `generate_audio` remains true.

## Offline validation

Check the bound runtime matrix and intentionally blocked templates:

```bash
cd media/production/cast-perspective-r5
./run-gated.zsh --template-check
```

Check a filled but still blocked plan. This verifies all 178 local prompt/reference hashes, exact runtime semantics, identity anchors, rights coverage, unit price, base/retry/hard budget ceilings, reviewers and timestamps without making an HTTP request:

```bash
./run-gated.zsh --validate-only \
  --manifest manifest.r5.json \
  --approval batch-approval.r5.json
```

Useful local hash command:

```bash
shasum -a 256 runtime-variant-matrix.json task-matrix.json manifest.r5.json prompts/FILE.txt refs/FILE.jpg
```

## Price and authorization boundary

The current Fumin model-list response identifies `seedance-2.0-mini` but exposes no price, credit, billing or cost field. Price must come from the current Fumin billing dashboard or provider quote, never a guess. Complete:

- currency, unit amount, `per-task` or `per-second` basis, evidence reference, verifier and time;
- base generation maximum ≥ calculated 178-task cost;
- explicit retry task cap and retry budget, both allowed to be zero;
- hard total maximum ≥ base cap + retry cap;
- `retryRequiresNewApproval=true` — there is never an automatic paid retry;
- technical reviewer, rights reviewer, budget owner, scope/ticket reference and timezone-qualified times;
- commercial/public use, likeness, voice and any motion-reference rights.

Approval binds three hashes: provider manifest, task matrix, and runtime variant matrix. Changing any semantic route, prompt, reference, model/spec, budget or rights input requires review again.

## Paid execution — not run in this round

Only after production inputs, rights and budget are approved:

1. Set both manifest root/default `doNotSubmit=false`; calculate the final manifest hash.
2. Put exact manifest/task/runtime-matrix hashes in approval; set approval `doNotSubmit=false`.
3. Rerun `--validate-only` and independently review its 178-job receipt.
4. Inject provider credentials from the protected environment; never copy them here.
5. Confirm the exact batch ID and use a disposable `.work-candidates` child:

```bash
export CONFIRM_PAID_BATCH_ID='THE-REVIEWED-BATCH-ID'
export FUMIN_BATCH_CLIENT='/reviewed/path/to/seedance_fumin_batch.py'
./run-gated.zsh --execute \
  --manifest manifest.r5.json \
  --approval batch-approval.r5.json \
  --output-dir .work-candidates/batch-r5-reviewed
```

The wrapper revalidates the entire semantic gap, runs the provider adapter's local validation, removes any shared `FUMIN_IMAGE_URL` override so per-job identity boards cannot be replaced, and then allows the client to probe the exact model.

Provider `succeeded` means candidate only. Identity, speech/ASR, audio, continuity, framing, runtime and mobile QA still decide whether a master can become `approved-runtime`. Any paid rewrite needs a new approval.
