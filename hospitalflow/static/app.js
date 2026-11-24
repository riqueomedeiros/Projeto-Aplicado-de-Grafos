"use strict";

const campo = id => document.getElementById(id);
const cenario = campo("cenario");
const algoritmo = campo("algoritmo");
const modo = campo("modo");
const origem = campo("origem");
const destino = campo("destino");
const corredor = campo("corredor");
const erro = campo("erro");
const painel = campo("painel");
const detalhes = campo("detalhes");
const mensagem = campo("mensagem");
const grafo = campo("grafo");
const interditados = new Set();

let hospital;
let carga;
let consulta;
let ultimaConsulta;
let resultado;
let rotaSelecionada = 0;

const operacao = () => algoritmo.value === "dfs" ? modo.value : algoritmo.value;
const urlCenario = () => cenario.dataset.apiBase.replace("__cenario__", cenario.value);
const nome = id => hospital.setores[id].nome;
const nomeCorredor = item => `${nome(item.origem)} ↔ ${nome(item.destino)}`;
const mostrarTempo = numero => String(numero).replace(".", ",") + " min";
const caminhoTexto = caminho => caminho.map(nome).join(" → ");

async function solicitar(url, signal, dados) {
  const opcoes = dados === undefined ? { signal } : {
    signal,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  };
  let resposta;
  try {
    resposta = await fetch(url, opcoes);
  } catch (falha) {
    if (falha.name === "AbortError") throw falha;
    throw new Error("Não foi possível conectar ao servidor do HospitalFlow.");
  }
  if (!resposta.headers.get("content-type")?.includes("application/json")) {
    throw new Error("O servidor retornou uma resposta inesperada.");
  }
  const json = await resposta.json();
  if (!resposta.ok) throw new Error(json.erro || "Não foi possível concluir a consulta.");
  return json;
}

function mostrarErro(texto = "") {
  erro.textContent = texto;
  erro.hidden = !texto;
}

function abrirElemento(tag, texto, onde = detalhes) {
  const elemento = document.createElement(tag);
  elemento.textContent = texto;
  onde.append(elemento);
  return elemento;
}

function atualizarDestinos(valor = destino.value) {
  const evacuacao = operacao() === "evacuar";
  const setores = Object.values(hospital.setores).filter(setor => !evacuacao || setor.saida);
  destino.replaceChildren(new Option(
    evacuacao && !setores.length ? "Nenhum ponto de saída cadastrado" : "Selecione o destino", "",
  ));
  for (const setor of setores) destino.add(new Option(setor.nome, setor.id));
  if (setores.some(setor => setor.id === valor)) destino.value = valor;
  destino.disabled = setores.length === 0;
  campo("rotulo-destino").textContent = evacuacao ? "Ponto de saída" : "Destino";
}

function atualizarCampos() {
  campo("campo-modo").hidden = algoritmo.value !== "dfs";
  campo("campo-origem").hidden = operacao() === "ciclo";
  campo("campo-destino").hidden = ["explorar", "ciclo"].includes(operacao());
  campo("consultar").textContent = algoritmo.value === "dfs" ? "Executar DFS" : "Calcular rota";
  atualizarDestinos();
}

function atualizarCorredores() {
  const escolhido = corredor.value;
  const corredores = Object.values(hospital.corredores);
  const lista = campo("bloqueios");
  corredor.replaceChildren(new Option(corredores.length ? "Selecione um corredor" : "Nenhum corredor cadastrado", ""));
  lista.replaceChildren();
  for (const item of corredores) {
    const fechado = interditados.has(item.id);
    const rotulo = nomeCorredor(item);
    corredor.add(new Option(rotulo + (fechado ? " (interditado)" : ""), item.id));
    if (fechado) abrirElemento("li", rotulo, lista);
  }
  corredor.value = corredores.some(item => item.id === escolhido) ? escolhido : "";
  corredor.disabled = corredores.length === 0;
  campo("liberar").disabled = interditados.size === 0;
  atualizarAcaoCorredor();
}

function atualizarAcaoCorredor() {
  const botao = campo("interditar");
  const fechado = interditados.has(corredor.value);
  botao.disabled = !corredor.value;
  botao.classList.toggle("danger", !fechado);
  botao.textContent = fechado ? "Liberar corredor" : "Interditar";
}

function limparResultado() {
  resultado = null;
  rotaSelecionada = 0;
  mensagem.textContent = "";
  detalhes.replaceChildren();
}

async function carregar() {
  carga?.abort();
  consulta?.abort();
  const requisicao = new AbortController();
  carga = requisicao;
  hospital = null;
  ultimaConsulta = null;
  interditados.clear();
  painel.hidden = true;
  limparResultado();
  mostrarErro();
  campo("cenario-nota").textContent = "Carregando cenário…";

  try {
    const dados = await solicitar(urlCenario(), requisicao.signal);
    if (carga !== requisicao) return;
    hospital = dados;
    campo("cenario-nota").textContent = hospital.nota;
    campo("mapa-nota").textContent = hospital.nome;
    origem.replaceChildren(new Option("Selecione a origem", ""));
    for (const setor of Object.values(hospital.setores)) origem.add(new Option(setor.nome, setor.id));
    atualizarCampos();
    destino.value = "";
    corredor.value = "";
    atualizarCorredores();
    desenharGrafo();
    painel.hidden = false;
  } catch (falha) {
    if (falha.name === "AbortError" || carga !== requisicao) return;
    campo("cenario-nota").textContent = "Escolha outro cenário para continuar.";
    mostrarErro(falha.message);
  }
}

async function executar() {
  if (!hospital) return;
  consulta?.abort();
  const requisicao = new AbortController();
  consulta = requisicao;
  limparResultado();
  mostrarErro();
  desenharGrafo();

  const dados = { operacao: operacao(), origem: origem.value, destino: destino.value };
  ultimaConsulta = null;
  if (dados.operacao !== "ciclo" && !dados.origem) {
    mostrarErro("Selecione o setor de origem.");
    origem.focus();
    return;
  }
  if (!campo("campo-destino").hidden && !dados.destino) {
    mostrarErro(dados.operacao === "evacuar" && destino.disabled ?
      "O cenário não tem um ponto de saída cadastrado." : "Selecione o setor de destino.");
    destino.focus();
    return;
  }

  ultimaConsulta = dados;
  mensagem.textContent = "Consultando os corredores livres…";
  try {
    const resposta = await solicitar(urlCenario() + "/consulta", requisicao.signal, {
      ...dados, interditados: [...interditados],
    });
    if (consulta !== requisicao) return;
    resultado = resposta;
    mostrarResultado(dados.operacao);
    desenharGrafo();
  } catch (falha) {
    if (falha.name === "AbortError" || consulta !== requisicao) return;
    mensagem.textContent = "";
    mostrarErro(falha.message);
  }
}

function mostrarResultado(tipo) {
  mensagem.textContent = resultado.mensagem;
  if (tipo === "explorar") {
    abrirElemento("p", `${resultado.ordem.length} de ${Object.keys(hospital.setores).length} setores visitados.`);
    const lista = abrirElemento("ol", "");
    for (const setor of resultado.ordem) abrirElemento("li", nome(setor), lista);
    return;
  }
  if (tipo === "ciclo") {
    if (resultado.ciclo) abrirElemento("p", caminhoTexto(resultado.ciclo));
    return;
  }
  if (tipo === "evacuar") {
    if (resultado.rotas.length) abrirElemento("p", `Rotas encontradas: ${resultado.rotas.length}.`);
    const lista = abrirElemento("ol", "");
    resultado.rotas.forEach((rota, indice) => {
      const rotulo = `${rota.length - 1} corredor(es) · ${caminhoTexto(rota)}`;
      const botao = abrirElemento("button", rotulo, abrirElemento("li", "", lista));
      botao.setAttribute("aria-pressed", String(indice === rotaSelecionada));
      botao.addEventListener("click", () => {
        rotaSelecionada = indice;
        for (const item of lista.querySelectorAll("button")) {
          item.setAttribute("aria-pressed", String(item === botao));
        }
        desenharGrafo();
      });
    });
    return;
  }

  if (!resultado.caminho) {
    if (resultado.original) abrirElemento("p", "Sem interdições: " + caminhoTexto(resultado.original));
    return;
  }
  abrirElemento("p", caminhoTexto(resultado.caminho));
  abrirElemento("p", `Corredores percorridos: ${resultado.corredores}. Setores intermediários: ${resultado.intermediarios}.`);
  if (tipo === "dijkstra") {
    abrirElemento("p", "Tempo estimado total: " + mostrarTempo(resultado.tempo_min));
  }
  if (interditados.size) {
    abrirElemento("p", "Sem interdições: " + caminhoTexto(resultado.original));
    if (tipo === "dijkstra") {
      abrirElemento("p", "Tempo original: " + mostrarTempo(resultado.tempo_original) +
        ". Tempo adicional: " + mostrarTempo(resultado.tempo_adicional) + ".");
    } else {
      abrirElemento("p", "Corredores adicionais: " + resultado.corredores_adicionais + ".");
    }
  }
  if (resultado.corredores) {
    const lista = abrirElemento("ol", "");
    for (const [indice, setor] of resultado.caminho.slice(1).entries()) {
      const anterior = resultado.caminho[indice];
      const tempo = resultado.trechos ? " · " + mostrarTempo(resultado.trechos[indice].tempo_min) : "";
      abrirElemento("li", nome(anterior) + " → " + nome(setor) + tempo, lista);
    }
  }
}

function elementoSvg(tag, atributos, pai, texto) {
  const elemento = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [chave, valor] of Object.entries(atributos)) elemento.setAttribute(chave, valor);
  if (texto !== undefined) elemento.textContent = texto;
  pai.append(elemento);
  return elemento;
}

function desenharGrafo() {
  const setores = Object.values(hospital.setores);
  const posicoes = new Map();
  const passos = resultado?.caminho || resultado?.ciclo || resultado?.rotas?.[rotaSelecionada] || [];
  const visitados = new Set(resultado?.ordem || passos);
  const arestasAtivas = new Map();
  passos.slice(1).forEach((setor, indice) => {
    const anterior = passos[indice];
    if (!arestasAtivas.has(anterior)) arestasAtivas.set(anterior, new Set());
    arestasAtivas.get(anterior).add(setor);
  });

  grafo.replaceChildren();
  const quantidade = setores.length;
  const largura = Math.max(720, quantidade * 60);
  const altura = Math.max(410, quantidade * 32);
  grafo.setAttribute("viewBox", `0 0 ${largura} ${altura}`);
  grafo.style.minWidth = quantidade > 12 ? largura + "px" : "";
  setores.forEach((setor, indice) => {
    const angulo = -Math.PI / 2 + indice * 2 * Math.PI / quantidade;
    const x = largura / 2 + (quantidade > 1 ? Math.cos(angulo) * (largura / 2 - 155) : 0);
    const y = altura / 2 + (quantidade > 1 ? Math.sin(angulo) * (altura / 2 - 60) : 0);
    posicoes.set(setor.id, { x, y });
  });

  for (const item of Object.values(hospital.corredores)) {
    const a = posicoes.get(item.origem);
    const b = posicoes.get(item.destino);
    const fechado = interditados.has(item.id);
    const ativo = arestasAtivas.get(item.origem)?.has(item.destino) || arestasAtivas.get(item.destino)?.has(item.origem);
    const rotulo = nomeCorredor(item) + (fechado ? ", interditado" : ", livre");
    const grupo = elementoSvg("g", {
      class: "edge" + (fechado ? " blocked" : "") + (ativo ? " on-path" : ""),
      tabindex: "0", role: "button", "aria-label": "Selecionar " + rotulo,
    }, grafo);
    const extremos = { x1: a.x, y1: a.y, x2: b.x, y2: b.y };
    elementoSvg("line", { ...extremos, class: "line" }, grupo);
    elementoSvg("line", { ...extremos, class: "hit" }, grupo);
    elementoSvg("title", {}, grupo, rotulo);
    if (algoritmo.value === "dijkstra") {
      elementoSvg("text", {
        x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 - 7, "text-anchor": "middle",
      }, grupo, mostrarTempo(item.tempo_min));
    }
    const selecionar = () => {
      corredor.value = item.id;
      atualizarAcaoCorredor();
      corredor.focus();
    };
    grupo.addEventListener("click", selecionar);
    grupo.addEventListener("keydown", evento => {
      if (!["Enter", " "].includes(evento.key)) return;
      evento.preventDefault();
      selecionar();
    });
  }

  setores.forEach((setor, indice) => {
    const { x, y } = posicoes.get(setor.id);
    const grupo = elementoSvg("g", { class: visitados.has(setor.id) ? "node on-path" : "node" }, grafo);
    elementoSvg("circle", { cx: x, cy: y, r: 15 }, grupo);
    elementoSvg("text", { x, y: y + 5, "text-anchor": "middle", class: "number" }, grupo, indice + 1);
    elementoSvg("text", { x, y: y + 34, "text-anchor": "middle" }, grupo, setor.nome);
  });
}

function refletirInterdicao() {
  atualizarCorredores();
  if (ultimaConsulta) {
    executar();
  } else {
    mostrarErro();
    desenharGrafo();
  }
}

function trocarOperacao() {
  if (!hospital) return;
  consulta?.abort();
  ultimaConsulta = null;
  limparResultado();
  mostrarErro();
  atualizarCampos();
  desenharGrafo();
}

cenario.addEventListener("change", carregar);
algoritmo.addEventListener("change", trocarOperacao);
modo.addEventListener("change", trocarOperacao);
origem.addEventListener("change", trocarOperacao);
destino.addEventListener("change", trocarOperacao);
corredor.addEventListener("change", atualizarAcaoCorredor);
campo("consulta").addEventListener("submit", evento => {
  evento.preventDefault();
  executar();
});
campo("interditar").addEventListener("click", () => {
  if (!hospital?.corredores[corredor.value]) return;
  if (interditados.has(corredor.value)) interditados.delete(corredor.value);
  else interditados.add(corredor.value);
  refletirInterdicao();
});
campo("liberar").addEventListener("click", () => {
  interditados.clear();
  refletirInterdicao();
});

carregar();
