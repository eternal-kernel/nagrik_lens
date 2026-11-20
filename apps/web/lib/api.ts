/**
 * API client and TypeScript interfaces matching FastAPI backend schemas.
 */

export interface Constituency {
  id: number;
  election_id: number;
  name: string;
  code: string;
  state: string;
}

export interface Election {
  id: number;
  name: string;
  election_type: string;
  year: number;
  state: string;
  created_at: string;
  constituencies?: Constituency[];
}

export interface CandidateSummary {
  id: number;
  constituency_id: number;
  name: string;
  display_name: string;
  party_name: string;
  is_fictional: boolean;
  created_at: string;
  constituency_name?: string | null;
  election_name?: string | null;
}

export interface AffidavitSummary {
  id: number;
  candidate_id: number;
  source_url?: string | null;
  file_path: string;
  file_hash: string;
  filing_date: string;
  processing_status: string;
  publication_status: string;
  redaction_boxes?: Record<string, any> | null;
  created_at: string;
}

export interface CandidateDetail {
  id: number;
  constituency_id: number;
  name: string;
  display_name: string;
  party_name: string;
  is_fictional: boolean;
  created_at: string;
  constituency: Constituency;
  election?: Election | null;
  affidavits: AffidavitSummary[];
}

export interface LegalGlossaryItem {
  code_key: string;
  act_name: string;
  term: string;
  explanation: string;
  review_status: string;
}

export interface RenderedDisclosure {
  id: number;
  affidavit_id: number;
  category: string;
  field_key: string;
  subject_type: string;
  page_number: number;
  raw_excerpt?: string | null;
  structured_value: Record<string, any>;
  verification_status: string;
  explanation: string;
  glossary_items: LegalGlossaryItem[];
  created_at: string;
  updated_at: string;
}

export interface ReviewEvent {
  id: number;
  disclosure_id: number;
  reviewer_name: string;
  action: string;
  previous_value?: Record<string, any> | null;
  new_value?: Record<string, any> | null;
  review_note?: string | null;
  created_at: string;
}

export interface AdminDisclosureRead extends RenderedDisclosure {
  review_events: ReviewEvent[];
}

export interface AdminAffidavitListItem {
  id: number;
  candidate_id: number;
  candidate_name: string;
  filing_date: string;
  processing_status: string;
  publication_status: string;
  disclosure_count: number;
  needs_review_count: number;
}

export interface InspectionPageDiagnostic {
  page_number: number;
  char_count: number;
  has_embedded_text: boolean;
  extraction_method: string;
}

export interface PdfInspectionReport {
  file_hash: string;
  file_size_bytes: number;
  page_count: number;
  digital_pages: number;
  scanned_pages: number;
  ocr_available: boolean;
  page_diagnostics: InspectionPageDiagnostic[];
}

export interface AffidavitUploadResponse {
  affidavit: AffidavitSummary;
  inspection: PdfInspectionReport;
}

export interface AffidavitExtractionResponse {
  affidavit_id: number;
  processing_status: string;
  pages_inspected: number;
  ocr_pages_detected: number;
  disclosures_extracted: number;
  warnings: string[];
}

export interface CandidateMatchItem {
  candidate_id: number;
  name: string;
  display_name: string;
  party_name: string;
  constituency_name: string;
  constituency_code?: string | null;
  election_name?: string | null;
  confidence: number;
  matched_terms: string[];
}

export interface PosterScanResponse {
  ocr_text: string;
  matches: CandidateMatchItem[];
  requires_disambiguation: boolean;
  detected_constituency?: string | null;
  detected_party?: string | null;
  message?: string | null;
}

export interface DisclosurePatchRequest {
  structured_value?: Record<string, any>;
  page_number?: number;
  verification_status?: "draft" | "needs_review" | "verified" | "rejected" | string;
  review_note?: string;
  reviewer_name: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function getElections(): Promise<Election[]> {
  const res = await fetch(`${API_BASE}/elections`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch elections: ${res.statusText}`);
  }
  return res.json();
}

export async function getCandidates(params?: {
  election_id?: number;
  constituency_id?: number;
  search?: string;
}): Promise<CandidateSummary[]> {
  const query = new URLSearchParams();
  if (params?.election_id) query.set("election_id", String(params.election_id));
  if (params?.constituency_id) query.set("constituency_id", String(params.constituency_id));
  if (params?.search) query.set("search", params.search);

  const url = `${API_BASE}/candidates${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch candidates: ${res.statusText}`);
  }
  return res.json();
}

export async function getCandidateDetail(id: number | string): Promise<CandidateDetail> {
  const res = await fetch(`${API_BASE}/candidates/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch candidate details: ${res.statusText}`);
  }
  return res.json();
}

export async function getAffidavitDisclosures(
  affidavitId: number | string,
  lang: string = "en"
): Promise<RenderedDisclosure[]> {
  const res = await fetch(`${API_BASE}/affidavits/${affidavitId}/disclosures?lang=${lang}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch affidavit disclosures: ${res.statusText}`);
  }
  return res.json();
}

export function getAffidavitPdfUrl(affidavitId: number | string): string {
  return `${API_BASE}/affidavits/${affidavitId}/pdf`;
}

export async function getAdminAffidavitDisclosures(
  affidavitId: number | string,
  adminKey: string,
  lang: string = "en"
): Promise<AdminDisclosureRead[]> {
  const res = await fetch(
    `${API_BASE}/admin/affidavits/${affidavitId}/disclosures?lang=${lang}`,
    {
      cache: "no-store",
      headers: {
        "X-Admin-Key": adminKey,
      },
    }
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Admin request failed with status ${res.status}`
    );
  }
  return res.json();
}

export async function patchAdminDisclosure(
  disclosureId: number | string,
  payload: DisclosurePatchRequest,
  adminKey: string
): Promise<AdminDisclosureRead> {
  const res = await fetch(`${API_BASE}/admin/disclosures/${disclosureId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to update disclosure: ${res.statusText}`
    );
  }
  return res.json();
}

export async function getAdminAffidavits(
  adminKey: string
): Promise<AdminAffidavitListItem[]> {
  const res = await fetch(`${API_BASE}/admin/affidavits`, {
    cache: "no-store",
    headers: {
      "X-Admin-Key": adminKey,
    },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch affidavits list: ${res.status}`
    );
  }
  return res.json();
}

export async function uploadAdminAffidavit(
  file: File,
  candidateId: number | string,
  filingDate: string | null = null,
  sourceUrl: string | null = null,
  adminKey: string
): Promise<AffidavitUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("candidate_id", String(candidateId));
  if (filingDate) formData.append("filing_date", filingDate);
  if (sourceUrl) formData.append("source_url", sourceUrl);

  const res = await fetch(`${API_BASE}/admin/affidavits/upload`, {
    method: "POST",
    headers: {
      "X-Admin-Key": adminKey,
    },
    body: formData,
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Upload failed with status ${res.status}`);
  }
  return res.json();
}

export async function extractAdminAffidavit(
  affidavitId: number | string,
  adminKey: string
): Promise<AffidavitExtractionResponse> {
  const res = await fetch(`${API_BASE}/admin/affidavits/${affidavitId}/extract`, {
    method: "POST",
    headers: {
      "X-Admin-Key": adminKey,
    },
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Extraction failed with status ${res.status}`
    );
  }
  return res.json();
}

export async function scanPosterImage(
  file: File,
  constituencyId?: number | null
): Promise<PosterScanResponse> {
  const formData = new FormData();
  formData.append("file", file);
  let url = `${API_BASE}/poster/scan`;
  if (constituencyId != null) {
    url += `?constituency_id=${constituencyId}`;
  }
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Poster scan failed with status ${res.status}`
    );
  }
  return res.json();
}
