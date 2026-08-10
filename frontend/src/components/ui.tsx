import type { ReactNode } from 'react';

export function Card({
  title,
  subtitle,
  children,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5">
      {title && (
        <header className="mb-4">
          <h2 className="text-sm font-semibold tracking-wide text-zinc-900 uppercase">{title}</h2>
          {subtitle && <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-zinc-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-zinc-400">{hint}</span>}
    </label>
  );
}

const TONE_CLASS = {
  neutral: 'bg-zinc-100 text-zinc-700 border-zinc-200',
  strong: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  medium: 'bg-sky-50 text-sky-800 border-sky-200',
  weak: 'bg-amber-50 text-amber-800 border-amber-200',
  missing: 'bg-rose-50 text-rose-800 border-rose-200',
} as const;

export type Tone = keyof typeof TONE_CLASS;

export function Tag({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs ${TONE_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}

export function ScoreCard({
  label,
  value,
  caption,
}: {
  label: string;
  value: number;
  caption: string;
}) {
  const tone =
    value >= 80 ? 'text-emerald-700' : value >= 60 ? 'text-sky-700' : 'text-amber-700';
  return (
    <div className="rounded-lg border border-zinc-200 p-4">
      <p className="text-xs font-medium tracking-wide text-zinc-500 uppercase">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${tone}`}>{value}%</p>
      <p className="mt-1 text-xs text-zinc-500">{caption}</p>
    </div>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  variant = 'primary',
  type = 'button',
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary';
  type?: 'button' | 'submit';
}) {
  const base =
    'inline-flex items-center justify-center rounded-md px-4 py-2.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50';
  const styles =
    variant === 'primary'
      ? 'bg-zinc-900 text-white hover:bg-zinc-700'
      : 'border border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50';
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${styles}`}>
      {children}
    </button>
  );
}
