#!/usr/bin/env python3
"""Synthetic Form 26 PDF Generator for Nagrik Lens.

Generates a realistic 4-page ECI Form 26 affidavit for 'Candidate X (Fictional Sample)'
using PyMuPDF 2.x (import pymupdf). Ensures Unicode glyphs like the Indian Rupee (₹)
render cleanly.
"""

from pathlib import Path
import pymupdf


def get_default_pdf_path() -> Path:
    """Return default output path for fictional candidate affidavit."""
    # nagrik-lens/fixtures/fictional/candidate_x_affidavit.pdf
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent.parent
    output_dir = workspace_root / "fixtures" / "fictional"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "candidate_x_affidavit.pdf"


CSS_STYLES = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #111827;
    margin: 0;
    padding: 0;
    font-size: 9pt;
    line-height: 1.35;
}
.banner {
    background-color: #fee2e2;
    border: 1.5px solid #dc2626;
    color: #991b1b;
    font-weight: 800;
    font-size: 9.5pt;
    text-align: center;
    padding: 5px;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
}
.header-title {
    text-align: center;
    font-size: 13pt;
    font-weight: bold;
    margin: 4px 0 2px 0;
    color: #1f2937;
}
.header-subtitle {
    text-align: center;
    font-size: 8pt;
    font-weight: 600;
    color: #4b5563;
    margin: 0 0 10px 0;
    text-transform: uppercase;
}
.section-title {
    font-size: 10pt;
    font-weight: bold;
    color: #1e3a8a;
    border-bottom: 1.5px solid #bfdbfe;
    padding-bottom: 3px;
    margin-top: 10px;
    margin-bottom: 6px;
}
.info-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
}
.info-table th, .info-table td {
    border: 1px solid #d1d5db;
    padding: 4px 6px;
    text-align: left;
    font-size: 8.5pt;
    vertical-align: top;
}
.info-table th {
    background-color: #f3f4f6;
    color: #1f2937;
    font-weight: 700;
}
.text-right {
    text-align: right;
}
.text-center {
    text-align: center;
}
.highlight {
    font-weight: bold;
    color: #111827;
}
.footer-note {
    font-size: 7.5pt;
    color: #6b7280;
    text-align: center;
    border-top: 1px solid #e5e7eb;
    padding-top: 4px;
    margin-top: 12px;
}
"""


def generate_page_1_html() -> str:
    return f"""
<div class="banner">FICTIONAL SAMPLE — NOT A REAL CANDIDATE</div>
<div class="header-title">FORM 26 (See Rule 4A)</div>
<div class="header-subtitle">AFFIDAVIT TO BE FILED BY THE CANDIDATE ALONG WITH NOMINATION PAPER BEFORE THE RETURNING OFFICER</div>

<div class="section-title">ELECTION & CANDIDATE PARTICULARS</div>
<table class="info-table">
    <tr>
        <th style="width: 32%;">Election For</th>
        <td>Telangana Legislative Assembly General Election 2024 (Fictional Sample)</td>
    </tr>
    <tr>
        <th>Constituency</th>
        <td><strong>Fictional Constituency, Telangana</strong> (Constituency Code: FC-01)</td>
    </tr>
    <tr>
        <th>Candidate Name</th>
        <td><span class="highlight">Candidate X (Fictional Sample)</span></td>
    </tr>
    <tr>
        <th>Father's / Spouse's Name</th>
        <td>Late Fictional Senior</td>
    </tr>
    <tr>
        <th>Age & Permanent Address</th>
        <td>42 years, Resident of Plot 42, Fictional Enclave, Fictional District, Telangana - 500001</td>
    </tr>
    <tr>
        <th>Party Affiliation</th>
        <td><strong>Independent — Fictional</strong></td>
    </tr>
    <tr>
        <th>Filing Date</th>
        <td><strong>2024-04-15</strong> (15th April 2024)</td>
    </tr>
    <tr>
        <th>Permanent Account Number (PAN)</th>
        <td>ABCDE1234F (Self: Valid return filed for AY 2023-24)</td>
    </tr>
</table>

<div class="section-title">ITEM (10) DETAILS OF HIGHEST EDUCATIONAL QUALIFICATION</div>
<table class="info-table">
    <tr>
        <th style="width: 32%;">Highest Degree / Course</th>
        <td><span class="highlight">Bachelor of Commerce (B.Com)</span></td>
    </tr>
    <tr>
        <th>College / University</th>
        <td><strong>Osmania University, Hyderabad, Telangana</strong></td>
    </tr>
    <tr>
        <th>Year of Completion</th>
        <td><strong>2012</strong></td>
    </tr>
    <tr>
        <th>Course Format</th>
        <td>3-Year Regular Undergraduate Degree Program</td>
    </tr>
    <tr>
        <th>Official Excerpt</th>
        <td>"B.Com, Osmania University, 2012"</td>
    </tr>
</table>

<div class="footer-note">
    Form 26 Affidavit — Candidate X (Fictional Sample) | Page 1 of 4 | Nagrik Lens Verification Fixture
</div>
"""


def generate_page_2_html() -> str:
    return f"""
<div class="banner">FICTIONAL SAMPLE — NOT A REAL CANDIDATE (Page 2 of 4)</div>
<div class="header-title">ITEM (7) DETAILS OF MOVABLE AND IMMOVABLE ASSETS</div>

<div class="section-title">A. DETAILS OF MOVABLE ASSETS</div>
<table class="info-table">
    <thead>
        <tr>
            <th style="width: 5%;">Sr.</th>
            <th style="width: 35%;">Description</th>
            <th style="width: 15%;" class="text-right">Self</th>
            <th style="width: 15%;" class="text-right">Spouse</th>
            <th style="width: 15%;" class="text-right">HUF</th>
            <th style="width: 15%;" class="text-right">Dependent-1</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>(i)</td>
            <td>Cash in hand</td>
            <td class="text-right">₹50,000</td>
            <td class="text-right">₹20,000</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(ii)</td>
            <td>Deposits in Bank Accounts & FDs</td>
            <td class="text-right">₹2,50,000</td>
            <td class="text-right">₹1,50,000</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iii)</td>
            <td>Motor Vehicles (Two-wheelers)</td>
            <td class="text-right">₹1,00,000</td>
            <td class="text-right">₹50,000</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iv)</td>
            <td>Jewellery, bullion and valuables</td>
            <td class="text-right">₹1,00,000</td>
            <td class="text-right">₹1,00,000</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr style="background-color: #fef3c7; font-weight: bold;">
            <td><strong>(v)</strong></td>
            <td><strong>Gross Total Movable Assets</strong></td>
            <td class="text-right"><strong>₹5,00,000</strong></td>
            <td class="text-right"><strong>₹3,20,000</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
        </tr>
    </tbody>
</table>

<div class="section-title">B. DETAILS OF IMMOVABLE ASSETS</div>
<table class="info-table">
    <thead>
        <tr>
            <th style="width: 5%;">Sr.</th>
            <th style="width: 35%;">Description</th>
            <th style="width: 15%;" class="text-right">Self</th>
            <th style="width: 15%;" class="text-right">Spouse</th>
            <th style="width: 15%;" class="text-right">HUF</th>
            <th style="width: 15%;" class="text-right">Dependent-1</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>(i)</td>
            <td>Agricultural Land (Sy. No. 99/A, Fictional Village; 2.00 Acres)</td>
            <td class="text-right">₹18,00,000</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(ii)</td>
            <td>Non-Agricultural Land</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iii)</td>
            <td>Commercial Buildings</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iv)</td>
            <td>Residential Buildings</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr style="background-color: #fef3c7; font-weight: bold;">
            <td><strong>(v)</strong></td>
            <td><strong>Total Current Market Value of Immovable Assets</strong></td>
            <td class="text-right"><strong>₹18,00,000</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
        </tr>
    </tbody>
</table>

<div class="footer-note">
    Form 26 Affidavit — Candidate X (Fictional Sample) | Page 2 of 4 | Nagrik Lens Verification Fixture
</div>
"""


def generate_page_3_html() -> str:
    return f"""
<div class="banner">FICTIONAL SAMPLE — NOT A REAL CANDIDATE (Page 3 of 4)</div>
<div class="header-title">ITEM (8) DETAILS OF LIABILITIES AND GOVERNMENT DUES</div>

<div class="section-title">A. LIABILITIES TO FINANCIAL INSTITUTIONS AND OTHERS</div>
<table class="info-table">
    <thead>
        <tr>
            <th style="width: 5%;">Sr.</th>
            <th style="width: 45%;">Description of Liability</th>
            <th style="width: 25%;" class="text-right">Self</th>
            <th style="width: 25%;" class="text-right">Spouse</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>(i)</td>
            <td>
                <strong>Loans from Banks / FIs:</strong><br/>
                Home loan from Public Sector Bank (Fictional National Bank, Main Branch)
            </td>
            <td class="text-right" style="vertical-align: middle;"><span class="highlight">₹6,50,000</span></td>
            <td class="text-right" style="vertical-align: middle;">Nil</td>
        </tr>
        <tr>
            <td>(ii)</td>
            <td>Loans or dues to any other individuals / entities</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iii)</td>
            <td>Any other liability (Personal borrowings / private credit)</td>
            <td class="text-right">Nil</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr style="background-color: #fee2e2; font-weight: bold;">
            <td><strong>(iv)</strong></td>
            <td><strong>Grand Total of Liabilities</strong></td>
            <td class="text-right"><strong>₹6,50,000</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
        </tr>
    </tbody>
</table>

<div class="section-title">B. GOVERNMENT DUES</div>
<table class="info-table">
    <thead>
        <tr>
            <th style="width: 5%;">Sr.</th>
            <th style="width: 70%;">Category of Government Dues</th>
            <th style="width: 25%;" class="text-right">Outstanding Amount</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>(i)</td>
            <td>Dues to departments dealing with government accommodation</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(ii)</td>
            <td>Dues to departments dealing with water and electricity supply</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iii)</td>
            <td>Dues to departments dealing with telephones and transport</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr>
            <td>(iv)</td>
            <td>Income Tax dues, GST dues, and Municipal / Property Taxes</td>
            <td class="text-right">Nil</td>
        </tr>
        <tr style="background-color: #f3f4f6; font-weight: bold;">
            <td><strong>(v)</strong></td>
            <td><strong>Grand Total of All Government Dues</strong></td>
            <td class="text-right"><strong>Nil</strong></td>
        </tr>
    </tbody>
</table>

<div class="footer-note">
    Form 26 Affidavit — Candidate X (Fictional Sample) | Page 3 of 4 | Nagrik Lens Verification Fixture
</div>
"""


def generate_page_4_html() -> str:
    return f"""
<div class="banner">FICTIONAL SAMPLE — NOT A REAL CANDIDATE (Page 4 of 4)</div>
<div class="header-title">CRIMINAL ANTECEDENTS & VERIFICATION</div>

<div class="section-title">ITEM (5) PENDING CRIMINAL CASES</div>
<table class="info-table">
    <tr>
        <th style="width: 32%;">Item 5(i) Cases where charges framed</th>
        <td><strong>NIL</strong> — No court has framed criminal charges against the candidate.</td>
    </tr>
    <tr>
        <th>Item 5(ii) Cases where court took cognizance</th>
        <td><strong>1 Pending Case</strong> (Pre-charge stage; details below)</td>
    </tr>
    <tr>
        <th>FIR Number & Police Station</th>
        <td><span class="highlight">FIR No. 112/2022</span>, <strong>Fictional PS</strong>, Fictional District</td>
    </tr>
    <tr>
        <th>Case Number & Court</th>
        <td><span class="highlight">Case No. CC/450/2023</span>, <strong>Judicial First Class Magistrate Court</strong></td>
    </tr>
    <tr>
        <th>Sections of Acts Applicable</th>
        <td><span class="highlight">IPC 143</span> (Unlawful Assembly), <span class="highlight">IPC 341</span> (Wrongful Restraint)</td>
    </tr>
    <tr>
        <th>Brief Description</th>
        <td>Alleged participation in peaceful civic protest; cognizance taken under CrPC.</td>
    </tr>
    <tr>
        <th>Whether Charges Framed?</th>
        <td><strong>NO</strong> (Charges Framed: NO)</td>
    </tr>
    <tr>
        <th>Whether Appeal / Revision Filed?</th>
        <td><strong>NO</strong> (Appeal Filed: NO)</td>
    </tr>
</table>

<div class="section-title">ITEM (6) CASES OF CONVICTION</div>
<table class="info-table">
    <tr>
        <th style="width: 32%;">Conviction Record</th>
        <td><span class="highlight">NIL / NOT APPLICABLE</span></td>
    </tr>
    <tr>
        <th>Details & Count</th>
        <td><strong>Count: 0</strong>. The candidate has NEVER been convicted of any criminal offence by any court of law.</td>
    </tr>
</table>

<div class="section-title">VERIFICATION & OATH (DEPONENT)</div>
<p style="font-size: 8pt; line-height: 1.35; margin: 4px 0 8px 0;">
    I, Candidate X, the deponent above named, do hereby verify and declare that the contents of this affidavit are true and correct to the best of my knowledge and belief and no part of it is false and nothing material has been concealed therefrom.
</p>
<table style="width: 100%; margin-top: 6px;">
    <tr>
        <td style="font-size: 8.5pt;">
            Verified at: <strong>Fictional City, Telangana</strong><br/>
            Filing Date: <strong>15th day of April, 2024 (2024-04-15)</strong>
        </td>
        <td style="text-align: right; font-size: 8.5pt;">
            <div style="border-top: 1px dashed #374151; display: inline-block; padding-top: 4px; width: 220px; text-align: center;">
                <strong>Candidate X (Fictional Sample)</strong><br/>
                <em>DEPONENT</em>
            </div>
        </td>
    </tr>
</table>

<div class="footer-note">
    Form 26 Affidavit — Candidate X (Fictional Sample) | Page 4 of 4 | Nagrik Lens Verification Fixture
</div>
"""


def generate_fictional_pdf(output_path: Path | None = None) -> Path:
    """Generate 4-page synthetic Form 26 PDF using PyMuPDF 2.x."""
    if output_path is None:
        output_path = get_default_pdf_path()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # A4 dimensions: 595.28 x 841.89 points
    a4_width, a4_height = 595, 842
    # Margin 36 points (0.5 inch)
    content_rect = pymupdf.Rect(36, 36, a4_width - 36, a4_height - 36)

    doc = pymupdf.open()

    pages_html = [
        generate_page_1_html(),
        generate_page_2_html(),
        generate_page_3_html(),
        generate_page_4_html(),
    ]

    for page_idx, html_content in enumerate(pages_html, start=1):
        page = doc.new_page(width=a4_width, height=a4_height)
        page.insert_htmlbox(content_rect, html_content, css=CSS_STYLES)

    doc.save(str(output_path))
    doc.close()
    return output_path


if __name__ == "__main__":
    pdf_path = generate_fictional_pdf()
    print(f"Successfully generated synthetic Form 26 PDF at: {pdf_path}")
    
    # Inspect generated PDF
    verify_doc = pymupdf.open(str(pdf_path))
    print(f"Total pages: {len(verify_doc)}")
    for idx, page in enumerate(verify_doc):
        text_preview = page.get_text().strip().split("\n")[:3]
        print(f"  Page {idx + 1} header lines: {' | '.join(text_preview)}")
    verify_doc.close()
