"""Leitura e validação dos arquivos JSON que descrevem o hospital."""

import json
from decimal import Decimal
from pathlib import Path

from .grafo import Corredor, Hospital, Setor


class ErroDados(ValueError):
    """Problema no arquivo que pode ser apresentado na interface."""


def texto(objeto: dict, campo: str, local: str) -> str:
    valor = objeto.get(campo)
    if not isinstance(valor, str) or not valor.strip():
        raise ErroDados(f"{local}: preencha «{campo}» com um texto não vazio.")
    return valor.strip()


def registros(documento: dict, campo: str):
    itens = documento.get(campo)
    if not isinstance(itens, list):
        raise ErroDados(f"«{campo}» deve ser uma lista.")
    for indice, item in enumerate(itens, start=1):
        local = f"{campo}, item {indice}"
        if not isinstance(item, dict):
            raise ErroDados(f"{local}: esperado um objeto JSON.")
        yield item, local


def peso(valor, local: str) -> Decimal:
    if type(valor) not in (int, Decimal):
        raise ErroDados(f"{local}: «tempo_min» deve ser um número finito.")
    tempo = Decimal(valor)
    if not tempo.is_finite():
        raise ErroDados(f"{local}: «tempo_min» deve ser um número finito.")
    if tempo < 0:
        raise ErroDados(f"{local}: «tempo_min» não pode ser negativo.")
    if not tempo:
        return Decimal(0)
    # Restringe expoentes extremos que poderiam causar erros na soma dos trechos.
    if not -324 <= tempo.adjusted() <= 308:
        raise ErroDados(f"{local}: «tempo_min» está fora da faixa numérica aceita.")
    return tempo


def objeto_sem_chaves_repetidas(pares: list[tuple]) -> dict:
    objeto = dict(pares)
    if len(objeto) != len(pares):
        raise ErroDados("O JSON contém um objeto com campos repetidos.")
    return objeto


def carregar_hospital(arquivo: Path) -> Hospital:
    try:
        with arquivo.open(encoding="utf-8-sig") as entrada:
            documento = json.load(
                entrada, parse_float=Decimal, parse_constant=Decimal,
                object_pairs_hook=objeto_sem_chaves_repetidas,
            )
    except FileNotFoundError as erro:
        raise ErroDados(f"Arquivo de dados ausente: {arquivo.name}.") from erro
    except json.JSONDecodeError as erro:
        raise ErroDados(f"JSON malformado na linha {erro.lineno}, coluna {erro.colno}.") from erro
    except UnicodeError as erro:
        raise ErroDados("O arquivo de dados precisa estar em UTF-8.") from erro
    except ErroDados:
        raise
    except (ValueError, ArithmeticError, RecursionError) as erro:
        raise ErroDados("O JSON contém números ou estruturas fora dos limites aceitos.") from erro
    except OSError as erro:
        raise ErroDados(f"Não foi possível ler o arquivo {arquivo.name}.") from erro

    if not isinstance(documento, dict):
        raise ErroDados("O arquivo precisa conter um objeto JSON.")
    nome = texto(documento, "nome", "Cenário")
    nota = texto(documento, "nota", "Cenário")

    setores = {}
    for item, local in registros(documento, "setores"):
        identificador = texto(item, "id", local)
        rotulo = texto(item, "nome", local)
        saida = item.get("saida", False)
        if identificador in setores:
            raise ErroDados(f"{local}: ID de setor repetido «{identificador}».")
        if not isinstance(saida, bool):
            raise ErroDados(f"{local}: «saida» deve ser true ou false.")
        setores[identificador] = Setor(identificador, rotulo, saida)
    if not setores:
        raise ErroDados("O grafo hospitalar está vazio. Cadastre pelo menos um setor.")

    corredores = {}
    pares = set()
    for item, local in registros(documento, "corredores"):
        identificador = texto(item, "id", local)
        origem = texto(item, "origem", local)
        destino = texto(item, "destino", local)
        if origem not in setores or destino not in setores:
            raise ErroDados(f"{local}: o corredor referencia um setor inexistente.")
        if origem == destino:
            raise ErroDados(f"{local}: o corredor precisa ligar dois setores distintos.")
        par = frozenset((origem, destino))
        if identificador in corredores or par in pares:
            raise ErroDados(f"{local}: ID ou ligação de corredor repetida.")
        corredores[identificador] = Corredor(
            identificador, origem, destino, peso(item.get("tempo_min"), local),
        )
        pares.add(par)

    return Hospital(nome, nota, setores, corredores)
