#!/usr/bin/env python3
"""Synthetic Poster Fixture Generator for Nagrik Lens.

Generates realistic civic campaign poster PNGs for testing the Poster Scanner
and Fuzzy Candidate Matcher using Pillow (PIL):
1. poster_single_candidate.png: Focused single candidate poster for Kiran Rao.
2. poster_multi_candidate.png: Cluttered multi-candidate flexi poster for Kiran Rao and Ananya Sharma.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_DIR = WORKSPACE_ROOT / "fixtures" / "fictional"


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load system TrueType font with graceful fallback to default."""
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path_str in font_candidates:
        p = Path(path_str)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_single_candidate_poster(output_path: Path | None = None) -> Path:
    """Generate high-contrast single candidate campaign poster for Kiran Rao."""
    if output_path is None:
        output_path = OUTPUT_DIR / "poster_single_candidate.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 1. Top Watermark Banner
    draw.rectangle([(0, 0), (width, 50)], fill=(220, 38, 38))
    watermark_font = get_font(18, bold=True)
    draw.text((width // 2, 25), "FICTIONAL DEMO POSTER — NOT A REAL CAMPAIGN", fill=(255, 255, 255), anchor="mm", font=watermark_font)

    # 2. Header Area
    draw.rectangle([(0, 50), (width, 160)], fill=(30, 58, 138))
    header_font = get_font(32, bold=True)
    subhead_font = get_font(20, bold=False)
    draw.text((width // 2, 95), "TELANGANA ASSEMBLY ELECTIONS 2024", fill=(255, 255, 255), anchor="mm", font=header_font)
    draw.text((width // 2, 135), "VOTE FOR HONEST LEADERSHIP & CIVIC PROGRESS", fill=(229, 231, 235), anchor="mm", font=subhead_font)

    # 3. Constituency Bar
    draw.rectangle([(40, 180), (width - 40, 240)], fill=(243, 244, 246), outline=(209, 213, 219), width=2)
    const_font = get_font(24, bold=True)
    draw.text((width // 2, 210), "Fictional Constituency (FC-01)", fill=(17, 24, 39), anchor="mm", font=const_font)

    # 4. Main Candidate Photo / Graphic Placeholder Box
    draw.rectangle([(150, 270), (width - 150, 620)], fill=(238, 242, 255), outline=(129, 140, 248), width=3)
    portrait_label_font = get_font(26, bold=True)
    draw.text((width // 2, 440), "[ CANDIDATE PORTRAIT ]", fill=(99, 102, 241), anchor="mm", font=portrait_label_font)
    draw.text((width // 2, 480), "KIRAN RAO", fill=(67, 56, 202), anchor="mm", font=portrait_label_font)

    # 5. Big Vote Callout
    callout_font = get_font(46, bold=True)
    name_font = get_font(52, bold=True)
    draw.text((width // 2, 670), "VOTE FOR", fill=(185, 28, 28), anchor="mm", font=callout_font)
    draw.text((width // 2, 740), "KIRAN RAO", fill=(17, 24, 39), anchor="mm", font=name_font)

    # 6. Party & Symbol Info
    party_box_y = 800
    draw.rectangle([(60, party_box_y), (width - 60, party_box_y + 160)], fill=(240, 253, 244), outline=(34, 197, 94), width=2)
    party_font = get_font(30, bold=True)
    party_sub_font = get_font(22, bold=False)
    draw.text((width // 2, party_box_y + 45), "Civic Reform Front — Fictional", fill=(21, 128, 61), anchor="mm", font=party_font)
    draw.text((width // 2, party_box_y + 90), "Committed to Education, Health & Infrastructure", fill=(55, 65, 81), anchor="mm", font=party_sub_font)
    draw.text((width // 2, party_box_y + 125), "Election Symbol: Book & Pen (Fictional)", fill=(75, 85, 99), anchor="mm", font=party_sub_font)

    # 7. Slogans
    slogan_font = get_font(22, bold=True)
    draw.text((width // 2, 1020), "MANCHI NAYAKUDU - PRAJA SEVAKUDU", fill=(79, 70, 229), anchor="mm", font=slogan_font)
    draw.text((width // 2, 1060), "Please cast your valuable vote on May 13, 2024", fill=(107, 114, 128), anchor="mm", font=subhead_font)

    # 8. Bottom Disclaimer Banner
    draw.rectangle([(0, height - 60), (width, height)], fill=(243, 244, 246))
    bottom_font = get_font(16, bold=False)
    draw.text((width // 2, height - 30), "Issued by Civic Reform Front Election Committee | Nagrik Lens Test Fixture", fill=(107, 114, 128), anchor="mm", font=bottom_font)

    img.save(str(output_path), "PNG")
    print(f"Generated single candidate poster at: {output_path}")
    return output_path


def generate_multi_candidate_poster(output_path: Path | None = None) -> Path:
    """Generate cluttered multi-candidate flexi banner for Kiran Rao and Ananya Sharma."""
    if output_path is None:
        output_path = OUTPUT_DIR / "poster_multi_candidate.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = 1200, 900
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 1. Top Watermark Banner
    draw.rectangle([(0, 0), (width, 45)], fill=(220, 38, 38))
    watermark_font = get_font(18, bold=True)
    draw.text((width // 2, 22), "FICTIONAL DEMO POSTER — NOT A REAL CAMPAIGN", fill=(255, 255, 255), anchor="mm", font=watermark_font)

    # 2. Grand Event Header with Campaign Noise
    draw.rectangle([(0, 45), (width, 180)], fill=(67, 56, 202))
    rally_font = get_font(38, bold=True)
    noise_font = get_font(24, bold=True)
    sub_noise_font = get_font(18, bold=False)
    draw.text((width // 2, 90), "GRAND PUBLIC MEETING — TELANGANA 2024", fill=(254, 240, 138), anchor="mm", font=rally_font)
    draw.text((width // 2, 135), "YOUTH WING WELCOME & MASS CITIZEN CONVENTION", fill=(255, 255, 255), anchor="mm", font=noise_font)
    draw.text((width // 2, 162), "VENUE: FICTIONAL MUNICIPAL GROUNDS | ALL ARE WELCOME", fill=(224, 231, 255), anchor="mm", font=sub_noise_font)

    # 3. Constituency Callout
    draw.rectangle([(80, 195), (width - 80, 245)], fill=(254, 243, 199), outline=(245, 158, 11), width=2)
    const_font = get_font(22, bold=True)
    draw.text((width // 2, 220), "UNITED DEMOCRATIC ALLIANCE — FICTIONAL CONSTITUENCY (FC-01)", fill=(180, 83, 9), anchor="mm", font=const_font)

    # 4. Multi-Candidate Columns
    # Left Column: Kiran Rao
    col1_x1, col1_x2 = 60, 570
    draw.rectangle([(col1_x1, 260), (col1_x2, 660)], fill=(240, 253, 244), outline=(34, 197, 94), width=2)
    draw.rectangle([(col1_x1 + 40, 280), (col1_x2 - 40, 470)], fill=(220, 252, 231), outline=(74, 222, 128), width=1)
    cand_label_font = get_font(20, bold=True)
    name_large_font = get_font(34, bold=True)
    party_font = get_font(20, bold=True)
    slogan_small = get_font(17, bold=False)

    draw.text(((col1_x1 + col1_x2) // 2, 375), "[ CANDIDATE PHOTO ]", fill=(22, 101, 52), anchor="mm", font=cand_label_font)
    draw.text(((col1_x1 + col1_x2) // 2, 510), "KIRAN RAO", fill=(17, 24, 39), anchor="mm", font=name_large_font)
    draw.text(((col1_x1 + col1_x2) // 2, 555), "Civic Reform Front — Fictional", fill=(21, 128, 61), anchor="mm", font=party_font)
    draw.text(((col1_x1 + col1_x2) // 2, 595), "MLA Candidate — Fictional Constituency", fill=(55, 65, 81), anchor="mm", font=slogan_small)
    draw.text(((col1_x1 + col1_x2) // 2, 625), "Voice for Transparent Governance", fill=(107, 114, 128), anchor="mm", font=slogan_small)

    # Right Column: Ananya Sharma
    col2_x1, col2_x2 = 630, 1140
    draw.rectangle([(col2_x1, 260), (col2_x2, 660)], fill=(239, 246, 255), outline=(59, 130, 246), width=2)
    draw.rectangle([(col2_x1 + 40, 280), (col2_x2 - 40, 470)], fill=(219, 234, 254), outline=(96, 165, 250), width=1)

    draw.text(((col2_x1 + col2_x2) // 2, 375), "[ CANDIDATE PHOTO ]", fill=(30, 64, 175), anchor="mm", font=cand_label_font)
    draw.text(((col2_x1 + col2_x2) // 2, 510), "ANANYA SHARMA", fill=(17, 24, 39), anchor="mm", font=name_large_font)
    draw.text(((col2_x1 + col2_x2) // 2, 555), "Progressive Alliance — Fictional", fill=(29, 78, 216), anchor="mm", font=party_font)
    draw.text(((col2_x1 + col2_x2) // 2, 595), "MP Candidate — Alliance Leader", fill=(55, 65, 81), anchor="mm", font=slogan_small)
    draw.text(((col2_x1 + col2_x2) // 2, 625), "Champion of Public Policy & Justice", fill=(107, 114, 128), anchor="mm", font=slogan_small)

    # 5. United Appeal Banner
    draw.rectangle([(60, 680), (width - 60, 770)], fill=(255, 241, 242), outline=(244, 63, 94), width=2)
    appeal_font = get_font(28, bold=True)
    alliance_sub = get_font(20, bold=False)
    draw.text((width // 2, 715), "VOTE FOR OUR ALLIANCE LEADERS", fill=(190, 18, 60), anchor="mm", font=appeal_font)
    draw.text((width // 2, 748), "CIVIC REFORM FRONT & PROGRESSIVE ALLIANCE JOINT FRONT", fill=(75, 85, 99), anchor="mm", font=alliance_sub)

    # 6. Slogans / Noise Footnote
    foot_noise_font = get_font(18, bold=True)
    draw.text((width // 2, 805), "TELANGANA YOUTH POWER — MARCH TOWARDS VICTORY", fill=(67, 56, 202), anchor="mm", font=foot_noise_font)
    draw.text((width // 2, 830), "Telangana 2024 Campaign Office | Fictional District Central Office", fill=(107, 114, 128), anchor="mm", font=slogan_small)

    # 7. Bottom Disclaimer Banner
    draw.rectangle([(0, height - 40), (width, height)], fill=(243, 244, 246))
    bottom_font = get_font(15, bold=False)
    draw.text((width // 2, height - 20), "Nagrik Lens Test Fixture — Fictional Flexi Poster For OCR & Fuzzy Matcher Validation", fill=(107, 114, 128), anchor="mm", font=bottom_font)

    img.save(str(output_path), "PNG")
    print(f"Generated multi-candidate poster at: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_single_candidate_poster()
    generate_multi_candidate_poster()
