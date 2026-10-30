"""
Citizen FAQ generator - answers ONLY from the approved scheme record.

    python faq.py            # offline: deterministic template writer (no API key)
    python faq.py --llm      # Claude writes the answers; checker still gates every one
Output: printed FAQs + faqs.json
"""
import json
import os
import sys

from checker import check_faq
from records import (ACCORDING, CONFLICT_ASK, CONFLICT_INTRO, LOW_CONF, LOWCONF, NF_EN, NF_HI,
                     SCHEMES, SOURCES, conf_num, field_state, fill, specs_for)


# ----------------------------------------------------------------------------
# Building one FAQ entry
# ----------------------------------------------------------------------------
def build_faq(scheme, spec, a_en, a_hi, writer):
    sources = [{"field": r["field"], "source": r["evidence"]["source"], "location": r["evidence"]["location"],
                "link": r["evidence"]["source_link"], "evidence_text": r["evidence"]["text"]}
               for f in spec["fields"] for r in scheme["rows"] if r["field"] == f]
    return {"id": spec["id"], "scheme_ref": scheme["ref"], "q_en": spec["q_en"], "q_hi": spec["q_hi"],
            "a_en": a_en, "a_hi": a_hi, "source_fields": list(spec["fields"]),
            "sources": sources, "writer": writer}


# ----------------------------------------------------------------------------
# Writer 1: deterministic templates (safe default, works offline)
# ----------------------------------------------------------------------------
def template_writer(scheme, spec, feedback=None):
    states = {f: field_state(scheme["rows"], f) for f in spec["fields"]}
    kinds = [k for k, _ in states.values()]

    if "not found" in kinds:  # record has no answer -> say so, never guess
        return build_faq(scheme, spec, NF_EN, NF_HI, "template")

    if "conflict" in kinds:  # keep every value + its source
        en, hi = [CONFLICT_INTRO["en"]], [CONFLICT_INTRO["hi"]]
        for kind, rows in states.values():
            if kind != "conflict":
                continue
            for r in rows:
                lab = SOURCES[r["evidence"]["source"]]
                en.append(ACCORDING["en"].format(label=lab["label_en"], value=r["value"]))
                hi.append(ACCORDING["hi"].format(label=lab["label_hi"], value=r["value_hi"]))
        en.append(CONFLICT_ASK["en"])
        hi.append(CONFLICT_ASK["hi"])
        return build_faq(scheme, spec, " ".join(en), " ".join(hi), "template")

    used = {f: rows[0] for f, (_, rows) in states.items()}
    a_en = fill(spec["a_en"], {f: r["value"] for f, r in used.items()})
    a_hi = fill(spec["a_hi"], {f: r["value_hi"] for f, r in used.items()})
    if any(conf_num(r["confidence"]) < LOW_CONF for r in used.values()):
        a_en, a_hi = a_en + " " + LOWCONF["en"], a_hi + " " + LOWCONF["hi"]
    return build_faq(scheme, spec, a_en, a_hi, "template")


# ----------------------------------------------------------------------------
# Writer 2: Claude (only sees the cited rows, never the whole internet / its memory)
# ----------------------------------------------------------------------------
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

LLM_SYSTEM = f"""You write FAQ answers for citizens (many have low literacy). Use ONLY the record rows given.
Rules:
- Short sentences, simple words. Write English and Hindi (Devanagari). Keep every number as digits.
- Copy each record value EXACTLY (value for English, value_hi for Hindi). Do not add facts, tips or numbers.
- If a field's status is "not found": answer exactly: EN: {NF_EN}  HI: {NF_HI}
- If status is "conflict": say the sources disagree, give EVERY value with its source label, and ask the
  user to confirm with the scheme office. Never pick one.
- If a found value has confidence below {LOW_CONF}, add a note asking the user to confirm with the scheme office.
Return ONLY JSON: {{"answer_en": "...", "answer_hi": "..."}}"""


def llm_writer(scheme, spec, feedback=None):
    import anthropic
    rows = []
    for f in spec["fields"]:
        rf = [r for r in scheme["rows"] if r["field"] == f]
        if not rf:
            rows.append({"field": f, "status": "not found"})
        for r in rf:
            lab = SOURCES[r["evidence"]["source"]]
            rows.append({"field": f, "status": r["status"], "value": r["value"], "value_hi": r["value_hi"],
                         "evidence_text": r["evidence"]["text"], "source_label_en": lab["label_en"],
                         "source_label_hi": lab["label_hi"], "confidence": r["confidence"]})
    payload = {"question_en": spec["q_en"], "question_hi": spec["q_hi"], "record_rows": rows}
    if feedback:
        payload["previous_attempt_problems"] = feedback
    resp = anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=600, system=LLM_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    try:
        raw = resp.content[0].text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return build_faq(scheme, spec, str(data["answer_en"]), str(data["answer_hi"]), "llm")
    except Exception:  # unparsable -> empty answer -> checker fails it -> fallback
        return build_faq(scheme, spec, "", "", "llm")


# ----------------------------------------------------------------------------
# Pipeline: write -> check -> (retry once with feedback) -> fall back to template
# ----------------------------------------------------------------------------
def generate_faqs(scheme, writer=template_writer, retries=1):
    out = []
    for spec in specs_for(scheme["ref"]):
        faq, feedback, issues = None, None, []
        for _ in range(retries + 1):
            cand = writer(scheme, spec, feedback)
            issues = check_faq(scheme, cand, spec)
            if not issues:
                faq = cand
                break
            feedback = issues
        if faq is None:  # never ship an answer that failed the check
            faq = template_writer(scheme, spec)
            faq["writer"] = f"template (fallback after {writer.__name__} failed the check)"
            faq["rejected_because"] = issues
            assert not check_faq(scheme, faq, spec), "template answer must always pass the checker"
        faq["checker"] = "passed"
        out.append(faq)
    return out


def main():
    writer = llm_writer if "--llm" in sys.argv else template_writer
    result = {}
    for ref, scheme in SCHEMES.items():
        faqs = generate_faqs(scheme, writer)
        result[ref] = faqs
        print(f"\n{'=' * 78}\n{ref}  {scheme['name']}  ({len(faqs)} FAQs, all checked)\n{'=' * 78}")
        for i, f in enumerate(faqs, 1):
            print(f"\nQ{i}. {f['q_en']}\n    {f['q_hi']}")
            print(f"  A (EN): {f['a_en']}\n  A (HI): {f['a_hi']}")
            print(f"  source_fields: {f['source_fields']}  | writer: {f['writer']}")
    with open("faqs.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print("\nSaved faqs.json")


if __name__ == "__main__":
    main()
