"""Gerador de PDF com ReportLab.

Layout ATS-friendly:
 - texto real e selecionavel (nunca imagem)
 - fonte padrao Helvetica, sem fontes exoticas
 - coluna unica, sem tabelas nem icones
 - titulos de secao explicitos e em texto
 - links clicaveis, mas com o rotulo textual sempre presente
 - nenhum score ou metadado interno da IA
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.resume.models import Resume

_TEXT = HexColor("#1A1A1A")
_MUTED = HexColor("#555555")
_RULE = HexColor("#C8C8C8")
_LINK = HexColor("#1A4F8A")

_NAME = ParagraphStyle(
    "Name", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=_TEXT, spaceAfter=2
)
_HEADLINE = ParagraphStyle(
    "Headline", fontName="Helvetica", fontSize=10, leading=13, textColor=HexColor("#444444")
)
_CONTACT = ParagraphStyle(
    "Contact", fontName="Helvetica", fontSize=8.5, leading=11, textColor=HexColor("#333333")
)
_SECTION = ParagraphStyle(
    "Section",
    fontName="Helvetica-Bold",
    fontSize=9.5,
    leading=12,
    textColor=_TEXT,
    spaceBefore=9,
    spaceAfter=2,
)
_BODY = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=9, leading=12.5, textColor=_TEXT, alignment=TA_JUSTIFY
)
_ROLE = ParagraphStyle(
    "Role", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=_TEXT
)
_META = ParagraphStyle("Meta", fontName="Helvetica", fontSize=8.5, leading=11, textColor=_MUTED)
_BULLET = ParagraphStyle(
    "Bullet",
    fontName="Helvetica",
    fontSize=9,
    leading=12.5,
    textColor=_TEXT,
    alignment=TA_JUSTIFY,
)


@dataclass(frozen=True)
class PdfGenerationResult:
    content: bytes
    filename: str

    @property
    def byte_length(self) -> int:
        return len(self.content)


def _esc(value: str) -> str:
    return html.escape(value, quote=False)


def _section_title(label: str) -> list:
    return [
        Paragraph(_esc(label.upper()), _SECTION),
        HRFlowable(width="100%", thickness=0.7, color=_RULE, spaceBefore=1, spaceAfter=4),
    ]


def _bullet_list(texts: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(_esc(text), _BULLET), leftIndent=10) for text in texts],
        bulletType="bullet",
        start="-",
        bulletFontName="Helvetica",
        bulletFontSize=9,
        leftIndent=10,
        spaceBefore=1,
    )


def render_resume_pdf(resume: Resume, filename: str) -> PdfGenerationResult:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=11 * mm,
        title=f"Currículo — {resume.basics.name}",
        author=resume.basics.name,
        subject="Currículo profissional",
        creator="CV Matcher",
    )

    story: list = [
        Paragraph(_esc(resume.basics.name), _NAME),
        Paragraph(_esc(resume.basics.headline), _HEADLINE),
    ]

    contact = "  |  ".join(
        part
        for part in (resume.basics.location, resume.basics.email, resume.basics.phone)
        if part
    )
    story.append(Paragraph(_esc(contact), _CONTACT))

    # Links clicaveis mantendo o rotulo textual (requisito ATS).
    if resume.basics.links:
        link_markup = "  |  ".join(
            f'<link href="{_esc(link.url)}" color="#{_LINK.hexval()[2:]}">{_esc(link.label)}</link>'
            for link in resume.basics.links
        )
        story.append(Paragraph(link_markup, _CONTACT))

    story.append(Spacer(1, 4))

    story.extend(_section_title("Resumo profissional"))
    story.append(Paragraph(_esc(resume.summary), _BODY))

    story.extend(_section_title("Formação"))
    for education in resume.education:
        story.append(Paragraph(_esc(education.degree), _ROLE))
        story.append(
            Paragraph(f"{_esc(education.institution)}  ·  {_esc(education.period)}", _META)
        )

    story.extend(_section_title("Experiência profissional"))
    for experience in resume.experience:
        block: list = [
            Paragraph(f"{_esc(experience.role)} — {_esc(experience.company)}", _ROLE),
            Paragraph(f"{_esc(experience.location)}  ·  {_esc(experience.period)}", _META),
            _bullet_list([bullet.text for bullet in experience.bullets]),
            Spacer(1, 3),
        ]
        story.append(KeepTogether(block))

    story.extend(_section_title("Habilidades técnicas"))
    for category in resume.skill_categories:
        story.append(
            Paragraph(
                f"<b>{_esc(category.label)}:</b> {_esc(', '.join(category.items))}", _BODY
            )
        )

    if resume.projects:
        story.extend(_section_title("Projetos"))
        for project in resume.projects:
            block = [
                Paragraph(_esc(project.name), _ROLE),
                Paragraph(_esc(project.description), _BODY),
            ]
            if project.bullets:
                block.append(_bullet_list([bullet.text for bullet in project.bullets]))
            block.append(Spacer(1, 2))
            story.append(KeepTogether(block))

    if resume.courses:
        story.extend(_section_title("Cursos"))
        story.append(_bullet_list([course.name for course in resume.courses]))

    if resume.languages:
        story.extend(_section_title("Idiomas"))
        story.append(
            _bullet_list([f"{lang.name}: {lang.level}" for lang in resume.languages])
        )

    doc.build(story)
    return PdfGenerationResult(content=buffer.getvalue(), filename=filename)
