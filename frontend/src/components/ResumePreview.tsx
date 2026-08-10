import type { Resume } from '@/lib/api-types';

/**
 * Pre-visualizacao do curriculo adaptado. Espelha a estrutura do PDF — nao
 * exibe nenhum score nem metadado interno da IA.
 */
export function ResumePreview({ resume }: { resume: Resume }) {
  return (
    <article className="rounded-lg border border-zinc-200 bg-white p-8 text-[13px] leading-relaxed text-zinc-800">
      <header className="mb-5">
        <h1 className="text-xl font-bold text-zinc-900">{resume.basics.name}</h1>
        <p className="text-zinc-600">{resume.basics.headline}</p>
        <p className="mt-1 text-xs text-zinc-500">
          {[resume.basics.location, resume.basics.email, resume.basics.phone]
            .filter(Boolean)
            .join('  |  ')}
        </p>
        <p className="mt-1 flex gap-3 text-xs">
          {resume.basics.links.map((link) => (
            <span key={link.label} className="text-sky-700">
              {link.label}
            </span>
          ))}
        </p>
      </header>

      <Section title="Resumo profissional">
        <p className="text-justify">{resume.summary}</p>
      </Section>

      <Section title="Formação">
        {resume.education.map((education) => (
          <div key={education.id} className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-semibold text-zinc-900">{education.degree}</p>
            <p className="text-xs text-zinc-500">{education.period}</p>
            <p className="w-full text-xs text-zinc-500">{education.institution}</p>
          </div>
        ))}
      </Section>

      <Section title="Experiência profissional">
        {resume.experience.map((experience) => (
          <div key={experience.id} className="mb-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-semibold text-zinc-900">
                {experience.role} — {experience.company}
              </p>
              <p className="text-xs text-zinc-500">{experience.period}</p>
            </div>
            <p className="text-xs text-zinc-500">{experience.location}</p>
            <ul className="mt-1.5 space-y-1.5">
              {experience.bullets.map((bullet) => (
                <li key={bullet.id} className="flex gap-2">
                  <span className="text-zinc-400">–</span>
                  <span className="text-justify">{bullet.text}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Section>

      <Section title="Habilidades técnicas">
        <dl className="space-y-1">
          {resume.skill_categories.map((category) => (
            <div key={category.id} className="flex flex-wrap gap-2">
              <dt className="w-32 shrink-0 font-semibold text-zinc-900">{category.label}:</dt>
              <dd className="flex-1">{category.items.join(', ')}</dd>
            </div>
          ))}
        </dl>
      </Section>

      {resume.projects.length > 0 && (
        <Section title="Projetos">
          {resume.projects.map((project) => (
            <div key={project.id} className="mb-2">
              <p className="font-semibold text-zinc-900">{project.name}</p>
              <p className="text-justify">{project.description}</p>
              {project.bullets.length > 0 && (
                <ul className="mt-1.5 space-y-1.5">
                  {project.bullets.map((bullet) => (
                    <li key={bullet.id} className="flex gap-2">
                      <span className="text-zinc-400">–</span>
                      <span className="text-justify">{bullet.text}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </Section>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        <Section title="Cursos">
          <ul className="space-y-1">
            {resume.courses.map((course) => (
              <li key={course.id} className="flex gap-2">
                <span className="text-zinc-400">–</span>
                <span>{course.name}</span>
              </li>
            ))}
          </ul>
        </Section>
        <Section title="Idiomas">
          <ul className="space-y-1">
            {resume.languages.map((language) => (
              <li key={language.name} className="flex gap-2">
                <span className="text-zinc-400">–</span>
                <span>
                  {language.name}: {language.level}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      </div>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <h2 className="mb-2 border-b border-zinc-200 pb-1 text-xs font-bold tracking-wider text-zinc-900 uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}
