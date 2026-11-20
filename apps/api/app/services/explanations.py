"""Deterministic explanation engine for Nagrik Lens.

Generates neutral, source-linked, plain-language explanations in English,
Telugu, and Hindi without free-form LLM generation. All values are explicitly
attributed as declared by the candidate/deponent, with zero evaluative language.
"""

from typing import Any, Dict, List, Tuple
from fastapi import HTTPException

from app.models.affidavit import Disclosure
from app.models.glossary import LegalGlossary
from app.schemas.glossary import LegalGlossaryItem

SUPPORTED_LANGUAGES = {"en", "te", "hi"}

SUBJECT_LABELS: Dict[str, Dict[str, str]] = {
    "self": {
        "en": "the candidate",
        "te": "అభ్యర్థి",
        "hi": "उम्मीदवार",
    },
    "spouse": {
        "en": "the candidate's spouse",
        "te": "అభ్యర్థి జీవిత భాగస్వామి",
        "hi": "उम्मीदवार के जीवनसाथी",
    },
    "huf": {
        "en": "Hindu Undivided Family (HUF)",
        "te": "హిందూ అవిభక్త కుటుంబం (HUF)",
        "hi": "अविभाजित हिंदू परिवार (HUF)",
    },
    "dependent_1": {
        "en": "Dependent 1",
        "te": "ఆధారపడిన వ్యక్తి 1",
        "hi": "आश्रित 1",
    },
    "dependent_2": {
        "en": "Dependent 2",
        "te": "ఆధారపడిన వ్యక్తి 2",
        "hi": "आश्रित 2",
    },
    "dependent_3": {
        "en": "Dependent 3",
        "te": "ఆధారపడిన వ్యక్తి 3",
        "hi": "आश्रित 3",
    },
    "joint": {
        "en": "joint holding",
        "te": "ఉమ్మడి హోల్డింగ్",
        "hi": "संयुक्त धारिता",
    },
}


def format_inr(amount: int | float, lang: str = "en") -> str:
    """Format Indian Rupees into clean plain language across EN, TE, and HI.

    Examples:
        500000   -> '₹5 lakh'   / '₹5 లక్షలు'   / '₹5 लाख'
        1800000  -> '₹18 lakh'  / '₹18 లక్షలు'  / '₹18 लाख'
        650000   -> '₹6.5 lakh' / '₹6.5 లక్షలు' / '₹6.5 लाख'
        320000   -> '₹3.2 lakh' / '₹3.2 లక్షలు' / '₹3.2 लाख'
        50000    -> '₹50,000'   / '₹50,000'    / '₹50,000'
        0        -> 'Nil'       / 'సున్నా (Nil)' / 'शून्य (Nil)'
    """
    if amount == 0:
        return {"en": "Nil", "te": "సున్నా (Nil)", "hi": "शून्य (Nil)"}.get(lang, "Nil")

    if amount >= 10_000_000:
        cr = amount / 10_000_000
        cr_str = f"{cr:.2f}".rstrip("0").rstrip(".")
        if lang == "te":
            return f"₹{cr_str} కోట్లు"
        elif lang == "hi":
            return f"₹{cr_str} करोड़"
        else:
            return f"₹{cr_str} crore"

    if amount >= 100_000:
        lakh = amount / 100_000
        lakh_str = f"{lakh:.2f}".rstrip("0").rstrip(".")
        if lang == "te":
            return f"₹{lakh_str} లక్షలు"
        elif lang == "hi":
            return f"₹{lakh_str} लाख"
        else:
            return f"₹{lakh_str} lakh"

    formatted_num = f"{int(amount):,}"
    return f"₹{formatted_num}"


def normalize_glossary_key(raw_key: str) -> str:
    """Normalize legal section/code string (e.g., 'IPC 143' -> 'IPC_143')."""
    return raw_key.strip().replace(" ", "_").replace("-", "_").upper()


def get_glossary_item_for_lang(
    item: LegalGlossary, lang: str
) -> LegalGlossaryItem:
    """Render a LegalGlossary model into a language-specific LegalGlossaryItem schema."""
    if lang == "te":
        exp = item.explanation_te
    elif lang == "hi":
        exp = item.explanation_hi
    else:
        exp = item.explanation_en

    return LegalGlossaryItem(
        code_key=item.code_key,
        act_name=item.act_name,
        term=item.term_en,
        explanation=exp,
        review_status=item.review_status,
    )


def build_explanation(
    disclosure: Disclosure,
    lang: str = "en",
    glossary_map: Dict[str, LegalGlossary] | None = None,
) -> Tuple[str, List[LegalGlossaryItem]]:
    """Generate a deterministic explanation and attached glossary entries for a disclosure.

    Raises:
        HTTPException(status_code=400): If lang is not in {'en', 'te', 'hi'}.
    """
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang}'. Supported languages are: {', '.join(sorted(SUPPORTED_LANGUAGES))}",
        )

    glossary_map = glossary_map or {}
    val: Dict[str, Any] = disclosure.structured_value or {}
    cat = disclosure.category
    subject = disclosure.subject_type

    subj_labels = SUBJECT_LABELS.get(subject, SUBJECT_LABELS["self"])
    subj_text = subj_labels.get(lang, subj_labels["en"])

    explanation = ""
    glossary_items: List[LegalGlossaryItem] = []

    # 1. Education
    if cat == "education":
        degree = val.get("degree", "Qualification")
        institution = val.get("institution", "Institution")
        year = val.get("year", "N/A")
        if lang == "te":
            explanation = (
                f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: "
                f"వారి అత్యున్నత విద్యార్హత {institution} నుండి {year}లో పూర్తి చేసిన {degree}."
            )
        elif lang == "hi":
            explanation = (
                f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                f"उनकी उच्चतम शैक्षणिक योग्यता {institution} से वर्ष {year} में पूर्ण की गई {degree} है।"
            )
        else:
            explanation = (
                f"Declared by the candidate in the Form 26 affidavit: "
                f"highest educational qualification is {degree} from {institution}, completed in {year}."
            )

    # 2. Movable Assets
    elif cat == "movable_assets":
        amt = val.get("amount", 0)
        formatted_amount = format_inr(amt, lang)
        if lang == "te":
            if subject == "self":
                explanation = (
                    f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: "
                    f"అభ్యర్థి పేరిట ఉన్న మొత్తం చరాస్తుల విలువ {formatted_amount}."
                )
            else:
                explanation = (
                    f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: "
                    f"{subj_text} పేరిట ఉన్న మొత్తం చరాస్తుల విలువ {formatted_amount}."
                )
        elif lang == "hi":
            if subject == "self":
                explanation = (
                    f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                    f"उम्मीदवार के नाम पर कुल चल संपत्ति का मूल्य {formatted_amount} है।"
                )
            else:
                explanation = (
                    f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                    f"{subj_text} के नाम पर कुल चल संपत्ति का मूल्य {formatted_amount} है।"
                )
        else:
            if subject == "self":
                explanation = (
                    f"Declared by the candidate in the Form 26 affidavit: "
                    f"gross total movable assets belonging to the candidate are valued at {formatted_amount}."
                )
            else:
                explanation = (
                    f"Declared by the candidate in the Form 26 affidavit: "
                    f"gross total movable assets belonging to {subj_text} are valued at {formatted_amount}."
                )

    # 3. Immovable Assets
    elif cat == "immovable_assets":
        amt = val.get("amount", 0)
        formatted_amount = format_inr(amt, lang)
        asset_type = val.get("asset_type", "Immovable asset")
        if lang == "te":
            explanation = (
                f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: "
                f"{subj_text} పేరిట ఉన్న స్థిరాస్తుల ({asset_type}) ప్రకటించబడిన ప్రస్తుత మార్కెట్ విలువ {formatted_amount}."
            )
        elif lang == "hi":
            explanation = (
                f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                f"{subj_text} के नाम पर अचल संपत्ति ({asset_type}) का घोषित वर्तमान बाजार मूल्य {formatted_amount} है।"
            )
        else:
            explanation = (
                f"Declared by the candidate in the Form 26 affidavit: "
                f"immovable assets belonging to {subj_text} ({asset_type}) have a declared current market value of {formatted_amount}."
            )

    # 4. Liabilities
    elif cat == "liabilities":
        amt = val.get("amount", 0)
        formatted_amount = format_inr(amt, lang)
        loan_type = val.get("loan_type", "Loan/Liability")
        lender = val.get("lender", "Lending institution")
        if lang == "te":
            explanation = (
                f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: "
                f"{subj_text} పేరిట {lender} నుండి తీసుకున్న {loan_type} బకాయి మొత్తం {formatted_amount}."
            )
        elif lang == "hi":
            explanation = (
                f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                f"{subj_text} के नाम पर {lender} से {loan_type} की कुल बकाया देयता राशि {formatted_amount} है।"
            )
        else:
            explanation = (
                f"Declared by the candidate in the Form 26 affidavit: "
                f"liabilities under {subj_text} include {loan_type} from {lender} with an outstanding balance of {formatted_amount}."
            )

    # 5. Pending Criminal Cases
    elif cat == "pending_criminal_cases":
        fir_no = val.get("fir_no", "N/A")
        ps = val.get("police_station", "N/A")
        case_no = val.get("case_no", "N/A")
        court = val.get("court_name", "N/A")
        raw_sections = val.get("sections", [])
        sections_str = ", ".join(raw_sections) if raw_sections else "N/A"
        charges_framed = val.get("charges_framed", False)
        stage_code = val.get("stage_code", "STAGE_COGNIZANCE")

        # Collect glossary keys to attach
        needed_keys: List[str] = []
        for s in raw_sections:
            needed_keys.append(normalize_glossary_key(s))
        if stage_code:
            needed_keys.append(normalize_glossary_key(stage_code))
        if not charges_framed:
            needed_keys.append("CHARGES_NOT_FRAMED")

        for k in needed_keys:
            if k in glossary_map:
                glossary_items.append(get_glossary_item_for_lang(glossary_map[k], lang))

        if lang == "te":
            charges_note = (
                "అధికారికంగా నేరారోపణలు (ఛార్జీలు) నమోదు చేయబడ్డాయి"
                if charges_framed
                else "అధికారికంగా నేరారోపణలు (ఛార్జీలు) ఇంకా నమోదు కాలేదు"
            )
            explanation = (
                f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: "
                f"అభ్యర్థిపై 1 క్రిమినల్ కేసు విచారణలో ఉంది (ఎఫ్ఐఆర్ నెం. {fir_no}, {ps}; "
                f"కేసు నెం. {case_no}, {court}; సెక్షన్లు: {sections_str}). "
                f"న్యాయస్థానం కేసును పరిగణనలోకి (కాగ్నిజెన్స్) తీసుకున్నప్పటికీ, {charges_note}. "
                f"ముఖ్యమైన చట్టపరమైన గమనిక: భారతదేశ చట్టం ప్రకారం పెండింగ్‌లో ఉన్న క్రిమినల్ కేసు లేదా ఆరోపణ "
                f"అనేది కేవలం విచారణలో ఉన్న అంశం మాత్రమే; ఇది నేర నిర్ధారణ లేదా శిక్ష ఎంతమాత్రం కాదు."
            )
        elif lang == "hi":
            charges_note = (
                "औपचारिक रूप से आरोप तय किए जा चुके हैं"
                if charges_framed
                else "औपचारिक रूप से आरोप तय नहीं किए गए हैं"
            )
            explanation = (
                f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                f"उम्मीदवार के विरुद्ध 1 आपराधिक मामला विचाराधीन है (एफआईआर संख्या {fir_no}, {ps}; "
                f"केस संख्या {case_no}, {court}; धाराएं: {sections_str})। "
                f"अदालत ने मामले पर संज्ञान लिया है, और {charges_note}। "
                f"महत्वपूर्ण कानूनी स्पष्टीकरण: भारतीय कानून के तहत, लंबित आपराधिक मामला केवल अदालत में विचाराधीन एक आरोप है; "
                f"यह किसी भी प्रकार की दोषसिद्धि (सजा) नहीं है।"
            )
        else:
            charges_note = (
                "formal charges have been framed"
                if charges_framed
                else "formal charges have not been framed"
            )
            explanation = (
                f"Declared by the candidate in the Form 26 affidavit: "
                f"1 pending criminal case (FIR No. {fir_no}, {ps}; Case No. {case_no} at {court}) "
                f"under sections {sections_str}. The court has taken cognizance, and {charges_note}. "
                f"Important legal note: Under Indian law, a pending criminal case or charge sheet is an allegation awaiting judicial trial; "
                f"it is not a conviction and guilt has not been established."
            )

    # 6. Convictions
    elif cat == "convictions":
        count = val.get("count", 0)
        status_code = val.get("status", "NIL")
        if lang == "te":
            explanation = (
                f"ఫారం 26 అఫిడవిట్‌లోని ఐటెమ్ (6) లో అభ్యర్థి స్వయంగా ప్రకటించిన ప్రకారం: "
                f"అభ్యర్థికి ఏ న్యాయస్థానం ద్వారా కూడా ఎలాంటి నేరంలోనూ శిక్ష పడలేదు (దోష నిర్ధారణలు: ఏమీ లేవు / {status_code})."
            )
        elif lang == "hi":
            explanation = (
                f"फॉर्म 26 शपथ पत्र के मद (6) में उम्मीदवार द्वारा घोषित विवरण के अनुसार: "
                f"उम्मीदवार को किसी भी अदालत द्वारा किसी भी आपराधिक मामले में कभी दोषी नहीं ठहराया गया है (दोषसिद्धि: शून्य / {status_code})।"
            )
        else:
            explanation = (
                f"Declared by the candidate in Item (6) of the Form 26 affidavit: "
                f"candidate has never been convicted of any criminal offence by any court of law (Convictions: {status_code})."
            )

    # Fallback default for unexpected category
    else:
        if lang == "te":
            explanation = f"ఫారం 26 అఫిడవిట్‌లో అభ్యర్థి ప్రకటించిన వివరాలు."
        elif lang == "hi":
            explanation = f"फॉर्म 26 शपथ पत्र में उम्मीदवार द्वारा घोषित विवरण।"
        else:
            explanation = f"Declared by the candidate in the Form 26 affidavit."

    return explanation, glossary_items
