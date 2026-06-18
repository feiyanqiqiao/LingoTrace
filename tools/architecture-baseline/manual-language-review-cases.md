# Manual Japanese Language Review Cases

These Phase 0 PR B cases cover judgment that should not be faked by deterministic tests. All inputs are synthetic public examples.

## Case MLR-001: Common Sentence Reuse Value

- Behavior IDs: `JP-LISTEN-006`, `JP-SPEAK-001`
- Input: `駅まで歩いて行けます。`
- Accept when: the sentence is natural, reusable in daily life, and can be practiced without extra context.
- Reject when: the sentence is generic filler, depends on an omitted situation, or contains unresolved ASR noise.
- Review gate: PR reviewers must comment if the acceptance criteria do not represent current Japanese workflow expectations.

## Case MLR-002: Politeness And Register

- Behavior IDs: `JP-SPEAK-003`, `JP-SPEAK-004`
- Input: `予約しています。山田です。`
- Accept when: the expression is polite enough for a restaurant check-in and the role is clearly customer-facing.
- Reject when: the register is too casual, the speaker role is ambiguous, or the card would teach an unnatural fixed phrase.
- Review gate: PR reviewers must comment if the acceptance criteria do not represent current Japanese workflow expectations.

## Case MLR-003: Transcript Suitability For Memorization

- Behavior IDs: `JP-LISTEN-004`, `JP-LISTEN-007`
- Input: a synthetic transcript with overlapping timestamps and unclear speaker turns.
- Accept when: a reviewed slice manifest resolves order, timing, and grouping before the note is marked complete.
- Reject when: slice files are fabricated, timestamps are guessed, or ambiguous speaker identity is invented.
- Review gate: PR reviewers must comment if the acceptance criteria do not represent current Japanese workflow expectations.

## Case MLR-004: Grammar Explanation Naturalness

- Behavior IDs: `JP-REVIEW-005`, `JP-REVIEW-007`
- Input: a synthetic grammar card for `てもいいです`.
- Accept when: the explanation is accurate, concise, and shows a usable example.
- Reject when: the explanation overgeneralizes, misses connection rules, or routes the material into vocabulary storage.
- Review gate: PR reviewers must comment if the acceptance criteria do not represent current Japanese workflow expectations.
