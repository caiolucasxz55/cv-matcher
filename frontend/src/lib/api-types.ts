/**
 * Espelho tipado dos contratos expostos pela API FastAPI (`backend/app`).
 * Os nomes seguem snake_case por virem do backend Python sem transformação.
 */

export interface ResumeLink {
  label: string;
  url: string;
}

export interface ResumeBasics {
  name: string;
  headline: string;
  location: string;
  email: string;
  phone: string;
  links: ResumeLink[];
}

export interface ResumeExperienceBullet {
  id: string;
  text: string;
  terms: string[];
}

export interface ResumeExperience {
  id: string;
  role: string;
  company: string;
  location: string;
  period: string;
  current: boolean;
  bullets: ResumeExperienceBullet[];
}

export interface ResumeProjectBullet {
  id: string;
  text: string;
  terms: string[];
}

export interface ResumeProject {
  id: string;
  name: string;
  description: string;
  terms: string[];
  bullets: ResumeProjectBullet[];
}

export interface ResumeSkillCategory {
  id: string;
  label: string;
  items: string[];
}

export interface ResumeEducation {
  id: string;
  degree: string;
  institution: string;
  period: string;
}

export interface ResumeCourse {
  id: string;
  name: string;
  terms: string[];
}

export interface ResumeLanguage {
  name: string;
  level: string;
}

export interface SummaryFragment {
  id: string;
  text: string;
  terms: string[];
}

export interface ResumeSummaryTemplate {
  role: string;
  opening: string;
  capabilities: SummaryFragment[];
  focus: SummaryFragment[];
  fallback: string;
}

export interface Resume {
  id: string;
  version: string;
  kind: 'base' | 'adapted';
  basics: ResumeBasics;
  summary: string;
  experience: ResumeExperience[];
  projects: ResumeProject[];
  skill_categories: ResumeSkillCategory[];
  education: ResumeEducation[];
  courses: ResumeCourse[];
  languages: ResumeLanguage[];
  summary_template: ResumeSummaryTemplate;
}

export type Seniority =
  | 'estagio'
  | 'junior'
  | 'pleno'
  | 'senior'
  | 'especialista'
  | 'lead'
  | 'nao_identificada';

export type MatchLevel = 'STRONG' | 'MEDIUM' | 'WEAK' | 'NONE';

export interface JobRequirement {
  term: string;
  category: string;
  kind: 'required' | 'preferred';
  evidence: string;
}

export interface JobAnalysis {
  job_title: string;
  company: string;
  seniority: Seniority;
  keywords: string[];
  technologies: string[];
  frameworks: string[];
  programming_languages: string[];
  databases: string[];
  cloud: string[];
  devops: string[];
  ai_ml: string[];
  required_skills: string[];
  preferred_skills: string[];
  requirements: JobRequirement[];
  responsibilities: string[];
  ats_keywords: string[];
  candidate_matches: string[];
  missing_requirements: string[];
  source: string;
  ai_notes: string[];
}

export interface TermMatch {
  term: string;
  category: string;
  level: MatchLevel;
  kind: string;
  evidence: string[];
  related_via: string | null;
}

export interface AtsCheck {
  id: string;
  label: string;
  passed: boolean;
  weight: number;
  detail: string;
}

export interface ValidationIssue {
  value: string;
  location: string;
  reason: string;
  source: 'deterministic' | 'ai';
}

export interface ValidationResult {
  is_valid: boolean;
  score: number;
  hallucinations: ValidationIssue[];
  unsupported_claims: ValidationIssue[];
  missing_relevant_keywords: string[];
  overused_keywords: string[];
  factual_consistency: boolean;
  ats_quality: number;
  job_alignment: number;
  recommendations: string[];
  ats_checks: AtsCheck[];
  validator: 'deterministic' | 'deterministic+ai';
}

export interface ArchetypeScore {
  archetype_id: string;
  label: string;
  description: string;
  score: number;
  matched_signals: string[];
}

export interface Recommendation {
  recommended: boolean;
  detected_archetype: string | null;
  archetype_label: string | null;
  reasons: string[];
  ranking: ArchetypeScore[];
}

export interface MatchSummary {
  job_match_score: number;
  strong: TermMatch[];
  medium: TermMatch[];
  weak: TermMatch[];
  missing: TermMatch[];
}

/** Resposta possível a uma pergunta de gap (regra 2). */
export type ConfirmationAnswer = 'yes' | 'no' | 'unsure';

/** Pergunta pendente: a vaga pede, o currículo base não evidencia. */
export interface GapQuestion {
  term: string;
  category: string;
  kind: string;
  answer: ConfirmationAnswer | null;
}

/** Resposta da pessoa a uma GapQuestion, enviada de volta à API. */
export interface SkillConfirmationInput {
  term: string;
  answer: ConfirmationAnswer;
  context?: string;
}

/** Diagnostico do curriculo BASE. Nada foi adaptado. */
export interface AnalyzeResponse {
  analysis: JobAnalysis;
  match: MatchSummary;
  base_resume: Resume;
  validation: ValidationResult;
  recommendation: Recommendation;
  pending_gap_questions: GapQuestion[];
  pdf_filename: string;
  provider_name: string;
}

export interface SummaryOption {
  id: string;
  label: string;
  archetype_id: string;
  archetype_label: string;
  text: string;
  techs: string[];
}

/** As três estratégias exigidas (regra 9) — nenhuma outra existe. */
export type AdaptationStrategy = 'balanced' | 'ats_focus' | 'experience_focus';

export const STRATEGY_ORDER: AdaptationStrategy[] = ['balanced', 'ats_focus', 'experience_focus'];

export interface Variant {
  strategy: AdaptationStrategy;
  strategy_label: string;
  version_label: string;
  version_number: number;
  created_at: string;
  base_version: string;
  change_log: string[];
  summary_option_id: string | null;
  resume: Resume;
  validation: ValidationResult;
  auto_fixes: string[];
}

export interface BestVariant {
  strategy: AdaptationStrategy;
  label: string;
  reason: string;
}

export interface CreateVersionResponse {
  analysis: JobAnalysis;
  match: MatchSummary;
  balanced: Variant;
  ats_focus: Variant;
  experience_focus: Variant;
  summary_options: SummaryOption[];
  recommendation: Recommendation;
  best_variant: BestVariant;
  pdf_filename: string;
  provider_name: string;
  base_resume_untouched: boolean;
  pending_gap_questions: GapQuestion[];
}

export interface JobPayload {
  description: string;
  company?: string;
  job_title?: string;
  confirmations?: SkillConfirmationInput[];
}

export interface CreateVersionPayload extends JobPayload {
  archetype_id?: string;
  summary_option_id?: string;
}

export interface RevalidateResponse {
  match: MatchSummary;
  validation: ValidationResult;
  recommendation: Recommendation;
  pending_gap_questions: GapQuestion[];
}

export interface SkillItem {
  name: string;
  custom: boolean;
  recognized: boolean;
}

export interface SkillCategory {
  id: string;
  label: string;
  items: SkillItem[];
}

export interface SkillsOverview {
  categories: SkillCategory[];
  available_terms: string[];
}
