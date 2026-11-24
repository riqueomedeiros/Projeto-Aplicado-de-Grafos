"""Testes da integração entre dados, algoritmos e respostas HTTP."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from hospitalflow.grafo import detectar_ciclo, explorar, rotas_de_evacuacao
from hospitalflow.web import criar_app


class TestHospitalFlow(TestCase):
    def setUp(self):
        self.app = criar_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def consultar(self, operacao, origem=None, destino=None, interditados=(), cenario="normal"):
        return self.client.post(f"/api/cenarios/{cenario}/consulta", json={
            "operacao": operacao,
            "origem": origem,
            "destino": destino,
            "interditados": list(interditados),
        })

    def test_base_real_e_estaticos(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        for caminho in ("/static/styles.css", "/static/app.js"):
            with self.client.get(caminho) as resposta:
                self.assertEqual(resposta.status_code, 200)
        resposta = self.consultar("bfs", "entrada-principal", "raio-x-leste", cenario="derriford")
        self.assertEqual(resposta.json["caminho"], ["entrada-principal", "loja", "raio-x-leste"])

    def test_bfs_e_dijkstra_otimizam_criterios_diferentes(self):
        bfs = self.consultar("bfs", "recepcao", "uti").json
        dijkstra = self.consultar("dijkstra", "recepcao", "uti").json
        self.assertEqual(bfs["caminho"], ["recepcao", "pronto-socorro", "uti"])
        self.assertEqual(dijkstra["caminho"], ["recepcao", "farmacia", "laboratorio", "uti"])
        self.assertEqual(dijkstra["tempo_min"], "3.5")
        self.assertEqual(dijkstra["trechos"][1]["tempo_min"], "1.5")

    def test_interdicao_e_impacto_sem_estado_no_servidor(self):
        bloqueados = ["lab-uti"]
        resultado = self.consultar("dijkstra", "recepcao", "uti", bloqueados).json
        self.assertEqual(resultado["caminho"], ["recepcao", "pronto-socorro", "centro-cirurgico", "uti"])
        self.assertEqual(resultado["tempo_adicional"], "2.5")
        self.assertEqual(self.consultar("dijkstra", "recepcao", "uti").json["tempo_min"], "3.5")

        resultado = self.consultar("bfs", "recepcao", "uti", ["ps-uti"]).json
        self.assertEqual(resultado["corredores_adicionais"], 1)
        indisponivel = self.consultar("bfs", "recepcao", "uti", ["recepcao-ps", "recepcao-farmacia"])
        self.assertIsNone(indisponivel.json["caminho"])
        self.assertEqual(indisponivel.json["original"], ["recepcao", "pronto-socorro", "uti"])

    def test_dfs_explora_e_encontra_circuito_e_rotas_de_evacuacao(self):
        ordem = self.consultar("explorar", "recepcao").json["ordem"]
        self.assertEqual(ordem[0], "recepcao")
        self.assertEqual(len(ordem), 7)
        ciclo = self.consultar("ciclo").json["ciclo"]
        self.assertEqual(ciclo[0], ciclo[-1])
        self.assertGreaterEqual(len(ciclo), 4)
        self.assertIsNone(self.consultar("ciclo", cenario="extremo").json["ciclo"])
        rotas = self.consultar("evacuar", "uti", "saida").json["rotas"]
        self.assertGreater(len(rotas), 1)
        self.assertEqual([len(rota) for rota in rotas], sorted(map(len, rotas)))
        for rota in rotas:
            self.assertEqual((rota[0], rota[-1]), ("uti", "saida"))
            self.assertEqual(len(rota), len(set(rota)))
        sem_passagem = self.consultar("evacuar", "uti", "saida", ["lab-saida", "farmacia-saida"])
        self.assertEqual(sem_passagem.json["rotas"], [])

    def test_desconexao_peso_zero_e_origem_igual_ao_destino(self):
        for operacao in ("bfs", "dijkstra"):
            sem_rota = self.consultar(operacao, "triagem", "saida", cenario="extremo")
            self.assertEqual(sem_rota.status_code, 200)
            self.assertIsNone(sem_rota.json["caminho"])
            mesma = self.consultar(operacao, "saida", "saida", cenario="extremo")
            self.assertEqual(mesma.json["caminho"], ["saida"])
            self.assertEqual(mesma.json["corredores"], 0)
            self.assertEqual(mesma.json["intermediarios"], 0)
        sem_tempo = self.consultar("dijkstra", "triagem", "observacao", cenario="extremo")
        self.assertEqual(sem_tempo.json["tempo_min"], "0")
        ja_na_saida = self.consultar("evacuar", "saida", "saida", cenario="extremo")
        self.assertEqual(ja_na_saida.json["rotas"], [["saida"]])

    def test_entradas_invalidas_sem_erro_interno(self):
        url = "/api/cenarios/normal/consulta"
        for resposta in (
            self.client.post(url, data="{", content_type="application/json"),
            self.client.post(url, json=["bfs"]),
            self.consultar(["bfs"], "recepcao", "uti"),
            self.consultar("bfs", [], "uti"),
            self.consultar("bfs", "", "uti"),
            self.consultar("dijkstra", "recepcao", "inexistente"),
            self.consultar("ciclo", interditados=[{}]),
            self.consultar("evacuar", "uti", "farmacia"),
            self.client.get("/api/cenarios/outro"),
        ):
            self.assertEqual(resposta.status_code, 400)
            self.assertIn("erro", resposta.json)

    def test_arquivo_ausente_malformado_grafo_vazio_e_pesos_invalidos(self):
        self.assertIn("negativo", self.client.get("/api/cenarios/invalido").json["erro"])
        with TemporaryDirectory() as temp:
            pasta = Path(temp)
            client = criar_app(pasta).test_client()
            url = "/api/cenarios/normal"
            arquivo = pasta / "normal.json"

            ausente = client.get(url)
            self.assertEqual(ausente.status_code, 422)
            self.assertIn("ausente", ausente.json["erro"])
            arquivo.write_text("{", encoding="utf-8")
            self.assertIn("malformado", client.get(url).json["erro"])
            arquivo.write_bytes(b"\xff")
            self.assertIn("UTF-8", client.get(url).json["erro"])

            base = {"nome": "Teste", "nota": "Teste", "setores": [], "corredores": []}
            arquivo.write_text(json.dumps(base), encoding="utf-8")
            self.assertIn("vazio", client.get(url).json["erro"])
            base["setores"] = [{"id": "a", "nome": "Triagem"}, {"id": "b", "nome": "Observação"}]
            for peso in (-1, "3", True, None, float("inf"), float("nan")):
                with self.subTest(peso=peso):
                    base["corredores"] = [{"id": "ab", "origem": "a", "destino": "b", "tempo_min": peso}]
                    arquivo.write_text(json.dumps(base), encoding="utf-8")
                    resposta = client.get(url)
                    self.assertEqual(resposta.status_code, 422)
                    self.assertIn("tempo_min", resposta.json["erro"])
            base["corredores"] = []
            arquivo.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(client.get(url).status_code, 200)

    def test_dfs_iterativa_em_grafo_profundo(self):
        # A cadeia ultrapassa o limite padrão de recursão do Python.
        quantidade = 1500
        grafo = {str(indice): {} for indice in range(quantidade)}
        for indice in range(1, quantidade):
            a, b = str(indice - 1), str(indice)
            grafo[a][b] = grafo[b][a] = 1
        self.assertEqual(len(explorar(grafo, "0")), quantidade)
        self.assertIsNone(detectar_ciclo(grafo))
        rotas, parcial = rotas_de_evacuacao(grafo, "0", str(quantidade - 1))
        self.assertFalse(parcial)
        self.assertEqual(len(rotas[0]), quantidade)

    def test_evacuacao_retorna_resultado_parcial_quando_atinge_limite(self):
        grafo = {
            "a": {"b": 1, "c": 1}, "b": {"a": 1, "c": 1}, "c": {"a": 1, "b": 1},
        }
        rotas, parcial = rotas_de_evacuacao(grafo, "a", "c", limite=1)
        self.assertTrue(parcial)
        self.assertEqual(rotas, [["a", "b", "c"]])
