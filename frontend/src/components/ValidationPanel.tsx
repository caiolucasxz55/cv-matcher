import type { ValidationResult } from '@/lib/api-types';
import { Card } from './ui';

export function ValidationPanel({
  validation,
  autoFixes,
  changeLog,
}: {
  validation: ValidationResult;
  autoFixes: readonly string[];
  changeLog: readonly string[];
}) {
  const checks = [
    {
      id: 'no-hallucination',
      label: 'Sem informações inventadas',
      passed: validation.hallucinations.length === 0,
      detail:
        validation.hallucinations.length === 0
          ? 'Nenhuma tecnologia, empresa ou métrica fora do currículo base.'
          : validation.hallucinations.map((item) => `${item.value} (${item.location})`).join('; '),
    },
    {
      id: 'supported-claims',
      label: 'Afirmações com respaldo factual',
      passed: validation.unsupported_claims.length === 0,
      detail:
        validation.unsupported_claims.length === 0
          ? 'Todo texto do currículo adaptado tem origem no currículo base.'
          : validation.unsupported_claims
              .map((item) => `${item.value} (${item.location})`)
              .join('; '),
    },
    {
      id: 'relevant-keywords',
      label: 'Keywords relevantes utilizadas',
      passed: validation.missing_relevant_keywords.length === 0,
      detail:
        validation.missing_relevant_keywords.length === 0
          ? 'Todas as keywords da vaga com evidência real aparecem no currículo.'
          : `Poderiam ser evidenciadas: ${validation.missing_relevant_keywords.join(', ')}.`,
    },
    // "Sem keyword stuffing" já vem em ats_checks — não duplicar aqui.
    ...validation.ats_checks.map((check) => ({
      id: check.id,
      label: check.label,
      passed: check.passed,
      detail: check.detail,
    })),
  ];

  return (
    <Card
      title="Validação"
      subtitle={`Validador: ${
        validation.validator === 'deterministic+ai'
          ? 'checagem determinística + auditoria por IA'
          : 'checagem determinística'
      }`}
    >
      <div
        className={`mb-4 rounded-md border p-3 text-sm ${
          validation.is_valid
            ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
            : 'border-rose-200 bg-rose-50 text-rose-900'
        }`}
      >
        {validation.is_valid
          ? 'Currículo adaptado válido — nenhuma informação sem respaldo encontrada.'
          : 'Atenção: há informação sem respaldo no currículo base — a geração de PDF não é mais bloqueada, mas revise antes de enviar.'}
      </div>

      <ul className="space-y-2 text-sm">
        {checks.map((check) => (
          <li key={check.id} className="flex gap-2">
            <span
              aria-hidden
              className={check.passed ? 'text-emerald-600' : 'text-rose-600'}
            >
              {check.passed ? '✓' : '✗'}
            </span>
            <span>
              <span className="font-medium text-zinc-900">{check.label}</span>
              <span className="sr-only">{check.passed ? ' (aprovado)' : ' (reprovado)'}</span>
              <span className="block text-xs text-zinc-500">{check.detail}</span>
            </span>
          </li>
        ))}
      </ul>

      {changeLog.length > 0 && (
        <Details title="O que foi adaptado" items={changeLog} />
      )}
      {autoFixes.length > 0 && <Details title="Correções automáticas aplicadas" items={autoFixes} />}
      {validation.recommendations.length > 0 && (
        <Details title="Recomendações" items={validation.recommendations} />
      )}
    </Card>
  );
}

function Details({ title, items }: { title: string; items: readonly string[] }) {
  return (
    <details className="mt-4 border-t border-zinc-100 pt-3">
      <summary className="cursor-pointer text-xs font-semibold tracking-wide text-zinc-600 uppercase">
        {title}
      </summary>
      <ul className="mt-2 space-y-1 text-sm text-zinc-700">
        {items.map((item, position) => (
          <li key={`${position}-${item}`} className="flex gap-2">
            <span className="text-zinc-400">–</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
