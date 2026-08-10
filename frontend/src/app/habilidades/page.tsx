'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Button, Card } from '@/components/ui';
import { addSkill, getSkills, removeSkill } from '@/lib/api';
import type { SkillsOverview } from '@/lib/api-types';

export default function HabilidadesPage() {
  const [overview, setOverview] = useState<SkillsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    getSkills()
      .then(setOverview)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Erro inesperado.'))
      .finally(() => setLoading(false));
  }, []);

  async function handleAdd(categoryId: string): Promise<void> {
    const term = (draft[categoryId] ?? '').trim();
    if (!term) return;

    setError(null);
    setBusy(`add:${categoryId}`);
    try {
      setOverview(await addSkill(categoryId, term));
      setDraft((prev) => ({ ...prev, [categoryId]: '' }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setBusy(null);
    }
  }

  async function handleRemove(categoryId: string, term: string): Promise<void> {
    setError(null);
    setBusy(`remove:${categoryId}:${term}`);
    try {
      setOverview(await removeSkill(categoryId, term));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Erro inesperado.');
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-5 py-12">
      <header className="mb-10">
        <Link
          href="/"
          className="text-xs text-zinc-500 underline underline-offset-2 hover:text-zinc-800"
        >
          ← Voltar
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900">
          Habilidades técnicas
        </h1>
        <p className="mt-1 text-sm text-zinc-600">
          Digite qualquer habilidade que você tem — não precisa estar numa lista fixa. As
          sugestões que aparecem ao digitar já são reconhecidas automaticamente em descrições de
          vaga; habilidades fora delas (marcadas com{' '}
          <span className="text-amber-500">•</span>) entram no currículo normalmente, só não
          contam no matching automático.
        </p>
      </header>

      {error && (
        <p className="mb-6 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          {error}
        </p>
      )}

      {loading && <p className="text-sm text-zinc-500">Carregando…</p>}

      {overview && (
        <div className="space-y-6">
          {overview.categories.map((category) => (
            <Card key={category.id} title={category.label}>
              <div className="flex flex-wrap gap-2">
                {category.items.length === 0 && (
                  <span className="text-xs text-zinc-400">Nenhuma habilidade.</span>
                )}
                {category.items.map((item) => (
                  <span
                    key={item.name}
                    title={
                      item.recognized
                        ? undefined
                        : 'Fora do vocabulário reconhecido: aparece no currículo, mas não entra no matching automático com vagas.'
                    }
                    className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs ${
                      item.recognized
                        ? 'border-zinc-200 bg-zinc-50 text-zinc-700'
                        : 'border-dashed border-zinc-300 bg-white text-zinc-600'
                    }`}
                  >
                    {!item.recognized && (
                      <span aria-hidden className="text-amber-500">
                        •
                      </span>
                    )}
                    {item.name}
                    {item.custom && (
                      <button
                        type="button"
                        onClick={() => handleRemove(category.id, item.name)}
                        disabled={busy === `remove:${category.id}:${item.name}`}
                        aria-label={`Remover ${item.name}`}
                        className="text-zinc-400 hover:text-rose-600 disabled:opacity-50"
                      >
                        ×
                      </button>
                    )}
                  </span>
                ))}
              </div>

              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  handleAdd(category.id);
                }}
                className="mt-4 flex flex-wrap items-center gap-2 border-t border-zinc-100 pt-4"
              >
                <input
                  list={`skills-${category.id}`}
                  value={draft[category.id] ?? ''}
                  onChange={(event) =>
                    setDraft((prev) => ({ ...prev, [category.id]: event.target.value }))
                  }
                  placeholder="Digite uma habilidade…"
                  maxLength={80}
                  className="min-w-55 flex-1 rounded-md border border-zinc-300 px-2 py-1.5 text-xs outline-none focus:border-zinc-900"
                />
                <datalist id={`skills-${category.id}`}>
                  {overview.available_terms.map((term) => (
                    <option key={term} value={term} />
                  ))}
                </datalist>
                <Button
                  type="submit"
                  variant="secondary"
                  disabled={!(draft[category.id] ?? '').trim() || busy === `add:${category.id}`}
                >
                  {busy === `add:${category.id}` ? 'Adicionando…' : 'Adicionar'}
                </Button>
              </form>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
