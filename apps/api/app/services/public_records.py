"""Deterministic explanation generator for 5-Year Public Activity Records.

Produces neutral, source-linked, non-evaluative plain-language statements
in English, Telugu, and Hindi across:
1. constituency_works (funds allocated/utilized, works recommended/completed)
2. legislative_performance (session attendance %, questions asked, debates)
3. form26_five_year_delta (declared assets comparison between election cycles)
"""

from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.public_record import PublicActivityRecord
from app.schemas.public_record import FiveYearPreview
from app.services.explanations import format_inr

CATEGORY_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "drinking water pipelines": {
        "en": "drinking water pipelines",
        "te": "తాగునీటి పైప్‌లైన్లు",
        "hi": "पेयजल पाइपलाइन",
    },
    "primary school classrooms": {
        "en": "primary school classrooms",
        "te": "ప్రాథమిక పాఠశాల తరగతి గదులు",
        "hi": "प्राथमिक विद्यालय कक्षाएं",
    },
    "stormwater drains": {
        "en": "stormwater drains",
        "te": "వర్షపు నీటి కాలువలు",
        "hi": "वर्षा जल नालियां",
    },
    "rural roads and street lights": {
        "en": "rural roads and street lights",
        "te": "గ్రామీణ రోడ్లు మరియు వీధి దీపాలు",
        "hi": "ग्रामीण सड़कें और स्ट्रीट लाइटें",
    },
    "community health centres": {
        "en": "community health centres",
        "te": "కమ్యూనిటీ ఆరోగ్య కేంద్రాలు",
        "hi": "सामुदायिक स्वास्थ्य केंद्र",
    },
}


def _translate_categories(categories: List[str], lang: str) -> str:
    """Translate list of public work categories into target language."""
    translated: List[str] = []
    for cat in categories:
        cat_lower = cat.strip().lower()
        if cat_lower in CATEGORY_TRANSLATIONS and lang in CATEGORY_TRANSLATIONS[cat_lower]:
            translated.append(CATEGORY_TRANSLATIONS[cat_lower][lang])
        else:
            translated.append(cat.strip())
    return ", ".join(translated)


def _format_money(amount: Union[int, float, str], lang: str) -> str:
    """Format money value using format_inr if numeric, or return as string."""
    if isinstance(amount, (int, float)):
        return format_inr(amount, lang)
    return str(amount)


def render_public_record_explanations(record: Any) -> Dict[str, str]:
    """Generate deterministic, neutral EN/TE/HI explanations for a public activity record.

    Args:
        record: PublicActivityRecord model instance or dict with keys:
                record_type, period_label, source_name, source_url, structured_payload.

    Returns:
        dict with keys "en", "te", "hi" containing neutral, factual explanations.
    """
    if isinstance(record, dict):
        record_type = record.get("record_type", "")
        period_label = record.get("period_label", "")
        source_name = record.get("source_name", "")
        payload = record.get("structured_payload", {})
    else:
        record_type = getattr(record, "record_type", "")
        period_label = getattr(record, "period_label", "")
        source_name = getattr(record, "source_name", "")
        payload = getattr(record, "structured_payload", {}) or {}

    # 1. Constituency Development Works
    if record_type == "constituency_works":
        if "grant_name" in payload and "works_recommended" not in payload:
            grant = payload.get("grant_name", "Supplementary Development Grant")
            claimed_amt = _format_money(payload.get("claimed_amount", 0), "en")
            claimed_amt_te = _format_money(payload.get("claimed_amount", 0), "te")
            claimed_amt_hi = _format_money(payload.get("claimed_amount", 0), "hi")
            works_claimed = payload.get("works_claimed", 0)
            return {
                "en": (
                    f"According to {source_name} for {period_label}: "
                    f"{works_claimed} works claimed under {grant} with reported expenditure of {claimed_amt}."
                ),
                "te": (
                    f"{period_label} కాలానికి {source_name} ప్రకారం: "
                    f"{grant} కింద {claimed_amt_te} నివేదిత వ్యయంతో {works_claimed} పనులు జరిగినట్లు పేర్కొనబడింది."
                ),
                "hi": (
                    f"{period_label} के लिए {source_name} के अनुसार: "
                    f"{grant} के तहत {claimed_amt_hi} के कथित व्यय के साथ {works_claimed} कार्यों का दावा किया गया।"
                ),
            }

        completed = payload.get("works_completed", 0)
        recommended = payload.get("works_recommended", 0)
        utilized_val = payload.get("funds_utilized", 0)
        allocated_val = payload.get("funds_allocated", 0)
        raw_cats = payload.get("top_categories", [])

        cats_en = _translate_categories(raw_cats, "en") or "general constituency development works"
        cats_te = _translate_categories(raw_cats, "te") or "సాధారణ నియోజకవర్గ అభివృద్ధి పనులు"
        cats_hi = _translate_categories(raw_cats, "hi") or "सामान्य निर्वाचन क्षेत्र विकास कार्य"

        utilized_en = _format_money(utilized_val, "en")
        utilized_te = _format_money(utilized_val, "te")
        utilized_hi = _format_money(utilized_val, "hi")

        allocated_en = _format_money(allocated_val, "en")
        allocated_te = _format_money(allocated_val, "te")
        allocated_hi = _format_money(allocated_val, "hi")

        return {
            "en": (
                f"According to official public records from {source_name} for the period {period_label}: "
                f"{completed} works were completed out of {recommended} recommended constituency development works. "
                f"Total funds utilized were {utilized_en} out of an allocated {allocated_en}. "
                f"Primary work categories included: {cats_en}."
            ),
            "te": (
                f"{period_label} కాలానికి {source_name} అధికారిక ప్రజా రికార్డుల ప్రకారం: "
                f"సిఫార్సు చేసిన {recommended} నియోజకవర్గ అభివృద్ధి పనులలో {completed} పనులు పూర్తయ్యాయి. "
                f"కేటాయించిన {allocated_te} నిధులలో మొత్తం {utilized_te} వినియోగించబడ్డాయి. "
                f"ప్రధాన పనుల విభాగాలు: {cats_te}."
            ),
            "hi": (
                f"{period_label} की अवधि के लिए {source_name} के आधिकारिक सार्वजनिक रिकॉर्ड के अनुसार: "
                f"अनुशंसित {recommended} निर्वाचन क्षेत्र विकास कार्यों में से {completed} कार्य पूरे किए गए। "
                f"कुल आवंटित {allocated_hi} में से {utilized_hi} निधि का उपयोग किया गया। "
                f"प्रमुख कार्य श्रेणियों में शामिल हैं: {cats_hi}।"
            ),
        }

    # 2. Legislative Performance
    elif record_type == "legislative_performance":
        attendance = payload.get("attendance_percentage", 0)
        questions = payload.get("questions_asked", 0)
        debates = payload.get("debates_participated", 0)

        return {
            "en": (
                f"According to legislative session records published by {source_name} for {period_label}: "
                f"the representative recorded {attendance}% session attendance, asked {questions} questions, "
                f"and participated in {debates} debates."
            ),
            "te": (
                f"{period_label} కాలానికి {source_name} ప్రచురించిన శాసనసభ రికార్డుల ప్రకారం: "
                f"సభా సమావేశాలలో {attendance}% హాజరు నమోదైంది, {questions} ప్రశ్నలు అడిగారు "
                f"మరియు {debates} చర్చలలో పాల్గొన్నారు."
            ),
            "hi": (
                f"{period_label} की अवधि के लिए {source_name} द्वारा प्रकाशित विधायी सत्र रिकॉर्ड के अनुसार: "
                f"सदन की बैठकों में {attendance}% उपस्थिति दर्ज की गई, {questions} प्रश्न पूछे गए "
                f"और {debates} बहसों में भाग लिया गया।"
            ),
        }

    # 3. Form 26 Five-Year Delta
    elif record_type == "form26_five_year_delta":
        prev_year = payload.get("previous_election_year", "2019")
        curr_year = payload.get("current_election_year", "2024")

        prev_assets = payload.get("previous_declared_assets")
        if prev_assets is None:
            prev_assets = payload.get("declared_total_assets_previous")
        if prev_assets is None:
            m = payload.get("declared_movable_assets_previous", 0)
            i = payload.get("declared_immovable_assets_previous", 0)
            prev_assets = (m + i) if (m or i) else payload.get("declared_assets_previous", 0)

        curr_assets = payload.get("current_declared_assets")
        if curr_assets is None:
            curr_assets = payload.get("declared_total_assets_current")
        if curr_assets is None:
            m = payload.get("declared_movable_assets_current", 0)
            i = payload.get("declared_immovable_assets_current", 0)
            curr_assets = (m + i) if (m or i) else payload.get("declared_assets_current", 0)

        prev_en = _format_money(prev_assets, "en")
        prev_te = _format_money(prev_assets, "te")
        prev_hi = _format_money(prev_assets, "hi")

        curr_en = _format_money(curr_assets, "en")
        curr_te = _format_money(curr_assets, "te")
        curr_hi = _format_money(curr_assets, "hi")

        return {
            "en": (
                f"According to candidate sworn filings in {source_name}: "
                f"declared total assets were {prev_en} in the {prev_year} election "
                f"and {curr_en} in the {curr_year} election."
            ),
            "te": (
                f"{source_name} లో అభ్యర్థి సమర్పించిన ప్రమాణపూర్వక వివరాల ప్రకారం: "
                f"{prev_year} ఎన్నికలలో ప్రకటించిన మొత్తం ఆస్తులు {prev_te} కాగా, "
                f"{curr_year} ఎన్నికలలో {curr_te} గా ప్రకటించబడ్డాయి."
            ),
            "hi": (
                f"{source_name} में उम्मीदवार द्वारा घोषित शपथ पत्र के विवरण के अनुसार: "
                f"{prev_year} के चुनाव में कुल घोषित संपत्ति {prev_hi} थी "
                f"और {curr_year} के चुनाव में {curr_hi} घोषित की गई।"
            ),
        }

    # Fallback for generic/unrecognized record_type
    return {
        "en": f"Official public activity record from {source_name} for {period_label}.",
        "te": f"{period_label} కాలానికి {source_name} నుండి అధికారిక ప్రజా కార్యకలాపాల రికార్డు.",
        "hi": f"{period_label} के लिए {source_name} से आधिकारिक सार्वजनिक गतिविधि रिकॉर्ड।",
    }


def get_verified_public_records(candidate_id: int, db: Session) -> List[PublicActivityRecord]:
    """Fetch verified PublicActivityRecord rows strictly filtered at the SQL query level.

    Hard Publication Gate:
        NEVER fetch unverified records and filter in Python. The SQL query itself enforces
        verification_status == 'verified'.
    """
    stmt = (
        select(PublicActivityRecord)
        .where(
            PublicActivityRecord.candidate_id == candidate_id,
            PublicActivityRecord.verification_status == "verified",
        )
        .order_by(PublicActivityRecord.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def build_five_year_preview(candidate: Any, db: Session) -> FiveYearPreview:
    """Build a FiveYearPreview summary for a candidate strictly from verified PublicActivityRecords."""
    is_incumbent = bool(getattr(candidate, "prior_office_held", None))
    prior_office_held = getattr(candidate, "prior_office_held", None)

    cand_id = getattr(candidate, "id", None)
    if cand_id is None:
        return FiveYearPreview(
            is_incumbent=is_incumbent,
            prior_office_held=prior_office_held,
            works_completed=None,
            works_recommended=None,
            attendance_pct=None,
            verified_records_count=0,
        )

    # Strictly query verified records at SQL level
    verified_records = get_verified_public_records(cand_id, db)
    verified_count = len(verified_records)

    works_completed: Optional[int] = None
    works_recommended: Optional[int] = None
    attendance_pct: Optional[int] = None

    for rec in verified_records:
        payload = rec.structured_payload or {}
        if rec.record_type == "constituency_works" and works_completed is None:
            if "works_completed" in payload:
                works_completed = payload.get("works_completed")
            if "works_recommended" in payload:
                works_recommended = payload.get("works_recommended")
        elif rec.record_type == "legislative_performance" and attendance_pct is None:
            if "attendance_percentage" in payload:
                attendance_pct = payload.get("attendance_percentage")

    return FiveYearPreview(
        is_incumbent=is_incumbent,
        prior_office_held=prior_office_held,
        works_completed=works_completed,
        works_recommended=works_recommended,
        attendance_pct=attendance_pct,
        verified_records_count=verified_count,
    )
