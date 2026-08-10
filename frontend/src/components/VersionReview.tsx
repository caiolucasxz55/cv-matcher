'use client';

import { useEffect, useState } from 'react';
import type {
  AdaptationStrategy,
  CreateVersionResponse,
  Resume,
  ResumeSkillCategory,
  Variant,
} from '@/lib/api-types';
import { STRATEGY_ORDER } from '@/lib/api-types';
import { revalidateResume } from '@/lib/api';
import { MatchReport } from './MatchReport';
import { ResumePreview } from './ResumePreview';
import { ValidationPanel } from './ValidationPanel';
import { Button, Card } from './ui';

const STRATEGY_LETTER: Record<AdaptationStrategy, string> = {
  balanced: 'A',
  ats_focus: 'B',
  experience_focus: 'C',
};

const STRATEGY_HINT: Record<AdaptationStrategy, string> = {
  balanced: 'Equilíbrio entre aderência à vaga e leitura natural.',
  ats_focus: 'Maximiza cobertura literal das palavras-chave da vaga.',
  experience_focus: 'Prioriza bullets com resultado concreto já comprovado.',
};

/**
 * Tela de comparação + revisão: a pessoa compara as 3 versões (regra 9),
 * vê qual é recomendada (regra 10) e só então libera o PDF de uma delas.
 */
export function VersionReview({
  data,
  baseSummary,
  strategy,
  onStrategyChange,
  onGeneratePdf,
  generatingPdf,
  pdfError,
}: {
  data: CreateVersionResponse;
  baseSummary: string;
  strategy: AdaptationStrategy;
  onStrategyChange: (strategy: AdaptationStrategy) => void;
  onGeneratePdf: (resume: Resume) => void;
  generatingPdf: boolean;
  pdfError: string | null;
}) {
  const variant = data[strategy];

  // Edicao local das habilidades desta versao: nao toca no curriculo base,
  // so no que sera exibido/exportado aqui.
  const [editedSkills, setEditedSkills] = useState<ResumeSkillCategory[] | null>(null);
  const [recomputed, setRecomputed] = useState<Awaited<
    ReturnType<typeof revalidateResume>
  > | null>(null);
  const [revalidating, setRevalidating] = useState(false);
  const [revalidateError, setRevalidateError] = useState<string | null>(null);

  useEffect(() => {
    setEditedSkills(null);
    setRecomputed(null);
    setRevalidateError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, strategy]);

  const skillCategories = editedSkills ?? variant.resume.skill_categories;
  const effectiveResume: Resume =
    editedSkills === null ? variant.resume : { ...variant.resume, skill_categories: editedSkills };
  const effectiveValidation = recomputed?.validation ?? variant.validation;
  const effectiveMatch = recomputed?.match ?? data.match;
  const effectiveRecommendation = recomputed?.recommendation ?? data.recommendation;
  const hasPendingEdits = editedSkills !== null && recomputed === null;

  function handleAddSkill(categoryId: string, term: string): void {
    const cleaned = term.trim();
    if (!cleaned) return;
    setEditedSkills(
      skillCategories.map((category) =>
        category.id === categoryId && !category.items.includes(cleaned)
          ? { ...category, items: [...category.items, cleaned] }
          : category,
      ),
    );
    setRecomputed(null);
    setRevalidateError(null);
  }

  function handleRemoveSkill(categoryId: string, term: string): void {
    setEditedSkills(
      skillCategories.map((category) =>
        category.id === categoryId
          ? { ...category, items: category.items.filter((item) => item !== term) }
          : category,
      ),
    );
    setRecomputed(null);
    setRevalidateError(null);
  }

  async function handleRevalidate(): Promise<void> {
    setRevalidating(true);
    setRevalidateError(null);
    try {
      // Reanalisar (regra 12): recalcula match + validação + recomendação
      // juntos, nunca só a validação isolada.
      setRecomputed(
        await revalidateResume({ resume: effectiveResume, analysis: data.analysis }),
      );
    } catch (caught) {
      setRevalidateError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setRevalidating(false);
    }
  }

  return (
    <div className="space-y-8">
      <MatchReport analysis={data.analysis} match={effectiveMatch} />

      <Card
        title="Compare as 3 versões"
        subtitle="Mesmo conteúdo, três estratégias de organização. Nada é removido ou inventado em nenhuma delas."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {STRATEGY_ORDER.map((key) => (
            <VariantCard
              key={key}
              letter={STRATEGY_LETTER[key]}
              variant={data[key]}
              hint={STRATEGY_HINT[key]}
              active={strategy === key}
              recommended={data.best_variant.strategy === key}
              onClick={() => onStrategyChange(key)}
            />
          ))}
        </div>
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs font-semibold tracking-wide text-amber-900 uppercase">
            🏆 Versão recomendada: {STRATEGY_LETTER[data.best_variant.strategy]} —{' '}
            {data.best_variant.label}
          </p>
          <p className="mt-1 text-sm text-amber-900">{data.best_variant.reason}</p>
        </div>
      </Card>

      <Card
        title={`O que muda no resumo — versão ${STRATEGY_LETTER[strategy]}`}
        subtitle="Comparação lado a lado com o currículo base"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <DiffPane label="Currículo base" text={baseSummary} tone="neutral" />
          <DiffPane
            label={`${STRATEGY_LETTER[strategy]} — ${variant.strategy_label}`}
            text={variant.resume.summary}
            tone={variant.resume.summary === baseSummary ? 'neutral' : 'changed'}
          />
        </div>

        {variant.change_log.length > 0 && (
          <div className="mt-4 border-t border-zinc-100 pt-3">
            <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-600 uppercase">
              Alterações aplicadas
            </h3>
            <ul className="space-y-1 text-sm text-zinc-700">
              {variant.change_log.map((entry, position) => (
                <li key={`${position}-${entry}`} className="flex gap-2">
                  <span className="text-zinc-400">–</span>
                  <span>{entry}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      <section>
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-wide text-zinc-900 uppercase">
            Pré-visualização — versão {STRATEGY_LETTER[strategy]} ({variant.strategy_label})
          </h2>
          <p className="text-xs text-zinc-500">
            {variant.version_label} · base {variant.base_version} preservada
          </p>
        </div>
        <ResumePreview resume={effectiveResume} />
      </section>

      <Card
        title="Editar habilidades desta versão"
        subtitle="Ajuste rápido só para esta geração — não altera o currículo base. Depois de editar, clique em Reanalisar para recalcular match, validação e recomendação."
      >
        <div className="space-y-4">
          {skillCategories.map((category) => (
            <SkillCategoryEditor
              key={category.id}
              category={category}
              onAdd={(term) => handleAddSkill(category.id, term)}
              onRemove={(term) => handleRemoveSkill(category.id, term)}
            />
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-zinc-100 pt-4">
          <Button variant="secondary" onClick={handleRevalidate} disabled={revalidating}>
            {revalidating ? 'Reanalisando…' : 'Reanalisar'}
          </Button>
          <p className="text-xs text-zinc-500">
            {revalidating
              ? 'Recalculando match, validação e recomendação…'
              : hasPendingEdits
                ? 'Há edições ainda não reanalisadas.'
                : recomputed
                  ? 'Match, validação e recomendação atualizados com as edições.'
                  : 'Edite as habilidades acima e clique em Reanalisar.'}
          </p>
        </div>
        {revalidateError && (
          <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
            {revalidateError}
          </p>
        )}
        {recomputed && effectiveRecommendation.recommended && (
          <p className="mt-3 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
            Depois da edição, o perfil detectado ainda é {effectiveRecommendation.archetype_label}.
          </p>
        )}
      </Card>

      <ValidationPanel
        validation={effectiveValidation}
        autoFixes={variant.auto_fixes}
        changeLog={variant.change_log}
      />

      <Card>
        {!effectiveValidation.is_valid && !hasPendingEdits && (
          <p className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Atenção: há informação sem respaldo no currículo base (veja a validação acima). Você
            pode gerar o PDF mesmo assim — a decisão é sua.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-4">
          <Button
            onClick={() => onGeneratePdf(effectiveResume)}
            disabled={generatingPdf || hasPendingEdits}
          >
            {generatingPdf ? 'Gerando PDF…' : `Aprovar e gerar PDF (versão ${STRATEGY_LETTER[strategy]})`}
          </Button>
          <p className="text-xs text-zinc-500">
            {hasPendingEdits
              ? 'Reanalise as edições de habilidades antes de gerar o PDF.'
              : `Arquivo: ${data.pdf_filename}`}
          </p>
        </div>
        {pdfError && (
          <p className="mt-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
            {pdfError}
          </p>
        )}
      </Card>
    </div>
  );
}

function VariantCard({
  letter,
  variant,
  hint,
  active,
  recommended,
  onClick,
}: {
  letter: string;
  variant: Variant;
  hint: string;
  active: boolean;
  recommended: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`relative rounded-md border p-4 text-left transition-colors ${
        active ? 'border-zinc-900 bg-zinc-50' : 'border-zinc-200 hover:border-zinc-300'
      }`}
    >
      {recommended && (
        <span className="absolute -top-2 right-3 rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-semibold tracking-wide text-white uppercase">
          ⭐ Recomendada
        </span>
      )}
      <span className="block text-sm font-semibold text-zinc-900">
        Versão {letter} — {variant.strategy_label}
      </span>
      <span className="mt-1 block text-xs leading-relaxed text-zinc-600">{hint}</span>
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-700">
        <span>
          <span className="font-semibold tabular-nums">{variant.validation.score}%</span> match
        </span>
        <span>
          <span className="font-semibold tabular-nums">{variant.validation.ats_quality}%</span> ATS
        </span>
        <span className={variant.validation.is_valid ? 'text-emerald-700' : 'text-rose-700'}>
          {variant.validation.is_valid ? 'válida' : 'revisar'}
        </span>
      </div>
    </button>
  );
}

function SkillCategoryEditor({
  category,
  onAdd,
  onRemove,
}: {
  category: ResumeSkillCategory;
  onAdd: (term: string) => void;
  onRemove: (term: string) => void;
}) {
  const [draft, setDraft] = useState('');

  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold text-zinc-700">{category.label}</p>
      <div className="flex flex-wrap gap-2">
        {category.items.length === 0 && (
          <span className="text-xs text-zinc-400">Nenhuma habilidade.</span>
        )}
        {category.items.map((item) => (
          <span
            key={item}
            className="inline-flex items-center gap-1.5 rounded border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-700"
          >
            {item}
            <button
              type="button"
              onClick={() => onRemove(item)}
              aria-label={`Remover ${item}`}
              className="text-zinc-400 hover:text-rose-600"
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!draft.trim()) return;
          onAdd(draft);
          setDraft('');
        }}
        className="mt-1.5 flex gap-2"
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Adicionar habilidade…"
          maxLength={80}
          className="min-w-40 flex-1 rounded-md border border-zinc-300 px-2 py-1 text-xs outline-none focus:border-zinc-900"
        />
        <Button type="submit" variant="secondary" disabled={!draft.trim()}>
          Adicionar
        </Button>
      </form>
    </div>
  );
}

function DiffPane({
  label,
  text,
  tone,
}: {
  label: string;
  text: string;
  tone: 'neutral' | 'changed';
}) {
  return (
    <div
      className={`rounded-md border p-3 ${
        tone === 'changed' ? 'border-emerald-200 bg-emerald-50/50' : 'border-zinc-200'
      }`}
    >
      <p className="mb-1.5 text-xs font-semibold tracking-wide text-zinc-500 uppercase">
        {label}
      </p>
      <p className="text-[13px] leading-relaxed text-zinc-800">{text}</p>
    </div>
  );
}
