import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const api = axios.create({ baseURL: BASE });

// Types
export interface Tender {
  id: number;
  name: string;
  status: "processing" | "ready" | "error";
  upload_time: string;
  criterion_count: number;
  bidder_count: number;
  extraction_method: string;
}

export interface Criterion {
  id: number;
  tender_id?: number;
  criterion_type: "financial" | "technical" | "compliance" | "documentation";
  description: string;
  is_mandatory: boolean;
  threshold_value: string | null;
  extraction_confidence: number;
  raw_source_text: string;
}

export interface Bidder {
  id: number;
  tender_id?: number;
  name: string;
  status: "processing" | "evaluated" | "error";
  overall_verdict: "eligible" | "not_eligible" | "needs_review" | null;
  overall_reasoning: string | null;
  upload_time: string;
  extraction_method: string;
  // match score fields (populated after evaluation)
  criteria_total?: number;
  criteria_pass?: number;
  criteria_fail?: number;
  criteria_review?: number;
  match_score?: number | null;
}

export interface Evaluation {
  id: number | null;
  verdict: "pass" | "fail" | "needs_review" | null;
  confidence: number | null;
  extracted_value: string | null;
  evidence_snippet: string | null;
  reasoning: string | null;
  evaluated_at: string | null;
  human_verdict: "pass" | "fail" | "needs_review" | null;
  human_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface CriterionEvaluation {
  criterion: Criterion;
  evaluation: Evaluation | null;
}

export interface BidderDetail extends Bidder {
  criteria_evaluations: CriterionEvaluation[];
}

export interface CompareData {
  tender: { id: number; name: string; status: string };
  criteria: Criterion[];
  matrix: {
    bidder_id: number;
    bidder_name: string;
    overall_verdict: string | null;
    status: string;
    criteria: Record<number, {
      verdict: string | null;
      human_verdict: string | null;
      confidence: number | null;
      evaluation_id: number | null;
    }>;
  }[];
}

// API calls
export const uploadTender = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<{ tender_id: number; name: string; status: string }>("/api/tenders/upload", form);
};

export const listTenders = () => api.get<Tender[]>("/api/tenders");

export const getTender = (id: number) =>
  api.get<{ id: number; name: string; status: string; criteria: Criterion[] }>(`/api/tenders/${id}`);

export const getTenderStatus = (id: number) =>
  api.get<{ tender_status: string; criterion_count: number; bidders: Bidder[] }>(`/api/tenders/${id}/status`);

export const uploadBidder = (tenderId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<{ bidder_id: number; name: string; status: string }>(
    `/api/tenders/${tenderId}/bidders/upload`,
    form
  );
};

export const listBidders = (tenderId: number) =>
  api.get<Bidder[]>(`/api/tenders/${tenderId}/bidders`);

export const getBidder = (tenderId: number, bidderId: number) =>
  api.get<BidderDetail>(`/api/tenders/${tenderId}/bidders/${bidderId}`);

export const reviewEvaluation = (
  evaluationId: number,
  body: { human_verdict: string; human_note?: string; reviewed_by?: string }
) => api.patch(`/api/evaluations/${evaluationId}/review`, body);

export const getCompareData = (tenderId: number) =>
  api.get<CompareData>(`/api/tenders/${tenderId}/compare`);

export const getReportUrl = (tenderId: number) =>
  `${BASE}/api/tenders/${tenderId}/report`;

// Analysis types
export interface TenderOverview {
  work_description?: string | null;
  tender_type?: string | null;
  evaluation_method?: string | null;
  location?: string | null;
  bid_type?: string | null;
  beneficiary?: string | null;
  published_date?: string | null;
  bid_opening_date?: string | null;
  last_activity_date?: string | null;
  tender_fee_amount?: string | null;
  tender_fee_exemption_allowed?: string | null;
  emd_fee_amount?: string | null;
  emd_fee_exemption_allowed?: string | null;
  purchase_preferences?: string[];
}

export interface ItemEntry {
  item_name: string;
  quantity: string;
  quantity_unit: string | null;
  delivery_location: string | null;
  consignee: string | null;
  delivery_period: string | null;
  specifications_ref: string | null;
  specifications?: string[];
  source_text: string;
}

export interface AnalysisDocument {
  title: string;
  categories: string[];
  is_mandatory: boolean;
  format_available: boolean;
  summary: string;
  how_to_submit?: string | null;
  details?: string | null;
  format_notes?: string | null;
  source_text: string;
}

export interface ScopeItem {
  title: string;
  summary: string;
  citations: string[];
  source_text: string;
}

export interface EligibilityItem {
  title: string;
  summary: string;
  citations: string[];
  is_mandatory: boolean;
  threshold_value?: string | null;
  source_text: string;
}

export interface ContactItem {
  role: string;
  name?: string | null;
  organisation?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  citations: string[];
  source_text: string;
}

export interface TenderAnalysisData {
  tender_id: number;
  tender_status: string;
  overview: TenderOverview | null;
  documents: AnalysisDocument[];
  scope_of_work: ScopeItem[];
  eligibility: EligibilityItem[];
  contacts: ContactItem[];
  items: ItemEntry[];
  generated_at: string | null;
}

export const getTenderAnalysis = (tenderId: number) =>
  api.get<TenderAnalysisData>(`/api/tenders/${tenderId}/analysis`);

export const reanalyzeTender = (tenderId: number) =>
  api.post<{ status: string; tender_id: number }>(`/api/tenders/${tenderId}/reanalyze`);

export const askTender = (tenderId: number, question: string) =>
  api.post<{ question: string; answer: string }>(`/api/tenders/${tenderId}/ask`, { question });


export const checkHealth = () => api.get<{
  status: string;
  provider: string;
  ollama_ready: boolean;
  ollama_error: string | null;
  ocr_ready: boolean;
  ocr_issues: string[];
  fitz_available: boolean;
  tesseract_available: boolean;
}>("/api/health");

// Helpers
export const VERDICT_LABEL: Record<string, string> = {
  pass: "Pass",
  fail: "Fail",
  needs_review: "Needs Review",
  eligible: "Eligible",
  not_eligible: "Not Eligible",
};

export const VERDICT_COLOR: Record<string, string> = {
  pass: "bg-green-500 text-white",
  fail: "bg-red-500 text-white",
  needs_review: "bg-amber-500 text-white",
  eligible: "bg-green-500 text-white",
  not_eligible: "bg-red-500 text-white",
};

export const TYPE_COLOR: Record<string, string> = {
  financial: "bg-blue-100 text-blue-800",
  technical: "bg-green-100 text-green-800",
  compliance: "bg-amber-100 text-amber-800",
  documentation: "bg-purple-100 text-purple-800",
};
