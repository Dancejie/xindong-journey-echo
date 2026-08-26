# R6 promotion gate

`prepare_promotion.py` turns visually approved R6 candidates into the runtime
IDs already consumed by `backend/game_content.py`. It never calls Seedance or
another provider. Its default mode is read-only.

## Required review record

Copy `visual-qa-allowlist.template.json` to a retained QA record and add only
assets that a human has reviewed. Every item must include:

- the immutable planning-manifest SHA;
- the exact source ID and candidate path;
- the SHA-256 of the reviewed bytes;
- the people actually visible in `identityCast`;
- `visualQaVerdict: passed`;
- `audioQaVerdict: passed` when first-play audio is required.

The allowlist is authoritative for what was seen, but it cannot expand the cast
beyond the lead/support identities planned for that shot. A lead must always be
visible. `D1-A3B` local composites must verify both of their input identities.

F-A reuse entries use IDs such as
`reuse:EV-RULES-house-friction:F-A-jiangmi`. For these entries the original
runtime manifest's `identityCast` must be copied exactly. The script rejects a
blanket rewrite to Chen Xu or any other scheme-level support identity.

## Dry run

```sh
python3 media/production/gender-rotation-r6/prepare_promotion.py \
  media/production/gender-rotation-r6/visual-qa-allowlist.r6.json \
  --output /tmp/r6-promotion-plan.json
```

The output maps event candidates to
`<baseAssetId>--rotation-<schemeId>` and new portraits to
`CHAR-<characterId>-portrait`. It verifies the file hash and probes the actual
video/audio streams. It writes no runtime asset.

## Apply after review

Applying is intentionally noisy and no-overwrite. It copies reviewed bytes,
re-checks their hashes, and atomically merges the new records into
`media/runtime-media-manifest.json`. If any destination or runtime ID already
exists, the entire preflight is blocked.

```sh
python3 media/production/gender-rotation-r6/prepare_promotion.py \
  media/production/gender-rotation-r6/visual-qa-allowlist.r6.json \
  --apply --confirm PROMOTE_R6_VISUALLY_APPROVED_ASSETS
```

Do not apply until the complete visual/audio QA allowlist is retained and
reviewed. Provider success alone is not approval.
