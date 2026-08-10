"""Cache leve de respostas de IA.

O currículo base é imutável e a mesma vaga costuma gerar várias chamadas
praticamente idênticas ao validador de IA — por exemplo, `POST /api/versions`
cria 3 variantes (regra 9) e valida cada uma, então o `base_resume_text` e o
`job_analysis_text` são EXATAMENTE os mesmos nas 3 chamadas; só o
`adapted_resume_text` muda. Rodadas de auto-fix repetem a validação de novo
sobre o mesmo conteúdo quando nada mudou. Reanalisar sem editar nada também
repete o pedido anterior.

Este módulo evita reprocessar tudo isso: cache exato (por hash do pedido),
sem heurística de similaridade — só reaproveita quando o conteúdo é
byte-a-byte o mesmo. Em memória apenas (nunca grava em disco), com tamanho
limitado (LRU) para não crescer sem limite; é descartado ao reiniciar o
processo, coerente com a política do projeto de não persistir descrições de
vaga nem texto de currículo (ver README, seção Segurança).
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Generic, Hashable, TypeVar

T = TypeVar("T")

DEFAULT_MAXSIZE = 128


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    in_flight_joins: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return 0.0 if self.total == 0 else round(self.hits / self.total, 3)


class AsyncLRUCache(Generic[T]):
    """Cache assíncrono por chave exata, com deduplicação de chamadas
    concorrentes idênticas (duas requisições simultâneas com o mesmo pedido
    disparam só UMA chamada real à IA; a segunda espera o resultado da primeira)."""

    def __init__(self, maxsize: int = DEFAULT_MAXSIZE) -> None:
        self._maxsize = maxsize
        self._store: "OrderedDict[Hashable, T]" = OrderedDict()
        self._in_flight: dict[Hashable, "asyncio.Future[T]"] = {}
        self.stats = CacheStats()

    async def get_or_compute(self, key: Hashable, compute: Callable[[], Awaitable[T]]) -> T:
        cached = self._store.get(key)
        if cached is not None or key in self._store:
            self._store.move_to_end(key)
            self.stats.hits += 1
            return cached  # type: ignore[return-value]

        pending = self._in_flight.get(key)
        if pending is not None:
            self.stats.hits += 1
            self.stats.in_flight_joins += 1
            return await pending

        loop = asyncio.get_event_loop()
        future: "asyncio.Future[T]" = loop.create_future()
        self._in_flight[key] = future
        self.stats.misses += 1
        try:
            result = await compute()
        except BaseException as error:  # noqa: BLE001 - propaga para todos que esperavam
            future.set_exception(error)
            self._in_flight.pop(key, None)
            raise
        else:
            future.set_result(result)
            self._in_flight.pop(key, None)
            self._store[key] = result
            self._store.move_to_end(key)
            if len(self._store) > self._maxsize:
                self._store.popitem(last=False)
            return result

    def clear(self) -> None:
        self._store.clear()
        self._in_flight.clear()
        self.stats = CacheStats()

    def __len__(self) -> int:
        return len(self._store)
