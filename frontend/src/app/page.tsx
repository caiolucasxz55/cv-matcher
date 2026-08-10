'use client';

import Link from 'next/link';
import { useState } from 'react';
import { GapQuestions } from '@/components/GapQuestions';
import { MatchReport } from '@/components/MatchReport';
import { ResumePreview } from '@/components/ResumePreview';
import { ValidationPanel } from '@/components/ValidationPanel';
import { VersionReview } from '@/components/VersionReview';
import { Button, Card, Field, ScoreCard } from '@/components/ui';
import { analyzeJob, createVersion, downloadBlob, generatePdf } from '@/lib/api';
import type {
  AdaptationStrategy,
  AnalyzeResponse,
  CreateVersionResponse,
  Resume,
  SkillConfirmationInput,
} from '@/lib/api-types';

/**
 * Fluxo (regra 13):
 *   VAGA -> ANALISE -> MATCH -> PERGUNTAS SOBRE GAPS -> 3 VERSOES ->
 *   COMPARACAO -> RECOMENDACAO -> PREVIEW -> PDF
 */
type Step = 'form' | 'gap-questions' | 'match' | 'versions';

export default function Home() {
  const [company, setCompany] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [description, setDescription] = useState('');
  const [confirmations, setConfirmations] = useState<SkillConfirmationInput[]>([]);

  const [step, setStep] = useState<Step>('form');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [version, setVersion] = useState<CreateVersionResponse | null>(null);
  const [creating, setCreating] = useState(false);
  const [strategy, setStrategy] = useState<AdaptationStrategy>('balanced');

  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  function jobPayload(withConfirmations: SkillConfirmationInput[] = confirmations) {
    return {
      description,
      company: company.trim() || undefined,
      job_title: jobTitle.trim() || undefined,
      confirmations: withConfirmations,
    };
  }

  async function handleAnalyze(): Promise<void> {
    setAnalyzing(true);
    setError(null);
    setAnalysis(null);
    setVersion(null);
    setPdfError(null);
    setConfirmations([]);

    try {
      const result = await analyzeJob(jobPayload([]));
      setAnalysis(result);
      setStep(result.pending_gap_questions.length > 0 ? 'gap-questions' : 'match');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleGapAnswers(answers: SkillConfirmationInput[]): Promise<void> {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await analyzeJob(jobPayload(answers));
      setConfirmations(answers);
      setAnalysis(result);
      setStep('match');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleCreateVersion(): Promise<void> {
    setCreating(true);
    setError(null);
    setPdfError(null);

    try {
      const created = await createVersion(jobPayload());
      setVersion(created);
      setStrategy(created.best_variant.strategy);
      setStep('versions');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setCreating(false);
    }
  }

  async function handleGeneratePdf(resume: Resume): Promise<void> {
    if (!version) return;

    setGeneratingPdf(true);
    setPdfError(null);
    try {
      const blob = await generatePdf({
        resume,
        company: company.trim() || undefined,
        jobTitle: jobTitle.trim() || undefined,
      });
      downloadBlob(blob, version.pdf_filename);
    } catch (caught) {
      setPdfError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setGeneratingPdf(false);
    }
  }

  function handleReset(): void {
    setAnalysis(null);
    setVersion(null);
    setConfirmations([]);
    setStep('form');
  }

  const canAnalyze = description.trim().length >= 30 && !analyzing;

  return (
    <main className="mx-auto max-w-4xl px-5 py-12">
      <header className="mb-10">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">CV Matcher</h1>
          <Link
            href="/habilidades"
            className="mt-1 shrink-0 text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-800"
          >
            Editar habilidades técnicas
          </Link>
        </div>
        <p className="mt-1 text-sm text-zinc-600">
          Descubra se seu currículo atende a vaga, confirme o que falta e compare 3 versões
          adaptadas — sem inventar experiência.
        </p>
        <StepIndicator step={step} />
      </header>

      {step === 'form' && (
        <Card>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Nome da empresa (opcional)">
              <input
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                maxLength={160}
                placeholder="Ex.: Nubank"
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-900"
              />
            </Field>
            <Field label="Título da vaga (opcional)">
              <input
                value={jobTitle}
                onChange={(event) => setJobTitle(event.target.value)}
                maxLength={160}
                placeholder="Ex.: Desenvolvedor Backend Python"
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-900"
              />
            </Field>
          </div>

          <div className="mt-4">
            <Field
              label="Descrição da vaga"
              hint={`${description.length.toLocaleString('pt-BR')} caracteres — mínimo 30, máximo 40.000`}
            >
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                maxLength={40_000}
                rows={12}
                placeholder="Cole aqui a descrição completa da vaga..."
                className="w-full resize-y rounded-md border border-zinc-300 px-3 py-2 font-mono text-xs leading-relaxed outline-none focus:border-zinc-900"
              />
            </Field>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <Button onClick={handleAnalyze} disabled={!canAnalyze}>
              {analyzing ? 'Analisando…' : 'Analisar vaga'}
            </Button>
            {analyzing && (
              <span className="text-xs text-zinc-500">
                Comparando a vaga com o currículo base…
              </span>
            )}
          </div>

          {error && (
            <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
              {error}
            </p>
          )}
        </Card>
      )}

      {step === 'gap-questions' && analysis && (
        <div className="space-y-6">
          <GapQuestions
            questions={analysis.pending_gap_questions}
            onSubmit={handleGapAnswers}
            submitting={analyzing}
          />
          {error && (
            <p className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
              {error}
            </p>
          )}
        </div>
      )}

      {step === 'match' && analysis && (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-3">
            <ScoreCard
              label="Job match"
              value={analysis.match.job_match_score}
              caption="aderência do currículo base à vaga"
            />
            <ScoreCard
              label="ATS"
              value={analysis.validation.ats_quality}
              caption="compatibilidade com parsers ATS"
            />
            <ScoreCard
              label="Precisão factual"
              value={analysis.validation.factual_consistency ? 100 : 0}
              caption="respaldo no currículo base"
            />
          </div>

          <MatchReport analysis={analysis.analysis} match={analysis.match} />

          <Card
            title="Criar as 3 versões adaptadas"
            subtitle="Gera Balanced, ATS/Keyword Focus e Experience/Impact Focus (regra 9). Nada é inventado e nenhuma informação é removida."
          >
            {analysis.recommendation.recommended && (
              <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3">
                <p className="text-xs font-semibold tracking-wide text-amber-900 uppercase">
                  Recomendado para esta vaga
                </p>
                <ul className="mt-2 space-y-1 text-sm text-amber-900">
                  {analysis.recommendation.reasons.map((reason, position) => (
                    <li key={`${position}-${reason}`} className="flex gap-2">
                      <span className="text-amber-600">–</span>
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!analysis.recommendation.recommended && (
              <p className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
                Seu currículo base já cobre bem esta vaga. Você pode criar as 3 versões mesmo
                assim para comparar.
              </p>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={handleCreateVersion} disabled={creating}>
                {creating ? 'Criando…' : 'Criar 3 versões'}
              </Button>
              {analysis.recommendation.archetype_label && (
                <span className="text-xs text-zinc-500">
                  Perfil detectado: {analysis.recommendation.archetype_label}
                </span>
              )}
              {confirmations.length > 0 && (
                <span className="text-xs text-zinc-500">
                  {confirmations.filter((c) => c.answer === 'yes').length} habilidade(s)
                  confirmada(s) por você entram nesta versão.
                </span>
              )}
            </div>
          </Card>

          <section>
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold tracking-wide text-zinc-900 uppercase">
                Seu currículo base
              </h2>
              <p className="text-xs text-zinc-500">
                {analysis.base_resume.version} · exibido sem nenhuma alteração
              </p>
            </div>
            <ResumePreview resume={analysis.base_resume} />
          </section>

          <ValidationPanel validation={analysis.validation} autoFixes={[]} changeLog={[]} />

          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-800"
            >
              ← Começar de novo
            </button>
            <p className="text-center text-xs text-zinc-400">Análise: {analysis.provider_name}</p>
          </div>
        </div>
      )}

      {step === 'versions' && version && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setStep('match')}
            className="mb-6 text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-800"
          >
            ← Voltar para a análise
          </button>

          <VersionReview
            data={version}
            baseSummary={analysis?.base_resume.summary ?? version.balanced.resume.summary}
            strategy={strategy}
            onStrategyChange={setStrategy}
            onGeneratePdf={handleGeneratePdf}
            generatingPdf={generatingPdf}
            pdfError={pdfError}
          />

          <p className="mt-8 text-center text-xs text-zinc-400">
            Análise: {version.provider_name} · currículo base{' '}
            {version.base_resume_untouched ? 'intacto' : 'MODIFICADO (erro)'}
          </p>
        </div>
      )}
    </main>
  );
}

const STEP_LABELS: { key: Step; label: string }[] = [
  { key: 'form', label: 'Vaga' },
  { key: 'gap-questions', label: 'Perguntas' },
  { key: 'match', label: 'Match' },
  { key: 'versions', label: '3 versões' },
];

function StepIndicator({ step }: { step: Step }) {
  const activeIndex = STEP_LABELS.findIndex((item) => item.key === step);
  return (
    <ol className="mt-4 flex flex-wrap gap-2 text-xs">
      {STEP_LABELS.map((item, index) => (
        <li
          key={item.key}
          className={`rounded-full border px-2.5 py-1 ${
            index === activeIndex
              ? 'border-zinc-900 bg-zinc-900 text-white'
              : index < activeIndex
                ? 'border-zinc-300 bg-zinc-100 text-zinc-500'
                : 'border-zinc-200 text-zinc-400'
          }`}
        >
          {index + 1}. {item.label}
        </li>
      ))}
    </ol>
  );
}
