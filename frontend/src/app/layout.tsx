import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'CV Matcher — Adapte seu currículo para cada vaga',
  description:
    'Ferramenta de otimização de currículo baseada em evidências: analisa a vaga, compara com o currículo base e adapta a ênfase sem inventar experiência.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-white text-zinc-900">{children}</body>
    </html>
  );
}
