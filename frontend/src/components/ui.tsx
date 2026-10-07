import Link from 'next/link';
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
    <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
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
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium tracking-wide text-zinc-500 uppercase">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${tone}`}>{value}%</p>
      <p className="mt-1 text-xs text-zinc-500">{caption}</p>
    </div>
  );
}

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md';

const BUTTON_VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: 'bg-zinc-900 text-white hover:bg-zinc-700',
  secondary: 'border border-zinc-300 bg-white text-zinc-800 hover:border-zinc-400 hover:bg-zinc-50',
  ghost: 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900',
  danger: 'border border-rose-200 bg-white text-rose-700 hover:bg-rose-50',
};

const BUTTON_SIZE_CLASS: Record<ButtonSize, string> = {
  md: 'px-4 py-2.5 text-sm',
  sm: 'px-3 py-1.5 text-xs',
};

export function Button({
  children,
  onClick,
  disabled,
  loading = false,
  variant = 'primary',
  size = 'md',
  type = 'button',
  icon,
  fullWidth = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
  type?: 'button' | 'submit';
  icon?: ReactNode;
  fullWidth?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_SIZE_CLASS[size]} ${BUTTON_VARIANT_CLASS[variant]} ${fullWidth ? 'w-full' : ''}`}
    >
      {loading ? <Spinner className="h-4 w-4" /> : icon}
      {children}
    </button>
  );
}

/** Botão de "voltar" consistente: navega por rota (`href`) ou executa uma
 * ação local (`onClick`, ex.: reset de estado dentro da mesma página). */
export function BackButton({
  href,
  onClick,
  children = 'Voltar',
}: {
  href?: string;
  onClick?: () => void;
  children?: ReactNode;
}) {
  const className =
    'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900';
  if (href) {
    return (
      <Link href={href} className={className}>
        <IconChevronLeft className="h-3.5 w-3.5" />
        {children}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={className}>
      <IconChevronLeft className="h-3.5 w-3.5" />
      {children}
    </button>
  );
}

export function IconButton({
  label,
  onClick,
  disabled,
  tone = 'neutral',
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: 'neutral' | 'danger';
  children: ReactNode;
}) {
  const toneClass =
    tone === 'danger'
      ? 'text-zinc-400 hover:bg-rose-50 hover:text-rose-600'
      : 'text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700';
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded transition-colors disabled:opacity-50 ${toneClass}`}
    >
      {children}
    </button>
  );
}

/** Indicador de etapas do fluxo (vaga → perguntas → match → versões), usado
 * nas duas telas que rodam esse fluxo (CV Matcher atual e Novo). */
export function StepIndicator<T extends string>({
  steps,
  active,
}: {
  steps: readonly { key: T; label: string }[];
  active: T;
}) {
  const activeIndex = steps.findIndex((item) => item.key === active);
  return (
    <ol className="mt-4 flex flex-wrap gap-2 text-xs">
      {steps.map((item, index) => (
        <li
          key={item.key}
          className={`rounded-full border px-2.5 py-1 font-medium ${
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

export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-80"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export function IconChevronLeft({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

export function IconCheck({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

export function IconCopy({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
    </svg>
  );
}

export function IconX({ className = 'h-3.5 w-3.5' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

export function IconPlus({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
