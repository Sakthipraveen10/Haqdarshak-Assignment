# A3 · Citizen FAQ generator: walkthrough

## What I built (one paragraph)
Two synthetic scheme records in the brief's field format → 10 FAQs per scheme in English and Hindi (20 FAQs, 40 answers) → every answer carries `source_fields` plus the evidence rows it came from → a deterministic checker blocks any answer the record does not support. If the record has no answer, the FAQ says so. If sources conflict, the FAQ shows every value and its source.

**Design idea: the writer can be an LLM, but the checker is plain code.** A confident wrong answer can cost a family a benefit, so no answer reaches a citizen unless the checker has proved it from the record. Pipeline: `write → check → retry once with the checker's complaints → fall back to a fixed template`.

## Run it
```
python faq.py          # offline, deterministic writer, writes faqs.json
python faq.py --llm    # Claude writes the answers (needs ANTHROPIC_API_KEY); same checker gates them
python test_faq.py     # 21 tests, no API key needed
```
Files: `records.py` (data + approved wording), `faq.py` (writers + pipeline), `checker.py`, `test_faq.py`.

## Sample data: tricky cases on purpose
| Case | Where | What the FAQ does |
|---|---|---|
| Field not in record | SCH-001 `helpline`, `late_application_rule`; SCH-002 `application_fee` | "Not in our approved record, ask the scheme office." No guess. |
| Sources conflict | SCH-001 `deadline` (official PDF 31 Mar 2027 vs news 30 Apr 2027) | Shows both values with their sources, asks user to confirm. |
| Low confidence | SCH-002 `eligibility_income_limit` (poor OCR, 0.6) | Gives the value plus "please confirm" caution. |
| "Am I eligible if…" | Both schemes | Compares user's number with the record's limit, says "check with office if unsure". |

## What the checker verifies (`checker.py`)
1. **Citation:** `source_fields` exists and matches the field(s) the question is about.
2. **Numbers:** every number in the answer appears in the cited values or in the question itself.
3. **Wording:** every content word comes from the cited values, the question, or approved wording. This catches an invented "ration card".
4. **Shape matches the record's status** (decided from the record, not from the writer): not found → must say so, conflict → must contain every value and source, found → must contain the exact value, low confidence → must carry the caution.
5. **Hindi:** mostly Devanagari script, and the same numbers as the English answer.

21 tests include wrong amount, invented document (EN and HI), guessed helpline, conflict answered with one date, dropped eligibility condition, Hindi number mismatch, Hindi written in English, and a "liar" writer that is forced back to the template.

## Assumptions (and why)
- **Scheme and numbers are invented.** No real scheme or real phone number (`1800-000-0000` is a placeholder).
- **I added `value_hi`** (Hindi rendering of each value) and a human-readable **source label**. The brief's format has no Hindi slot, and conflict answers need to name their sources.
- **The record is already approved and correct.** FAQs are only as good as the record. Extraction mistakes upstream are out of scope here.
- **Numbers are kept as ASCII digits in Hindi** (₹6,000, not ६,०००). Easier to verify automatically, and common in Indian government text.
- **Low confidence = below 0.7.** Arbitrary threshold; a real team should tune it.
- **"Eligible if…" answers only compare against a stated limit** and always tell the user to confirm if unsure. They never promise eligibility.

## How I used AI
Claude (Anthropic) wrote the first version of the code, the sample records, and the Hindi wording; I reviewed the design and ran the tests. *(Edit this paragraph so it describes what you personally did and changed.)*
Model for the optional `--llm` writer: `claude-haiku-5-5`, chosen because the task is short and structured. **I have not run `--llm` live**: my build environment had no network. Only the offline path and the pipeline logic (with fake writers) are tested.

## Q1. How did I check the Hindi, given I am not fluent?
Honest answer first: **the Hindi was drafted by an AI and has not been reviewed by a native speaker.** What I did instead:
- **Fixed, reviewable wording.** Hindi comes from short templates plus one `value_hi` per field, so a Hindi reviewer reads about 30 short lines, not every generated answer.
- **Automatic checks that need no Hindi:** the same numbers as English, Devanagari script, every word from approved vocabulary, Hindi value numbers equal English value numbers (tested).
- **Not done, but proposed:** (a) back-translate Hindi → English with an LLM and compare to the original, (b) a native-speaker review of the template file before launch, then spot-checks on a sample of generated answers, (c) test with real users from the target group.
- **Known weakness:** my checks prove the facts match, not that the Hindi is natural. Words such as "बोनाफाइड प्रमाण पत्र" may not be what people actually say.

## Q2. Accurate but hard to follow for someone with low literacy: how do I balance?
Accuracy is the floor, clarity is what I optimise above it. I never trade away a fact, a number or a condition, and I trade away everything else.
- **Short sentences, everyday words, one idea per answer.** Lead with the answer, then the one condition that matters ("below ₹2,50,000 per year").
- **Never simplify by deleting a condition.** "Girls in classes 9 to 12 are eligible" is clearer but wrong. My checker has a test that fails exactly this edit.
- **Keep numbers exactly as in the record,** written as digits.
- **Say what to do next** ("ask the scheme office") instead of leaving the person stuck.
- **Beyond text:** voice read-out, icons, and an agent-assisted mode, because text may not reach everyone. I did not build these.
- **Measure it:** test with real low-literacy users (can they say back what they must do?) rather than trusting a readability score.

## Cost per scheme (if `--llm` is used)
Model: `claude-haiku-5-5`. **My token numbers are estimates, not measurements.**
- Per FAQ call ≈ 450 input tokens (instructions + cited rows) and ≈ 250 output tokens (English + Hindi; Hindi uses more tokens per word).
- 10 FAQs ≈ 4,500 in / 2,500 out. With ~20% retries ≈ **5,400 input + 3,000 output tokens per scheme**.
- **Cost = 5,400 × (input price per token) + 3,000 × (output price per token).** Fill the prices from Anthropic's current pricing page; I have not looked them up. For Haiku-class models this is a small fraction of a currency unit per scheme, but check the real numbers.
- The offline template writer costs nothing.

## What I do not know / limits
- Hindi quality is unverified by a human (above).
- `--llm` is untested live. The checker is strict (exact values, approved vocabulary), so a real model will sometimes be rejected and fall back to the template. That is deliberate. The cost is more rejected answers, and the fallback answers are plainer.
- The vocabulary check compares words, not meaning. A sentence made only of approved words could still be wrong in a way I did not think of. The exact-value and number checks reduce that risk but do not remove it.
- English word matching strips plurals naively; Hindi has no stemming, so inflected forms from an LLM will be flagged.
- Records are small and invented. Real documents will have messier fields (ranges, exceptions, state-wise differences).
- Some answers repeat the "confirm with the scheme office" line twice (the scenario answer plus the low-confidence note). Harmless but could be tidier.
