"""Modelo do hospital e operações de busca em grafos não dirigidos."""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from heapq import heappop, heappush

Adjacencia = dict[str, dict[str, Decimal]]


@dataclass(frozen=True)
class Setor:
    id: str
    nome: str
    saida: bool


@dataclass(frozen=True)
class Corredor:
    id: str
    origem: str
    destino: str
    tempo_min: Decimal


@dataclass(frozen=True)
class Hospital:
    nome: str
    nota: str
    setores: dict[str, Setor]
    corredores: dict[str, Corredor]

    def adjacencia(self, interditados: set[str]) -> Adjacencia:
        # Setores isolados continuam selecionáveis. Cada corredor liga os dois sentidos.
        grafo: Adjacencia = {setor: {} for setor in self.setores}
        for corredor in self.corredores.values():
            if corredor.id in interditados:
                continue
            a, b = corredor.origem, corredor.destino
            grafo[a][b] = corredor.tempo_min
            grafo[b][a] = corredor.tempo_min
        return grafo


def reconstruir_caminho(pais: dict[str, str | None], destino: str) -> list[str]:
    caminho = []
    atual: str | None = destino
    while atual is not None:
        caminho.append(atual)
        atual = pais[atual]
    return caminho[::-1]


def bfs(grafo: Adjacencia, origem: str, destino: str) -> list[str] | None:
    """O primeiro encontro com um setor usa o menor número de corredores."""
    fila = deque([origem])
    pais: dict[str, str | None] = {origem: None}
    while fila:
        atual = fila.popleft()
        if atual == destino:
            return reconstruir_caminho(pais, destino)
        for vizinho in grafo[atual]:
            if vizinho not in pais:
                pais[vizinho] = atual
                fila.append(vizinho)
    return None


def dijkstra(grafo: Adjacencia, origem: str, destino: str) -> list[str] | None:
    """Atualiza o melhor tempo de cada setor com pesos já validados."""
    tempos = {origem: Decimal(0)}
    pais: dict[str, str | None] = {origem: None}
    fila = [(Decimal(0), origem)]
    while fila:
        tempo, atual = heappop(fila)
        if tempo != tempos[atual]:
            continue  # A fila pode conter uma estimativa substituída por outra menor.
        if atual == destino:
            return reconstruir_caminho(pais, destino)
        for vizinho, peso in grafo[atual].items():
            novo_tempo = tempo + peso
            if vizinho not in tempos or novo_tempo < tempos[vizinho]:
                tempos[vizinho] = novo_tempo
                pais[vizinho] = atual
                heappush(fila, (novo_tempo, vizinho))
    return None


def explorar(grafo: Adjacencia, origem: str) -> list[str]:
    """Visita os setores alcançáveis em profundidade."""
    ordem = [origem]
    visitados = {origem}
    pilha = [iter(grafo[origem])]
    while pilha:
        vizinho = next(pilha[-1], None)
        if vizinho is None:
            pilha.pop()
        elif vizinho not in visitados:
            visitados.add(vizinho)
            ordem.append(vizinho)
            pilha.append(iter(grafo[vizinho]))
    return ordem


def rotas_de_evacuacao(
    grafo: Adjacencia, origem: str, saida: str, limite: int = 100,
    limite_passos: int = 50_000,
) -> tuple[list[list[str]], bool]:
    """Enumera caminhos simples em DFS com limite de resultados e de exploração."""
    if saida not in explorar(grafo, origem):
        return [], False

    caminho = [origem]
    presentes = {origem}
    pilha = [iter(grafo[origem])]
    rotas = []
    passos = 0
    while pilha:
        atual = caminho[-1]
        if atual == saida:
            if len(rotas) == limite:
                return sorted(rotas, key=len), True
            rotas.append(caminho.copy())
            vizinho = None
        else:
            if passos == limite_passos:
                return sorted(rotas, key=len), True
            vizinho = next(pilha[-1], None)
            passos += 1

        if vizinho is None:
            presentes.remove(caminho.pop())
            pilha.pop()
        elif vizinho not in presentes:
            presentes.add(vizinho)
            caminho.append(vizinho)
            pilha.append(iter(grafo[vizinho]))
    return sorted(rotas, key=len), False


def detectar_ciclo(grafo: Adjacencia) -> list[str] | None:
    """Procura uma aresta de retorno em todas as componentes do hospital."""
    visitados: set[str] = set()
    for origem in grafo:
        if origem in visitados:
            continue

        visitados.add(origem)
        caminho = [origem]
        no_caminho = {origem: 0}
        pilha: list[Iterator[str]] = [iter(grafo[origem])]
        while pilha:
            vizinho = next(pilha[-1], None)
            if vizinho is None:
                pilha.pop()
                del no_caminho[caminho.pop()]
            elif len(caminho) > 1 and vizinho == caminho[-2]:
                continue  # Em grafo não dirigido, voltar ao pai não forma um ciclo.
            elif vizinho in no_caminho:
                return caminho[no_caminho[vizinho]:] + [vizinho]
            elif vizinho not in visitados:
                visitados.add(vizinho)
                no_caminho[vizinho] = len(caminho)
                caminho.append(vizinho)
                pilha.append(iter(grafo[vizinho]))
    return None
