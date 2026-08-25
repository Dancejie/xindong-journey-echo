# Heart Journey R5 identity-safe media QA

Date: 2026-08-25

## Acceptance target

- The selected protagonist must never be replaced by Jiangmi or another cast member in an event clip.
- A committed event may use a generated master only when its reviewed `identityCast` exactly matches the runtime routing contract.
- Missing exact variants must degrade to the correct protagonist or participant dynamic portrait.
- First face appearance receives a Chinese HTML identity plate with name, confirmed occupation or `职业待公开`, MBTI and trait; it fades after about three seconds and does not replay on a looping background.
- Character-choice photos remain secondary to readable identity and action copy.

## Runtime routing

The backend owns the final media decision. It resolves one of five semantic modes:

1. `perspective`: selected protagonist only, `{base}--p-{protagonist}`.
2. `participant-pov`: active NPC on camera, `{base}--npc-{participant}`.
3. `unordered-pair`: exact protagonist/participant pair, `{base}--pair-{canonicalA}-{canonicalB}`.
4. `fixed-cast`: exact authored cast, `{base}--fixed-{ids}`.
5. `current-eight`: exact current cast, `{base}--group-current-eight`.

Story kitchen work reuses the Day 1 dinner-team pair family, and the first anonymous-message beat reuses the Day 1 heart-message perspective family. This avoids duplicate provider work while preserving exact identity validation.

## Corrected legacy evidence

`D1-A3B-cast-first-impressions` was visually re-reviewed as a six-person montage, not an eight-person montage. The manifest now records only Shenmo, Guyan, Jiangwan, Sunnian, Chensu and Jiangmi with their reviewed time ranges. The asset is therefore rejected for the `current-eight` route until a real eight-person master is approved.

The legacy Jiangmi `D1-A3-cast-introductions` audio was also checked against its detailed R4 report: it contains no intelligible dialogue and therefore cannot satisfy the new voiced Agent self-introduction contract. It is held out of R5 runtime routing; all eight self-introductions require generation.

## Local verification

- Python backend suite: 62 tests passed.
- TypeScript: `tsc --noEmit` passed.
- Production frontend: Vite build passed.
- Mobile UI: 390x844, 390x720 and 390x620 checks passed without horizontal overflow or action obstruction.
- Browser loop check: an identity plate appeared on the first pass and remained absent after the video wrapped.
- API smoke: Shenmo and Linyu routes returned their own portrait assets when exact event variants were unavailable; Jiangmi-only footage was not substituted.
- Manifest JSON, batch-gate Python compilation, Zsh syntax and `git diff --check` passed.

## Generation boundary

The complete semantic runtime requires 188 unique event masters. Strict identity-and-content review leaves 10 reusable masters and 178 generation gaps. The authoritative list is `media/production/cast-perspective-r5/runtime-variant-matrix.json`.

The paid Seedance gate is intentionally fail closed. No provider task has been submitted because the model endpoint exposes no price and no approved unit price/hard total budget has been recorded. Transport success will not be treated as visual, identity, audio or runtime approval.
