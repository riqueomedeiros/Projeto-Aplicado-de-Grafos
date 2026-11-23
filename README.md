# HospitalFlow — Rotas e interdições hospitalares

Projeto da disciplina de Grafo.s O HospitalFlow modela setores, acessos e pontos de passagem como vértices. As ligações de circulação são arestas bidirecionais com um tempo de deslocamento em minutos. A interface permite comparar critérios de rota e simular o impacto de interdições.

| Algoritmo | Consulta |
| --- | --- |
| BFS (busca em largura) | Encontra o trajeto que passa pelo menor número de corredores. |
| DFS (busca em profundidade) | Explora setores alcançáveis, lista caminhos simples até uma saída e identifica um circuito nos corredores livres. |
| Dijkstra | Encontra o trajeto de menor tempo estimado e informa a duração de cada trecho. |

## Equipe

| Nome | RA |
| --- | --- |
| Henrique de Oliveira Medeiros | 1681432612019 |
| Ana Beatriz | 1681432612001 |
| Gabriel Lasinskais | 1681432612010 |

## Pré-requisitos

- Python 3.10 ou superior. A versão utilizada na validação foi Python 3.12.
- Git para clonar o repositório e um navegador com JavaScript habilitado.
- Acesso à internet na instalação das dependências. A aplicação carrega os dados localmente.

## Instalação em cópia limpa

Quando o repositório remoto estiver disponível, substitua `URL_DO_REPOSITORIO` pela URL de clonagem. Para usar o ZIP, extraia-o e abra um terminal na pasta `hospitalflow` que contém `app.py`.

```bash
git clone "URL_DO_REPOSITORIO" hospitalflow
cd hospitalflow
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

### Linux e macOS

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python app.py
```

Abra [http://127.0.0.1:5000](http://127.0.0.1:5000) e mantenha o terminal aberto. Use `Ctrl+C` para encerrar. Se a porta 5000 estiver ocupada, inicie com `./.venv/bin/python -m flask --app app run --port 5001` ou, no PowerShell, `.\.venv\Scripts\python.exe -m flask --app app run --port 5001`. Nesse caso, abra [http://127.0.0.1:5001](http://127.0.0.1:5001).

## Exemplos de uso

1. **Base real.** Com **Hospital Derriford · base real** e **BFS** selecionados, escolha **Entrada principal · nível 6** como origem e **Raio-X Leste** como destino. Clique em **Calcular rota**. A aplicação mostra **Entrada principal · nível 6 → Loja League of Friends → Raio-X Leste**, com dois corredores. Em **Dijkstra**, a mesma consulta mostra 1,5 min estimado.
2. **Interdição com desvio.** Em **Teste normal**, calcule **Recepção → UTI** com Dijkstra. A rota inicial passa por Farmácia e Laboratório (3,5 min). Selecione **Laboratório ↔ UTI** na lista ou no grafo e clique em **Interditar**. A rota passa pelo Pronto-Socorro e pelo Centro Cirúrgico (6 min) e exibe 2,5 min adicionais. **Liberar todos** restaura os corredores e recalcula a consulta.
3. **Setor inacessível e origem igual ao destino.** Em **Teste extremo**, consulte de **Triagem** até **Saída de Emergência**. A interface informa que não há rota disponível. Selecione **Triagem** nos dois campos para obter um percurso de zero corredores e, em Dijkstra, 0 min.
4. **Arquivo inválido.** Selecione **Teste inválido**. A aplicação informa que `tempo_min` não pode ser negativo. Volte a qualquer cenário válido para continuar.
5. **DFS.** Em **Teste normal**, selecione **DFS**. Use **Explorar alas** a partir da Recepção, **Rotas de evacuação** da UTI até a Saída de Emergência ou **Detectar ciclo** no grafo livre. Clique em uma rota de evacuação para destacá-la no mapa.

As interdições ficam na aba atual e valem para os três algoritmos. Trocar de cenário ou recarregar a página inicia uma nova simulação. O desenho é topológico e a posição dos setores serve apenas para leitura do grafo.

## Dados e fonte

| Arquivo | Origem e finalidade |
| --- | --- |
| `data/derriford.json` | Base padrão. Recorte de locais e trajetos divulgados pelo University Hospitals Plymouth NHS Trust para o Hospital Derriford. |
| `data/normal.json` | Cenário didático derivado do projeto original, com ciclos e desvio após uma interdição. |
| `data/extremo.json` | Cenário didático com uma saída isolada e um corredor de peso zero. |
| `data/invalido.json` | Cenário didático com peso negativo para exercitar a mensagem de validação. |

A base real foi transcrita de [How to find Imaging — University Hospitals Plymouth NHS Trust](https://www.plymouthhospitals.nhs.uk/imaging-find-us/). As instruções ligam a entrada principal ao fim do corredor principal e ao Centro Mansfield. Também documentam o acesso ao Centro Mansfield a partir da entrada da maternidade e a passagem pela loja League of Friends para chegar aos dois setores de raio-X. O arquivo agrupa instruções consecutivas em ligações, incluindo o acesso por escada ou elevador como uma ligação. As duas entradas públicas funcionam como pontos de saída para a simulação acadêmica.

A fonte publica cerca de 30 m entre a bifurcação da loja e o Raio-X Leste. A estimativa de 0,5 min para esse trecho assume 60 m/min. Os demais tempos são valores de simulação. A aplicação foi feita para uso acadêmico e as instruções do hospital orientam a circulação real.

O formato é JSON em UTF-8. Cada arquivo traz `nome`, `nota`, uma lista `setores` e uma lista `corredores`. Um setor tem `id`, `nome` e `saida` opcional (por padrão, `false`). Cada corredor tem `id`, `origem`, `destino` e `tempo_min`. Os IDs devem ser únicos e os pesos devem ser números JSON finitos e não negativos. Setores isolados são válidos. Um cenário precisa ter pelo menos um setor. As alterações no JSON são lidas nas próximas consultas. Para atualizar o mapa da página após editar um arquivo, recarregue o navegador.

## Estrutura de pastas

```text
hospitalflow/
├── .gitignore
├── app.py
├── README.md
├── requirements.txt
├── data/
│   ├── derriford.json
│   ├── extremo.json
│   ├── invalido.json
│   └── normal.json
├── hospitalflow/
│   ├── __init__.py
│   ├── dados.py
│   ├── grafo.py
│   ├── web.py
│   ├── static/
│   │   ├── app.js
│   │   └── styles.css
│   └── templates/
│       └── index.html
└── tests/
    └── test_hospitalflow.py
```

`dados.py` lê e valida os arquivos. `grafo.py` constrói as listas de adjacência e implementa BFS com fila, DFS com pilha e Dijkstra com fila de prioridade. `web.py` recebe as consultas e apresenta os resultados no vocabulário hospitalar. As estruturas de fila e fila de prioridade vêm da biblioteca padrão do Python. A lógica de busca está implementada no projeto.

A busca por todos os caminhos simples pode ter custo exponencial. O modo de evacuação retorna até 100 rotas e examina até 50.000 passos de exploração. Quando atinge um limite, informa que a lista pode estar incompleta. As rotas encontradas são ordenadas pelo número de corredores.

## Testes automatizados

Rode a partir da raiz do projeto, no Linux ou macOS.

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

No Windows, execute no PowerShell.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes cobrem os algoritmos, o recálculo com interdições, os grafos desconexos, o peso zero, a origem igual ao destino, as entradas inválidas e os erros de leitura de dados. A interface apresenta erros de consulta com HTTP 400 e erros nos arquivos com HTTP 422. Uma consulta válida sem rota retorna HTTP 200 com o aviso correspondente.
