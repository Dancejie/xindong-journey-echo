# R6 visual and audio QA report

Reviewed: 2026-08-26T07:49:52+00:00

## Verdict

- Approved runtime sources: **108** (81 generated + 3 local composites + 24 prior-approved F-A reuses).
- Generated technical QA: **81/81 passed**, with zero missing, duplicate, unexpected or technically invalid candidate files.
- Required first-play audio: **100/100 non-silent AAC**.
- Generated event audio: **73/73 non-silent AAC**; measured mean-volume range `-49.4` to `-16.6 dB`, peak range `-31.4` to `-0.1 dB`.
- Dynamic portraits: **8/8 intentionally silent** and visually identity-stable.
- Paid retries: **0**. Final settled R6 spend: **CNY 41.0770200** under the approved **CNY 60** hard cap.
- Identity hard failures after original-frame review: **0**. Two apparent duplicate-person findings were contact-sheet adjacency false positives and were withdrawn after raw-frame inspection.

## Local remediation

- `EV-SIGNAL-first-anonymous-message--F-B-luyao--r6`: Removed generated rounded app-frame border by identity-safe center crop.
- `EV-GROUP-truth-firepit--F-B-luyao--r6`: Removed large generated top/bottom UI with a clean center frame and blurred extension.
- `EV-IDENTITY-profession-reveal--M-A-chengye--r6`: Trimmed the first 0.3 s containing a transient pseudo-character card; held the clean tail to preserve duration.
- `D1-A1-island-hotel-establish--M-B-hechuan--r6`: Removed four-corner pseudo-text by cropping 32 px top/bottom and reframing.
- `EV-TRIP-last-two-days--M-B-hechuan--r6`: Removed generated 64 px white top/bottom borders with a clean center frame and blurred extension.

## Accepted non-blocking visual deviations

- `D1-A5-guided-smalltalk--F-B-luyao--r6`: An unplanned guitar remains in frame; identity and small-talk causality remain usable.
- `EV-RULES-house-friction--F-B-luyao--r6`: The rule-board movement is subtle and relies on narration.
- `EV-BRIDGE-hidden-courage--F-B-luyao--r6`: The rescue beat is readable through staging but benefits from narration.
- `EV-FINAL-confession-day--F-B-luyao--r6`: A guitar enters the confession staging; identity and emotional beat remain coherent.
- `D2-A1-memory-callback--M-A-chengye--r6`: The recalled detail is primarily conveyed by dialogue/context.
- `EV-RULES-house-friction--M-A-chengye--r6`: The rule conflict is visually understated and benefits from narration.
- `EV-BRIDGE-hidden-courage--M-A-chengye--r6`: Contains short, correct Chinese dramatic text; accepted as a non-blocking stylistic overlay.
- `EV-PAST-consent-reveal--M-A-chengye--r6`: Contains short, correct Chinese dialogue text; accepted as a non-blocking stylistic overlay.
- `EV-DATE-blind-box--M-B-hechuan--r6`: Shows about six boxes instead of three; the blind-box action remains clear.
- `EV-BOMBSHELL-ninth-card--M-B-hechuan--r6`: Envelope carries faint prop-like pseudo-text; no identity or story error.
- `EV-PAST-consent-reveal--M-B-hechuan--r6`: Old envelope carries faint prop-like pseudo-text; no identity or story error.
- `EV-FINAL-confession-day--M-B-hechuan--r6`: Contains the correct subtitle '我选你'; accepted as a non-blocking dramatic overlay.

## Honest boundary

Audio QA verifies stream presence and loudness, not a word-for-word transcription of synthetic speech. Existing F-A runtime assets are reused from the project's prior approved set; this record does not create a new commercial likeness or voice-rights claim. Public/commercial clearance remains separate from local/runtime technical approval.
