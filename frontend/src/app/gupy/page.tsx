'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Button, Card, Field } from '@/components/ui';
import { buildGupyFormat } from '@/lib/api';
import type { GupyResponse } from '@/lib/api-types';

export default function GupyPage() {
  const [company, setCompany] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [description, setDescription] = useState('');

  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GupyResponse | null>(null);

  const canGenerate = description.trim().length >= 30 && !generating;

  async function handleGenerate(): Promise<void> {
    setGenerating(true);
    setError(null);
    setResult(null);
    try {
      const response = await buildGupyFormat({
        description,
        company: company.trim() || undefined,
        job_title: jobTitle.trim() || undefined,
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setGenerating(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-5 py-12">
      <header className="mb-10">
        <Link
          href="/"
          className="text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-800"
        >
          ← Voltar ao início
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900">
          Currículo versão Gupy
        </h1>
        <p className="mt-1 text-sm text-zinc-600">
          A Gupy não aceita currículo em PDF — você preenche campos separados. Cole a vaga abaixo
          e gere o parágrafo de "Descrição de atividades" e a lista de palavras-chave prontos
          para colar, com ênfase no que mais importa para essa vaga. Nada é inventado: só o texto
          e as habilidades que já existem no seu currículo, reordenados.
        </p>
      </header>

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
          <Button onClick={handleGenerate} disabled={!canGenerate}>
            {generating ? 'Gerando…' : 'Gerar currículo Gupy'}
          </Button>
          {generating && (
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

      {result && (
        <div className="mt-8 space-y-6">
          <p className="text-xs text-zinc-500">
            Aderência à vaga:{' '}
            <span className="font-semibold text-zinc-800">{result.match_score}%</span>
            {result.role && (
              <>
                {' '}
                · atividades de {result.role} @ {result.company}
              </>
            )}
          </p>

          <CopyCard
            title="Descrição de atividades"
            subtitle="Cole no campo de experiência profissional da Gupy."
            text={result.activity_description}
            rows={7}
          />

          <CopyCard
            title="Palavras-chave / Habilidades"
            subtitle="Cadastre como tags de habilidades na Gupy, na ordem sugerida (mais relevante primeiro)."
            text={result.keywords.join('\n')}
            rows={10}
          />
        </div>
      )}
    </main>
  );
}

function CopyCard({
  title,
  subtitle,
  text,
  rows,
}: {
  title: string;
  subtitle: string;
  text: string;
  rows: number;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard indisponível (ex.: contexto não seguro) — o texto continua
      // selecionável manualmente no campo abaixo.
    }
  }

  return (
    <Card title={title} subtitle={subtitle}>
      <textarea
        readOnly
        value={text}
        rows={rows}
        onFocus={(event) => event.currentTarget.select()}
        className="w-full resize-y rounded-md border border-zinc-300 bg-zinc-50 px-3 py-2 font-mono text-xs leading-relaxed outline-none"
      />
      <div className="mt-3">
        <Button variant="secondary" onClick={handleCopy}>
          {copied ? 'Copiado ✓' : 'Copiar'}
        </Button>
      </div>
    </Card>
  );
}
