import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { AppHeader } from '@/components/AppHeader';
import './globals.css';

export const metadata: Metadata = {
  title: 'CV Matcher — Adapte seu currículo para cada vaga',
  description:
    'Ferramenta de otimização de currículo baseada em evidências: analisa a vaga, compara com o currículo base e adapta a ênfase sem inventar experiência.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-zinc-50 text-zinc-900">
        <AppHeader />
        {children}
      </body>
    </html>
  );
}
