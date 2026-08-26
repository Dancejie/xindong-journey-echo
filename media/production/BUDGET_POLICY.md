# External generation budget policy

Effective 2026-08-25 for this project and its future media batches:

- Reuse an existing generated asset whenever it already satisfies the event, identity, audio, framing and rights contract.
- Every manifest must report the project's cumulative external-generation spend before the batch, the incremental estimate for the batch, and the projected cumulative total.
- **CNY 200 is the manual-review threshold.** If either the batch estimate or projected project total exceeds CNY 200, execution must stop until a human gives a fresh approval that explicitly names the maximum CNY amount.
- A general request such as “generate the videos” is not an over-threshold budget approval.
- Automatic paid retries are disabled. Any paid retry requires a new approval and its own maximum amount.
- Provider success creates a candidate only; failed identity, speech, continuity or runtime QA does not authorize an automatic regeneration.
