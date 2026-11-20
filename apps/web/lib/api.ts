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
