"""Rotas Flask e apresentação dos resultados no vocabulário do hospital."""

from decimal import Decimal
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from .dados import ErroDados, carregar_hospital
from .grafo import bfs, detectar_ciclo, dijkstra, explorar, rotas_de_evacuacao

CENARIOS = {
    "derriford": ("Hospital Derriford · base real", "derriford.json"),
    "normal": ("Teste normal · hospital simulado", "normal.json"),
    "extremo": ("Teste extremo · setores isolados", "extremo.json"),
    "invalido": ("Teste inválido · tempo incorreto", "invalido.json"),
}
OPERACOES = ("bfs", "dijkstra", "explorar", "evacuar", "ciclo")


class ErroConsulta(ValueError):
    """Entrada de consulta inválida."""


def selecionar_setor(dados, campo, hospital, rotulo):
    setor = dados.get(campo)
    if not isinstance(setor, str) or not setor.strip():
        raise ErroConsulta(f"Selecione {rotulo}.")
    setor = setor.strip()
    if setor not in hospital.setores:
        raise ErroConsulta(f"O setor escolhido para {rotulo} não existe neste cenário.")
    return setor


def consultar_rota(operacao, grafo, grafo_original, hospital, origem, destino):
    busca = bfs if operacao == "bfs" else dijkstra
    caminho = busca(grafo, origem, destino)
    original = caminho if grafo is grafo_original else busca(grafo_original, origem, destino)
    resposta = {"caminho": caminho, "original": original}
    de = hospital.setores[origem].nome
    para = hospital.setores[destino].nome
    if caminho is None:
        resposta["mensagem"] = f"Não há rota disponível de {de} até {para}."
        return resposta

    if origem == destino:
        resposta["mensagem"] = f"Você já está em {de}."
    elif caminho != original:
        resposta["mensagem"] = "Rota recalculada após a interdição."
    elif operacao == "bfs":
        resposta["mensagem"] = "Rota com menos corredores."
    else:
        resposta["mensagem"] = "Rota com menor tempo estimado."

    resposta["corredores"] = len(caminho) - 1
    resposta["intermediarios"] = max(len(caminho) - 2, 0)
    if operacao == "bfs":
        resposta["corredores_adicionais"] = len(caminho) - len(original)
    else:
        trechos = [
            {"de": a, "para": b, "tempo_min": grafo[a][b]}
            for a, b in zip(caminho, caminho[1:])
        ]
        tempo = sum((trecho["tempo_min"] for trecho in trechos), Decimal(0))
        tempo_original = sum(
            (grafo_original[a][b] for a, b in zip(original, original[1:])), Decimal(0),
        )
        resposta.update(
            trechos=trechos, tempo_min=tempo,
            tempo_original=tempo_original, tempo_adicional=tempo - tempo_original,
        )
    return resposta


def executar_consulta(dados, hospital):
    operacao = dados.get("operacao")
    if operacao not in OPERACOES:
        raise ErroConsulta("Selecione um algoritmo e uma operação válidos.")

    interditados = dados.get("interditados", [])
    if not isinstance(interditados, list) or any(
        not isinstance(item, str) or item not in hospital.corredores
        for item in interditados
    ):
        raise ErroConsulta("A consulta contém um corredor interditado inválido.")
    grafo = hospital.adjacencia(set(interditados))

    if operacao == "ciclo":
        ciclo = detectar_ciclo(grafo)
        mensagem = "Circuito encontrado no hospital." if ciclo else "Nenhum circuito encontrado nos corredores livres."
        return {"ciclo": ciclo, "mensagem": mensagem}

    origem = selecionar_setor(dados, "origem", hospital, "a origem")
    if operacao == "explorar":
        ordem = explorar(grafo, origem)
        nome = hospital.setores[origem].nome
        return {"ordem": ordem, "mensagem": f"Setores alcançáveis a partir de {nome}."}

    destino = selecionar_setor(dados, "destino", hospital, "o destino")
    if operacao == "evacuar":
        if not hospital.setores[destino].saida:
            raise ErroConsulta("Escolha um ponto de saída cadastrado no cenário.")
        rotas, parcial = rotas_de_evacuacao(grafo, origem, destino)
        if origem == destino:
            mensagem = "Você já está no ponto de saída."
        elif parcial:
            mensagem = "A busca atingiu o limite de exploração. A lista de rotas pode estar incompleta."
        elif rotas:
            mensagem = "Rotas sem repetição de setores até o ponto de saída."
        else:
            mensagem = "Não há rota disponível até o ponto de saída selecionado."
        return {"rotas": rotas, "parcial": parcial, "mensagem": mensagem}

    grafo_original = hospital.adjacencia(set()) if interditados else grafo
    return consultar_rota(operacao, grafo, grafo_original, hospital, origem, destino)


def criar_app(pasta_dados: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    diretorio = pasta_dados if pasta_dados is not None else Path(__file__).resolve().parents[1] / "data"

    def obter_hospital(cenario):
        if cenario not in CENARIOS:
            raise ErroConsulta("O cenário selecionado não existe.")
        # Relê o arquivo a cada consulta para refletir alterações sem reiniciar.
        return carregar_hospital(diretorio / CENARIOS[cenario][1])

    @app.errorhandler(ErroConsulta)
    def erro_consulta(erro):
        return jsonify(erro=str(erro)), 400

    @app.errorhandler(ErroDados)
    def erro_dados(erro):
        return jsonify(erro=str(erro)), 422

    @app.errorhandler(RequestEntityTooLarge)
    def consulta_grande(_erro):
        return jsonify(erro="O tamanho da consulta excede o limite aceito."), 413

    @app.get("/")
    def inicio():
        return render_template("index.html", cenarios=CENARIOS)

    @app.get("/api/cenarios/<cenario>")
    def carregar_cenario(cenario):
        return jsonify(obter_hospital(cenario))

    @app.post("/api/cenarios/<cenario>/consulta")
    def consultar(cenario):
        try:
            dados = request.get_json(silent=True)
        except RecursionError as erro:
            raise ErroConsulta("A consulta contém uma estrutura JSON inválida.") from erro
        if not isinstance(dados, dict):
            raise ErroConsulta("Envie um objeto JSON válido para consultar o hospital.")
        return jsonify(executar_consulta(dados, obter_hospital(cenario)))

    return app
