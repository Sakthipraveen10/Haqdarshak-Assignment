"""python test_faq.py  - no API key needed."""
import copy
import re

from checker import check_faq
from faq import build_faq, generate_faqs, template_writer
from records import SCHEMES, SHARED_SPECS, field_state, specs_for

S1, S2 = SCHEMES["SCH-001"], SCHEMES["SCH-002"]


def spec(ref, fid):
    return next(s for s in specs_for(ref) if s["id"] == fid)


def make(scheme, fid):
    sp = spec(scheme["ref"], fid)
    return sp, template_writer(scheme, sp)


def caught(scheme, fid, mutate):
    """Apply a wrong edit to a good FAQ -> checker must report at least one issue."""
    sp, faq = make(scheme, fid)
    assert check_faq(scheme, faq, sp) == [], "starting FAQ should be clean"
    bad = copy.deepcopy(faq)
    mutate(bad)
    return check_faq(scheme, bad, sp)


# ---------------------------------------------------------------- the good path
def test_each_scheme_has_10_faqs_in_both_languages():
    for s in (S1, S2):
        faqs = generate_faqs(s)
        assert len(faqs) == 10
        assert all(f["a_en"].strip() and f["a_hi"].strip() and f["source_fields"] for f in faqs)


def test_all_generated_faqs_pass_checker():
    for s in (S1, S2):
        for f in generate_faqs(s):
            assert check_faq(s, f, spec(s["ref"], f["id"])) == [], (s["ref"], f["id"])


def test_not_found_says_so_and_has_no_numbers():
    _, f = make(S1, "helpline")  # no helpline in record
    assert "not in our approved record" in f["a_en"] and "स्वीकृत रिकॉर्ड में नहीं है" in f["a_hi"]
    assert not re.search(r"\d", f["a_en"] + f["a_hi"])


def test_conflict_keeps_both_values_and_sources():
    _, f = make(S1, "deadline")
    for v in ("31 March 2027", "30 April 2027", "the official guideline PDF", "a news article"):
        assert v in f["a_en"]
    for v in ("31 मार्च 2027", "30 अप्रैल 2027"):
        assert v in f["a_hi"]


def test_low_confidence_gets_caution():
    _, f = make(S2, "eligibility")
    assert "hard to read" in f["a_en"] and "स्पष्ट नहीं थी" in f["a_hi"]


def test_field_missing_from_record_is_not_found_not_a_guess():
    s = copy.deepcopy(S2)
    s["rows"] = [r for r in s["rows"] if r["field"] != "benefit_amount"]
    sp = spec("SCH-002", "benefit")
    f = template_writer(s, sp)
    assert "not in our approved record" in f["a_en"]
    assert check_faq(s, f, sp) == []


# ---------------------------------------------------------------- the checker catches wrong answers
def test_catches_wrong_amount():
    assert caught(S1, "benefit", lambda f: f.update(a_en=f["a_en"].replace("6,000", "10,000")))


def test_catches_invented_document():
    assert caught(S1, "documents", lambda f: f.update(a_en=f["a_en"][:-1] + ", ration card."))


def test_catches_invented_document_in_hindi():
    assert caught(S1, "documents", lambda f: f.update(a_hi=f["a_hi"][:-1] + ", राशन कार्ड।"))


def test_catches_guessed_helpline_when_record_has_none():
    assert caught(S1, "helpline", lambda f: f.update(
        a_en="Yes. The helpline number is 1800-123-4567.", a_hi="हाँ, हेल्पलाइन नंबर 1800-123-4567 है।"))


def test_catches_silent_guess_for_missing_late_rule():
    assert caught(S1, "late", lambda f: f.update(
        a_en="Late applications are accepted with a penalty.",
        a_hi="देर से किए गए आवेदन जुर्माने के साथ स्वीकार किए जाते हैं।"))


def test_catches_conflict_answered_with_one_date():
    assert caught(S1, "deadline", lambda f: f.update(
        a_en="The last date to apply is 30 April 2027.", a_hi="आवेदन की अंतिम तारीख 30 अप्रैल 2027 है।"))


def test_catches_missing_source_fields():
    assert caught(S1, "benefit", lambda f: f.update(source_fields=[]))


def test_catches_wrong_source_field():
    assert caught(S1, "benefit", lambda f: f.update(source_fields=["documents_required"]))


def test_catches_hindi_number_different_from_english():
    assert caught(S2, "benefit", lambda f: f.update(a_hi=f["a_hi"].replace("12,000", "21,000")))


def test_catches_hindi_answer_written_in_english():
    assert caught(S2, "fee", lambda f: f.update(a_hi="This information is not in our approved record."))


def test_catches_missing_low_confidence_caution():
    def strip(f):
        f["a_en"] = f["a_en"].split(" Note:")[0]
        f["a_hi"] = f["a_hi"].split(" ध्यान दें:")[0]
    assert caught(S2, "eligibility", strip)


def test_catches_dropped_condition():
    # "simplifying" away the income condition is an accuracy loss
    assert caught(S2, "eligibility", lambda f: f.update(
        a_en="Girl students studying in classes 9 to 12 are eligible.",
        a_hi="कक्षा 9 से 12 में पढ़ने वाली छात्राएँ पात्र हैं।"))


# ---------------------------------------------------------------- pipeline never ships a bad answer
def test_bad_writer_falls_back_to_checked_template():
    def liar(scheme, sp, feedback=None):  # always invents an amount
        return build_faq(scheme, sp, "You get ₹99,999.", "आपको ₹99,999 मिलेंगे।", "liar")
    faqs = generate_faqs(S1, liar)
    assert len(faqs) == 10
    assert all("fallback" in f["writer"] and f["rejected_because"] for f in faqs)
    assert all(check_faq(S1, f, spec("SCH-001", f["id"])) == [] for f in faqs)


def test_writer_gets_feedback_and_can_recover():
    calls = []

    def learner(scheme, sp, feedback=None):
        calls.append(feedback)
        if feedback is None:
            return build_faq(scheme, sp, "wrong", "गलत", "learner")
        return template_writer(scheme, sp)
    generate_faqs(S2, learner, retries=1)
    assert calls[0] is None and calls[1]  # 2nd call received the checker's complaints


# ---------------------------------------------------------------- data sanity (Hindi values)
def test_hindi_values_have_same_numbers_as_english_values():
    from checker import nums
    for s in (S1, S2):
        for r in s["rows"]:
            assert nums(r["value"]) == nums(r["value_hi"]), (r["field"], r["value"], r["value_hi"])


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print("PASS", name)
    print(f"\n{len(tests)}/{len(tests)} passed")
