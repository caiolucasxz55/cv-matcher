"""Currículo versão Gupy — parágrafo de atividades e lista de palavras-chave
não podem inventar nada: só reordenam o texto/habilidades já existentes no
currículo base."""

from __future__ import annotations

from app.resume.base_resume import BASE_RESUME
from app.resume.gupy_format import build_activity_paragraph, build_keyword_list

EXPERIENCE = BASE_RESUME.experience[0]


class TestActivityParagraph:
    def test_e_concatenacao_literal_dos_bullets_sem_nenhuma_palavra_nova(self):
        paragraph = build_activity_paragraph(EXPERIENCE, relevance={})

        bullet_texts = [bullet.text for bullet in EXPERIENCE.bullets]
        for text in bullet_texts:
            assert text in paragraph

        # Comprimento exato = soma dos bullets + um espaço entre cada um.
        # Prova que nada foi acrescentado ou reescrito, só concatenado.
        expected_length = sum(len(text) for text in bullet_texts) + (len(bullet_texts) - 1)
        assert len(paragraph) == expected_length

    def test_ordem_muda_conforme_relevancia_da_vaga(self):
        frontend_bullet = next(b.text for b in EXPERIENCE.bullets if b.id == "exp-inoltra-b1")
        backend_bullet = next(b.text for b in EXPERIENCE.bullets if b.id == "exp-inoltra-b2")

        frontend_first = build_activity_paragraph(
            EXPERIENCE, relevance={"Frontend": 1.0, "UI/UX": 1.0, "Usabilidade": 1.0}
        )
        backend_first = build_activity_paragraph(
            EXPERIENCE, relevance={"Python": 1.0, "FastAPI": 1.0, "Backend": 1.0}
        )

        assert frontend_first.index(frontend_bullet) < frontend_first.index(backend_bullet)
        assert backend_first.index(backend_bullet) < backend_first.index(frontend_bullet)

    def test_sem_relevancia_mantem_ordem_original_do_curriculo_base(self):
        paragraph = build_activity_paragraph(EXPERIENCE, relevance={})
        bullet_texts = [bullet.text for bullet in EXPERIENCE.bullets]
        assert paragraph == " ".join(bullet_texts)


class TestKeywordList:
    def test_so_contem_habilidades_ja_declaradas_no_curriculo_base(self):
        keywords = build_keyword_list(BASE_RESUME.skill_categories, relevance={})

        all_declared = {
            item for category in BASE_RESUME.skill_categories for item in category.items
        }
        assert set(keywords) <= all_declared
        # Nada e perdido nem duplicado: mesma contagem que o total declarado.
        assert len(keywords) == len(all_declared)

    def test_ordenada_por_relevancia_para_a_vaga(self):
        keywords = build_keyword_list(
            BASE_RESUME.skill_categories, relevance={"Python": 1.0, "FastAPI": 0.8}
        )
        assert keywords.index("Python") < keywords.index("React")
        assert keywords.index("FastAPI") < keywords.index("Angular")
        # Entre os dois priorizados, o de maior peso vem primeiro.
        assert keywords.index("Python") < keywords.index("FastAPI")

    def test_sem_relevancia_mantem_ordem_original_das_categorias(self):
        keywords = build_keyword_list(BASE_RESUME.skill_categories, relevance={})
        expected = [item for category in BASE_RESUME.skill_categories for item in category.items]
        assert keywords == expected
