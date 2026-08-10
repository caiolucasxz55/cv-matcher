'use client';

import { useState } from 'react';
import type { ConfirmationAnswer, GapQuestion, SkillConfirmationInput } from '@/lib/api-types';
import { Button, Card } from './ui';

/**
 * Regra 2 — nunca assumir gap sem perguntar. Para cada requisito da vaga sem
 * evidência direta no currículo base, a pessoa escolhe: tem experiência, não
 * tem, ou não tem certeza. Só "Sim" pode entrar na versão adaptada.
 */
export function GapQuestions({
  questions,
  onSubmit,
  submitting,
}: {
  questions: readonly GapQuestion[];
  onSubmit: (confirmations: SkillConfirmationInput[]) => void;
  submitting: boolean;
}) {
  const [answers, setAnswers] = useState<Record<string, ConfirmationAnswer>>(() =>
    Object.fromEntries(
      questions.filter((q) => q.answer).map((q) => [q.term, q.answer as ConfirmationAnswer]),
    ),
  );
  const [contexts, setContexts] = useState<Record<string, string>>({});

  const answeredCount = Object.keys(answers).length;

  function setAnswer(term: string, answer: ConfirmationAnswer): void {
    setAnswers((prev) => ({ ...prev, [term]: answer }));
  }

  function handleSubmit(): void {
    const confirmations: SkillConfirmationInput[] = [];
    for (const question of questions) {
      const answer = answers[question.term];
      if (!answer) continue;
      confirmations.push({
        term: question.term,
        answer,
        context: answer === 'yes' ? (contexts[question.term] ?? '') : '',
      });
    }
    onSubmit(confirmations);
  }

  return (
    <Card
      title="Antes de continuar"
      subtitle="A vaga pede algumas coisas que não aparecem no seu currículo base. Isso não significa que você não tenha — responda e a gente ajusta o match certo."
    >
      <div className="space-y-4">
        {questions.map((question) => (
          <div key={question.term} className="rounded-md border border-zinc-200 p-4">
            <p className="text-sm text-zinc-900">
              Esta vaga {question.kind === 'required' ? 'exige' : 'valoriza'} experiência com{' '}
              <span className="font-semibold">{question.term}</span>. Você possui experiência com
              essa tecnologia?
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <AnswerButton
                label="Sim, tenho experiência"
                active={answers[question.term] === 'yes'}
                onClick={() => setAnswer(question.term, 'yes')}
              />
              <AnswerButton
                label="Não tenho experiência"
                active={answers[question.term] === 'no'}
                onClick={() => setAnswer(question.term, 'no')}
              />
              <AnswerButton
                label="Não tenho certeza"
                active={answers[question.term] === 'unsure'}
                onClick={() => setAnswer(question.term, 'unsure')}
              />
            </div>
            {answers[question.term] === 'yes' && (
              <input
                value={contexts[question.term] ?? ''}
                onChange={(event) =>
                  setContexts((prev) => ({ ...prev, [question.term]: event.target.value }))
                }
                placeholder="Onde/como adquiriu essa experiência? (opcional)"
                maxLength={400}
                className="mt-3 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-zinc-900"
              />
            )}
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-zinc-100 pt-4">
        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Aplicando…' : 'Confirmar e continuar'}
        </Button>
        <p className="text-xs text-zinc-500">
          {answeredCount} de {questions.length} respondida(s). Perguntas sem resposta ficam como
          requisito não confirmado — nunca entram no currículo.
        </p>
      </div>
    </Card>
  );
}

function AnswerButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
        active
          ? 'border-zinc-900 bg-zinc-900 text-white'
          : 'border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50'
      }`}
    >
      {label}
    </button>
  );
}
