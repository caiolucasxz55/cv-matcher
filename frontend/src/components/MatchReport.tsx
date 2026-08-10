import type { JobAnalysis, MatchSummary } from '@/lib/api-types';
import { Card, Tag } from './ui';

const SENIORITY_LABEL: Record<string, string> = {
  estagio: 'Estágio',
  junior: 'Júnior',
  pleno: 'Pleno',
  senior: 'Sênior',
  especialista: 'Especialista',
  lead: 'Lead / Liderança técnica',
  nao_identificada: 'Não identificada',
};

export function MatchReport({
  analysis,
  match,
}: {
  analysis: JobAnalysis;
  match: MatchSummary;
}) {
  return (
    <Card title="Job match" subtitle="Comparação entre os requisitos da vaga e o currículo base">
      <dl className="mb-5 grid gap-3 text-sm sm:grid-cols-3">
        <Info label="Empresa" value={analysis.company || '—'} />
        <Info label="Cargo" value={analysis.job_title} />
        <Info label="Senioridade" value={SENIORITY_LABEL[analysis.seniority] ?? '—'} />
      </dl>

      <TermGroup
        title="Match forte"
        hint="tecnologia com experiência profissional comprovada"
        tone="strong"
        terms={match.strong.map((item) => item.term)}
      />
      <TermGroup
        title="Match médio"
        hint="consta nas habilidades/cursos, sem experiência profissional explícita"
        tone="medium"
        terms={match.medium.map((item) => item.term)}
      />
      <TermGroup
        title="Match fraco"
        hint="apenas conceito relacionado — não foi adicionado ao currículo"
        tone="weak"
        terms={match.weak.map((item) =>
          item.related_via ? `${item.term} (via ${item.related_via})` : item.term,
        )}
      />
      <TermGroup
        title="Keywords da vaga não encontradas"
        hint="lacunas reais — o sistema nunca as adiciona ao currículo"
        tone="missing"
        terms={match.missing.map((item) => item.term)}
      />

      {analysis.responsibilities.length > 0 && (
        <div className="mt-5">
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">
            Responsabilidades identificadas
          </h3>
          <ul className="space-y-1 text-sm text-zinc-700">
            {analysis.responsibilities.slice(0, 6).map((item) => (
              <li key={item} className="flex gap-2">
                <span className="text-zinc-400">–</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.ai_notes.length > 0 && (
        <p className="mt-4 text-xs text-zinc-500">{analysis.ai_notes.join(' ')}</p>
      )}
    </Card>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-zinc-500">{label}</dt>
      <dd className="font-medium text-zinc-900">{value}</dd>
    </div>
  );
}

function TermGroup({
  title,
  hint,
  tone,
  terms,
}: {
  title: string;
  hint: string;
  tone: 'strong' | 'medium' | 'weak' | 'missing';
  terms: readonly string[];
}) {
  if (terms.length === 0) return null;
  return (
    <div className="mb-4">
      <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">
        {title} <span className="font-normal normal-case">— {hint}</span>
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {terms.map((term) => (
          <Tag key={term} tone={tone}>
            {term}
          </Tag>
        ))}
      </div>
    </div>
  );
}
