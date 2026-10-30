"""
Synthetic scheme records (field format from the brief) + approved FAQ wording.
Everything here is made up. No real scheme, no real phone number.

Extra keys I added to the brief's format (flagged in WALKTHROUGH.md):
  value_hi              reviewed Hindi rendering of `value` (the brief has no Hindi slot)
  source label (below)  a human name for each source, used when sources conflict
"""
import re

CAPTURED = "2026-10-30"

SOURCES = {
    "SRC_K1": {"link": "synthetic://kisan-sahayata/guidelines.pdf",
               "label_en": "the official guideline PDF", "label_hi": "आधिकारिक दिशानिर्देश PDF"},
    "SRC_K2": {"link": "synthetic://news/kisan-deadline-extended",
               "label_en": "a news article", "label_hi": "एक समाचार लेख"},
    "SRC_B1": {"link": "synthetic://beti-chhatravritti/guidelines.pdf",
               "label_en": "the official guideline PDF", "label_hi": "आधिकारिक दिशानिर्देश PDF"},
}


# ---------------------------------------------------------------- row builders
def _row(ref, field, value, value_hi, text, loc, src, conf, status, note):
    return {"scheme_ref": ref, "field": field, "value": value, "value_hi": value_hi,
            "evidence": {"text": text, "location": loc, "source": src,
                         "source_link": SOURCES[src]["link"], "captured": CAPTURED},
            "confidence": conf, "status": status, "note": note}


def found(ref, field, value, value_hi, text, loc, src, conf, note=""):
    return _row(ref, field, value, value_hi, text, loc, src, conf, "found", note)


def conflict(ref, field, value, value_hi, text, loc, src, conf, note=""):
    return _row(ref, field, value, value_hi, text, loc, src, conf, "conflict", note)


def missing(ref, field, src, note):
    return _row(ref, field, "", "", "", "whole document searched", src, 0.8, "not found", note)


# ---------------------------------------------------------------- scheme 1
K = "SCH-001"
SCHEME_1 = {"ref": K, "name": "Kisan Sahayata Yojana (synthetic)", "rows": [
    found(K, "benefit_amount", "₹6,000 per year", "प्रति वर्ष ₹6,000",
          "Eligible farmer families receive financial help of ₹6,000 per year.", "p.1, section 2", "SRC_K1", 0.95),
    found(K, "payment_frequency", "3 instalments of ₹2,000, one every 4 months",
          "3 किस्तों में, हर किस्त ₹2,000 की, हर 4 महीने में एक",
          "The amount is paid in three equal instalments of ₹2,000 every four months.", "p.2, section 3", "SRC_K1", 0.9),
    found(K, "eligibility_land_limit", "land up to 2 hectares", "2 हेक्टेयर तक की ज़मीन",
          "Farmers owning cultivable land up to 2 hectares are eligible.", "p.1, section 3", "SRC_K1", 0.9),
    found(K, "documents_required", "Aadhaar card, land ownership papers, bank passbook",
          "आधार कार्ड, ज़मीन के स्वामित्व के कागज़ात, बैंक पासबुक",
          "Applicants must submit: Aadhaar card, land ownership papers and bank passbook.", "p.3, section 5", "SRC_K1", 0.95),
    # two sources disagree on the deadline -> keep BOTH, status = conflict
    conflict(K, "deadline", "31 March 2027", "31 मार्च 2027",
             "Applications are accepted until 31 March 2027.", "p.1, section 4", "SRC_K1", 0.9,
             "Official PDF and news article disagree; the news article may be newer."),
    conflict(K, "deadline", "30 April 2027", "30 अप्रैल 2027",
             "The last date to apply has been extended to 30 April 2027, officials said.", "paragraph 2", "SRC_K2", 0.6,
             "News report only; not confirmed in an official document."),
    found(K, "how_to_apply", "at your Block Office or on the scheme's online portal",
          "अपने ब्लॉक कार्यालय में या योजना के ऑनलाइन पोर्टल पर",
          "Applications can be submitted at the Block Office or through the online portal.", "p.3, section 6", "SRC_K1", 0.9),
    missing(K, "helpline", "SRC_K1", "No helpline number anywhere in the guideline PDF."),
    found(K, "application_fee", "none (free of charge)", "कोई नहीं (निःशुल्क)",
          "No fee is charged for applying.", "p.3, section 6", "SRC_K1", 0.9),
    missing(K, "late_application_rule", "SRC_K1", "Document says nothing about late applications."),
]}

# ---------------------------------------------------------------- scheme 2
B = "SCH-002"
SCHEME_2 = {"ref": B, "name": "Beti Padhao Chhatravritti (synthetic)", "rows": [
    found(B, "benefit_amount", "₹12,000 per year", "प्रति वर्ष ₹12,000",
          "A scholarship of ₹12,000 per year is given to each selected student.", "p.1, section 2", "SRC_B1", 0.95),
    found(B, "payment_frequency", "one instalment per year", "साल में एक किस्त",
          "The scholarship is paid once a year.", "p.2, section 4", "SRC_B1", 0.9),
    found(B, "eligibility_class", "classes 9 to 12", "कक्षा 9 से 12",
          "Girl students studying in Classes 9 to 12 may apply.", "p.1, section 3", "SRC_B1", 0.95),
    found(B, "eligibility_income_limit", "below ₹2,50,000 per year", "₹2,50,000 प्रति वर्ष से कम",
          "[OCR] Annual family income should be below Rs 2,50,000", "p.2, table 1", "SRC_B1", 0.6,
          "Read from a scanned table; OCR quality is poor, so confidence is low."),
    found(B, "documents_required", "Aadhaar card, income certificate, school bonafide certificate",
          "आधार कार्ड, आय प्रमाण पत्र, स्कूल का बोनाफाइड प्रमाण पत्र",
          "Documents: Aadhaar card, income certificate, school bonafide certificate.", "p.3, section 5", "SRC_B1", 0.95),
    found(B, "deadline", "31 December 2026", "31 दिसंबर 2026",
          "The last date to apply is 31 December 2026.", "p.1, section 4", "SRC_B1", 0.9),
    found(B, "how_to_apply", "through your school", "अपने स्कूल के माध्यम से",
          "Students apply through their school.", "p.3, section 6", "SRC_B1", 0.9),
    found(B, "helpline", "1800-000-0000", "1800-000-0000",
          "For help call the toll-free helpline 1800-000-0000.", "p.4", "SRC_B1", 0.9,
          "Placeholder number (synthetic data)."),
    missing(B, "application_fee", "SRC_B1", "Document does not say whether a fee is charged."),
    found(B, "late_application_rule", "Applications received after the last date are not accepted.",
          "अंतिम तारीख के बाद मिले आवेदन स्वीकार नहीं किए जाते।",
          "Applications received after the last date will not be accepted.", "p.1, section 4", "SRC_B1", 0.9),
]}

SCHEMES = {K: SCHEME_1, B: SCHEME_2}

# ---------------------------------------------------------------- record helpers
LOW_CONF = 0.7
_CONF_WORDS = {"high": 0.9, "medium": 0.6, "low": 0.3}


def conf_num(c):
    return _CONF_WORDS.get(c, 0.0) if isinstance(c, str) else float(c)


def field_state(rows, field):
    """-> ('found' | 'not found' | 'conflict', rows to use). The ONLY place that decides this."""
    rf = [r for r in rows if r["field"] == field]
    if not rf:
        return "not found", []
    if any(r["status"] == "conflict" for r in rf):
        return "conflict", [r for r in rf if r["status"] == "conflict"]
    ok = [r for r in rf if r["status"] == "found" and r["value"].strip()]
    if not ok:
        return "not found", []
    return "found", ok[:1]


# ---------------------------------------------------------------- approved wording
NF_EN = "This information is not in our approved record, so we cannot answer it. Please ask the scheme office."
NF_HI = "यह जानकारी हमारे स्वीकृत रिकॉर्ड में नहीं है, इसलिए हम इसका उत्तर नहीं दे सकते। कृपया योजना कार्यालय से पूछें।"
NF_MARK = {"en": "not in our approved record", "hi": "स्वीकृत रिकॉर्ड में नहीं है"}

CONFLICT_INTRO = {"en": "Our sources disagree on this.", "hi": "इस बारे में हमारे स्रोतों में अलग-अलग जानकारी है।"}
CONFLICT_ASK = {"en": "Please confirm with the scheme office before relying on either.",
                "hi": "किसी एक पर भरोसा करने से पहले कृपया योजना कार्यालय से पुष्टि करें।"}
CONFLICT_MARK = {"en": "sources disagree", "hi": "अलग-अलग जानकारी"}
ACCORDING = {"en": "According to {label}: {value}.", "hi": "{label} के अनुसार: {value}।"}

LOWCONF = {"en": "Note: this detail was hard to read in the source, so please confirm it with the scheme office.",
           "hi": "ध्यान दें: स्रोत में यह जानकारी स्पष्ट नहीं थी, इसलिए कृपया योजना कार्यालय से पुष्टि कर लें।"}
LOWCONF_MARK = {"en": "hard to read", "hi": "स्पष्ट नहीं थी"}

# ---------------------------------------------------------------- FAQ specs
# a_en / a_hi use {field} placeholders; English fills `value`, Hindi fills `value_hi`.
SHARED_SPECS = [
    dict(id="benefit", fields=["benefit_amount"],
         q_en="How much money or benefit does this scheme give?",
         q_hi="इस योजना में कितनी राशि या लाभ मिलता है?",
         a_en="The scheme gives {benefit_amount}.",
         a_hi="इस योजना में {benefit_amount} मिलता है।"),
    dict(id="payment", fields=["payment_frequency"],
         q_en="When is the money paid?", q_hi="पैसा कब मिलता है?",
         a_en="Payment works like this: {payment_frequency}.",
         a_hi="भुगतान इस तरह होता है: {payment_frequency}।"),
    dict(id="documents", fields=["documents_required"],
         q_en="What documents do I need?", q_hi="मुझे कौन-से दस्तावेज़ चाहिए?",
         a_en="You need: {documents_required}.",
         a_hi="आपको ये दस्तावेज़ चाहिए: {documents_required}।"),
    dict(id="deadline", fields=["deadline"],
         q_en="What is the last date to apply?", q_hi="आवेदन की अंतिम तारीख क्या है?",
         a_en="The last date to apply is {deadline}.",
         a_hi="आवेदन की अंतिम तारीख {deadline} है।"),
    dict(id="how_to_apply", fields=["how_to_apply"],
         q_en="How do I apply?", q_hi="मैं आवेदन कैसे करूँ?",
         a_en="You can apply {how_to_apply}.",
         a_hi="आप {how_to_apply} आवेदन कर सकते हैं।"),
    dict(id="helpline", fields=["helpline"],
         q_en="Is there a helpline I can call?",
         q_hi="क्या कोई हेल्पलाइन नंबर है जिस पर मैं कॉल कर सकूँ?",
         a_en="Yes. The helpline number is {helpline}.",
         a_hi="हाँ, हेल्पलाइन नंबर {helpline} है।"),
    dict(id="fee", fields=["application_fee"],
         q_en="Do I have to pay a fee to apply?",
         q_hi="क्या आवेदन करने के लिए शुल्क देना पड़ता है?",
         a_en="Application fee: {application_fee}.",
         a_hi="आवेदन शुल्क: {application_fee}।"),
    dict(id="late", fields=["late_application_rule"],
         q_en="What happens if I apply after the last date?",
         q_hi="अंतिम तारीख के बाद आवेदन करूँ तो क्या होगा?",
         a_en="{late_application_rule}",
         a_hi="{late_application_rule}"),
]

SPECIFIC_SPECS = {
    "SCH-001": [
        dict(id="eligibility", fields=["eligibility_land_limit"],
             q_en="Who is eligible for this scheme?", q_hi="इस योजना के लिए कौन पात्र है?",
             a_en="Farmers with {eligibility_land_limit} are eligible.",
             a_hi="{eligibility_land_limit} वाले किसान पात्र हैं।"),
        dict(id="eligible_if", fields=["eligibility_land_limit"],
             q_en="Am I eligible if I own 3 hectares of land?",
             q_hi="अगर मेरे पास 3 हेक्टेयर ज़मीन है, तो क्या मैं पात्र हूँ?",
             a_en=("According to the record, eligible farmers have {eligibility_land_limit}. "
                   "You said you have 3 hectares, which is more than this limit, so you would not be "
                   "eligible under this rule. If you are unsure, please check with the scheme office."),
             a_hi=("रिकॉर्ड के अनुसार, पात्र किसानों के पास {eligibility_land_limit} होती है। "
                   "आपके पास 3 हेक्टेयर है, जो इस सीमा से अधिक है, इसलिए इस नियम के अनुसार आप पात्र नहीं होंगे। "
                   "यदि आप निश्चित नहीं हैं, तो कृपया योजना कार्यालय से पूछें।")),
    ],
    "SCH-002": [
        dict(id="eligibility", fields=["eligibility_class", "eligibility_income_limit"],
             q_en="Who is eligible for this scheme?", q_hi="इस योजना के लिए कौन पात्र है?",
             a_en=("Girl students studying in {eligibility_class} whose family income is "
                   "{eligibility_income_limit} are eligible."),
             a_hi=("{eligibility_class} में पढ़ने वाली वे छात्राएँ पात्र हैं जिनकी पारिवारिक आय "
                   "{eligibility_income_limit} है।")),
        dict(id="eligible_if", fields=["eligibility_income_limit"],
             q_en="Am I eligible if my family earns ₹3,00,000 a year?",
             q_hi="अगर मेरे परिवार की आय ₹3,00,000 प्रति वर्ष है, तो क्या मैं पात्र हूँ?",
             a_en=("According to the record, the family income must be {eligibility_income_limit}. "
                   "Your family income of ₹3,00,000 is not below that limit, so you would not be eligible "
                   "under this rule. If you are unsure, please check with the scheme office."),
             a_hi=("रिकॉर्ड के अनुसार, पारिवारिक आय {eligibility_income_limit} होनी चाहिए। "
                   "आपके परिवार की आय ₹3,00,000 इस सीमा से कम नहीं है, इसलिए इस नियम के अनुसार आप पात्र नहीं होंगे। "
                   "यदि आप निश्चित नहीं हैं, तो कृपया योजना कार्यालय से पूछें।")),
    ],
}


def specs_for(ref):
    return SPECIFIC_SPECS[ref] + SHARED_SPECS  # 2 + 8 = 10 FAQs per scheme


def fill(template, values):
    return re.sub(r"\{(\w+)\}", lambda m: values[m.group(1)], template)


def approved_text(lang):
    """All wording we have approved for `lang` (placeholders removed). Used by the checker."""
    parts = [NF_EN if lang == "en" else NF_HI, CONFLICT_INTRO[lang], CONFLICT_ASK[lang],
             ACCORDING[lang], LOWCONF[lang]]
    for sp in SHARED_SPECS + sum(SPECIFIC_SPECS.values(), []):
        parts.append(sp["a_" + lang])
    return re.sub(r"\{\w+\}", " ", " ".join(parts))
