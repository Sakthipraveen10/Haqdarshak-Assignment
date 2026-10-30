"""
Deterministic checker: does the record really support this answer?  (No LLM involved.)
Fails closed: anything it cannot prove is reported as an issue.
"""
import re

from records import (LOW_CONF, SOURCES, CONFLICT_MARK, LOWCONF_MARK, NF_MARK,
                     approved_text, conf_num, field_state)

_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_STOP_EN = set("the and for you your are can this that with will not from have has may any one per its who "
               "what how when where which also then than there their they them been being was were".split())


def nums(text):
    """All numbers in text, commas removed, Devanagari digits converted: '2,50,000' -> '250000'."""
    text = text.translate(_DEVA_DIGITS)
    return {m.replace(",", "") for m in re.findall(r"\d+(?:,\d+)*", text)}


def words(text, lang):
    if lang == "en":
        toks = [t for t in re.findall(r"[a-z]+", text.lower()) if t not in _STOP_EN]
        toks = [t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t for t in toks]
        return {t for t in toks if len(t) > 2}
    toks = re.findall(r"[\u0900-\u0963\u0970-\u097F]+", text)  # excludes danda and Devanagari digits
    return {t for t in toks if len(t) > 2}


def script_ratio(text):
    deva = len(re.findall(r"[\u0900-\u097F]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return deva / (deva + latin) if (deva + latin) else 0.0


def check_faq(scheme, faq, spec=None):
    """Return a list of problems. Empty list = answer is supported by the record."""
    issues = []
    rows = scheme["rows"]
    cited = faq.get("source_fields") or []

    # 1. citation: must point to record fields (and to the fields the question is about)
    if not cited:
        return ["no source_fields: answer does not point to any record field"]
    if spec is not None:
        if set(cited) != set(spec["fields"]):
            return [f"cites {sorted(cited)} but the question is about {sorted(spec['fields'])}"]
    else:
        unknown = [f for f in cited if f not in {r["field"] for r in rows}]
        if unknown:
            return [f"cites fields that are not in the record: {unknown}"]

    q = {"en": spec["q_en"] if spec else faq["q_en"], "hi": spec["q_hi"] if spec else faq["q_hi"]}

    # 2. what SHOULD the answer look like? Decided from the record, never from the writer.
    states = {f: field_state(rows, f) for f in cited}
    kinds = [k for k, _ in states.values()]
    expected = "not found" if "not found" in kinds else "conflict" if "conflict" in kinds else "found"
    used = [r for _, rs in states.values() for r in rs]
    all_rows = [r for r in rows if r["field"] in cited]
    low_conf = expected == "found" and any(conf_num(r["confidence"]) < LOW_CONF for r in used)

    for lang in ("en", "hi"):
        text = faq.get("a_" + lang) or ""
        tag = f"[{lang}] "
        if not text.strip():
            issues.append(tag + "empty answer")
            continue
        vkey = "value" if lang == "en" else "value_hi"

        # 3. numbers: every number must come from the cited values or from the question itself
        allowed_nums = nums(q["en"] + " " + q["hi"])
        for r in all_rows:
            allowed_nums |= nums(r["value"] + " " + r["value_hi"])
        bad = nums(text) - allowed_nums
        if bad:
            issues.append(tag + f"number(s) not in the record: {sorted(bad)}")

        # 4. wording: every content word must come from cited values, the question, or approved wording
        vocab = words(approved_text(lang) + " " + q[lang], lang)
        for r in all_rows:
            vocab |= words(r[vkey] + " " + SOURCES[r["evidence"]["source"]]["label_" + lang], lang)
        extra = words(text, lang) - vocab
        if extra:
            issues.append(tag + f"words not supported by the record: {sorted(extra)}")

        # 5. shape of the answer must match the record's status
        if expected == "not found":
            if NF_MARK[lang] not in text:
                issues.append(tag + "record has no answer, but the answer does not say so")
        elif expected == "conflict":
            if CONFLICT_MARK[lang] not in text:
                issues.append(tag + "sources conflict, but the answer does not say so")
            for r in used:
                if r[vkey] not in text:
                    issues.append(tag + f"conflicting value missing from answer: {r[vkey]!r}")
                lab = SOURCES[r["evidence"]["source"]]["label_" + lang]
                if lab not in text:
                    issues.append(tag + f"source of a conflicting value missing: {lab!r}")
        else:
            for r in used:
                if r[vkey].lower() not in text.lower():
                    issues.append(tag + f"answer does not contain the record value {r[vkey]!r}")
            if low_conf and LOWCONF_MARK[lang] not in text:
                issues.append(tag + "low-confidence field but no caution in the answer")

    # 6. Hindi must really be Hindi, and say the same numbers as English
    hi = faq.get("a_hi") or ""
    if hi.strip() and script_ratio(hi) < 0.6:
        issues.append("[hi] answer is mostly not in Devanagari script")
    if (faq.get("a_en") or "").strip() and hi.strip() and nums(faq["a_en"]) != nums(hi):
        issues.append(f"English and Hindi answers have different numbers: "
                      f"{sorted(nums(faq['a_en']))} vs {sorted(nums(hi))}")
    return issues
