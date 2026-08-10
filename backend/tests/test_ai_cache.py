"""AsyncLRUCache (`app.ai.cache`) — cache exato usado pelos providers remotos
para não reprocessar o mesmo currículo/vaga em toda chamada de IA."""

from __future__ import annotations

import asyncio

import pytest

from app.ai.cache import AsyncLRUCache


@pytest.mark.anyio
async def test_reaproveita_resultado_para_a_mesma_chave():
    cache: AsyncLRUCache[int] = AsyncLRUCache()
    calls = 0

    async def compute() -> int:
        nonlocal calls
        calls += 1
        return 42

    first = await cache.get_or_compute("k", compute)
    second = await cache.get_or_compute("k", compute)

    assert first == second == 42
    assert calls == 1
    assert cache.stats.hits == 1
    assert cache.stats.misses == 1


@pytest.mark.anyio
async def test_chaves_diferentes_computam_separadamente():
    cache: AsyncLRUCache[str] = AsyncLRUCache()
    calls: list[str] = []

    async def compute(value: str):
        async def inner() -> str:
            calls.append(value)
            return value

        return inner

    await cache.get_or_compute("a", await compute("a"))
    await cache.get_or_compute("b", await compute("b"))

    assert calls == ["a", "b"]
    assert len(cache) == 2


@pytest.mark.anyio
async def test_chamadas_concorrentes_identicas_disparam_so_uma_computacao():
    cache: AsyncLRUCache[int] = AsyncLRUCache()
    calls = 0

    async def compute() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return 7

    results = await asyncio.gather(
        cache.get_or_compute("k", compute),
        cache.get_or_compute("k", compute),
        cache.get_or_compute("k", compute),
    )

    assert results == [7, 7, 7]
    assert calls == 1
    assert cache.stats.in_flight_joins == 2


@pytest.mark.anyio
async def test_lru_descarta_a_entrada_mais_antiga():
    cache: AsyncLRUCache[int] = AsyncLRUCache(maxsize=2)

    async def compute(value: int):
        async def inner() -> int:
            return value

        return inner

    await cache.get_or_compute("a", await compute(1))
    await cache.get_or_compute("b", await compute(2))
    await cache.get_or_compute("c", await compute(3))  # deve descartar "a"

    assert len(cache) == 2
    calls = 0

    async def recompute_a() -> int:
        nonlocal calls
        calls += 1
        return 1

    await cache.get_or_compute("a", recompute_a)
    assert calls == 1  # "a" não estava mais no cache: precisou recomputar


@pytest.mark.anyio
async def test_erro_no_compute_nao_fica_preso_no_cache():
    cache: AsyncLRUCache[int] = AsyncLRUCache()

    async def failing() -> int:
        raise RuntimeError("falha simulada")

    with pytest.raises(RuntimeError):
        await cache.get_or_compute("k", failing)

    async def succeeding() -> int:
        return 99

    assert await cache.get_or_compute("k", succeeding) == 99


@pytest.mark.anyio
async def test_clear_reseta_cache_e_estatisticas():
    cache: AsyncLRUCache[int] = AsyncLRUCache()

    async def compute() -> int:
        return 1

    await cache.get_or_compute("k", compute)
    cache.clear()

    assert len(cache) == 0
    assert cache.stats.hits == 0
    assert cache.stats.misses == 0
