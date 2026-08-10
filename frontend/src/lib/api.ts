import type {
  AnalyzeResponse,
  CreateVersionPayload,
  CreateVersionResponse,
  JobAnalysis,
  JobPayload,
  Resume,
  RevalidateResponse,
  SkillsOverview,
} from './api-types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Erro de API com a mensagem já extraída do corpo da resposta. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: unknown };
        if (typeof first?.msg === 'string') return first.msg;
      }
      if (typeof detail === 'object' && detail !== null && 'error' in detail) {
        return String((detail as { error: unknown }).error);
      }
    }
  } catch {
    // corpo não-JSON: usa o fallback
  }
  return fallback;
}

async function postJson<T>(path: string, body: unknown, fallback: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response, fallback), response.status);
  }
  return (await response.json()) as T;
}

async function getJson<T>(path: string, fallback: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response, fallback), response.status);
  }
  return (await response.json()) as T;
}

/** Etapa 1 — avalia o currículo base (+ confirmações de gap) contra a vaga. Não adapta nada. */
export function analyzeJob(payload: JobPayload): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>('/api/analyze', payload, 'Falha ao analisar a vaga.');
}

/** Etapa 2 — cria as TRÊS variantes: balanced, ats_focus, experience_focus (regra 9). */
export function createVersion(payload: CreateVersionPayload): Promise<CreateVersionResponse> {
  return postJson<CreateVersionResponse>(
    '/api/versions',
    payload,
    'Falha ao criar a versão adaptada.',
  );
}

export async function generatePdf(params: {
  resume: Resume;
  company?: string;
  jobTitle?: string;
}): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      resume: params.resume,
      company: params.company,
      job_title: params.jobTitle,
    }),
  });

  if (!response.ok) {
    throw new ApiError(
      await extractErrorMessage(response, 'Falha ao gerar o PDF.'),
      response.status,
    );
  }
  return response.blob();
}

/** Habilidades técnicas do currículo base (originais + adicionadas pelo usuário). */
export function getSkills(): Promise<SkillsOverview> {
  return getJson<SkillsOverview>('/api/base-resume/skills', 'Falha ao carregar habilidades.');
}

export function addSkill(categoryId: string, term: string): Promise<SkillsOverview> {
  return postJson<SkillsOverview>(
    '/api/base-resume/skills',
    { category_id: categoryId, term },
    'Falha ao adicionar habilidade.',
  );
}

export function removeSkill(categoryId: string, term: string): Promise<SkillsOverview> {
  return postJson<SkillsOverview>(
    '/api/base-resume/skills/remove',
    { category_id: categoryId, term },
    'Falha ao remover habilidade.',
  );
}

/**
 * Botão "Reanalisar" (regra 12): recalcula match, validação E recomendação
 * juntos a partir do currículo editado na tela de revisão — nunca só a
 * validação isolada. Reaproveita `analysis` já obtida em `analyzeJob`/
 * `createVersion`, mas NÃO reaproveita o `match` antigo (ele é recalculado
 * do zero contra o índice de evidências atual).
 */
export function revalidateResume(params: {
  resume: Resume;
  analysis: JobAnalysis;
  confirmations?: JobPayload['confirmations'];
}): Promise<RevalidateResponse> {
  return postJson<RevalidateResponse>(
    '/api/revalidate',
    params,
    'Falha ao reanalisar o currículo.',
  );
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
