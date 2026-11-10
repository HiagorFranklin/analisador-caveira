// Analisador Caveira - Copyright (c) 2026 Hiagor Franklin. Todos os direitos reservados.
// Código proprietário: proibido copiar, modificar ou distribuir sem autorização. Veja LICENSE.

// Analisador Caveira — interface.
// Segurança: todo texto vindo da análise entra com textContent (nunca innerHTML),
// assim um link malicioso não consegue rodar código na página.

const $ = (id) => document.getElementById(id);
const CLASSE = { baixo: "baixo", "médio": "medio", alto: "alto" };
const VEREDITO = { baixo: "Parece tranquilo", "médio": "Suspeito", alto: "Perigo! Golpe provável" };
const CAVEIRAS = { baixo: 1, "médio": 2, alto: 3 };
const LIMITE_EML = 2 * 1024 * 1024;

function criar(tag, texto, classe) {
  const el = document.createElement(tag);
  if (texto != null) el.textContent = texto;
  if (classe) el.className = classe;
  return el;
}

function caveira() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "#caveira");
  svg.setAttribute("aria-hidden", "true");
  svg.appendChild(use);
  return svg;
}

function selo(nivel, texto) {
  const s = criar("span", null, "selo " + (CLASSE[nivel] || ""));
  if (nivel !== "baixo") s.appendChild(caveira());
  s.appendChild(document.createTextNode(texto));
  return s;
}

// "Desarma" o link: http -> hxxp e . -> [.]
function desarmar(url) {
  return String(url).replace(/^http/i, "hxxp").replace(/\./g, "[.]");
}

// Desarma só os links que aparecem no meio de um texto.
function desarmarTexto(texto) {
  return String(texto).replace(/(?:https?:\/\/|www\.)[^\s<>"']+/gi, desarmar);
}

// Para o histórico e o topo do resultado: link inteiro ou texto com links.
const exibir = (tipo, alvo) => (tipo === "url" ? desarmar(alvo) : desarmarTexto(alvo));

/* ---------------- Abas ---------------- */
const abas = document.querySelectorAll(".aba");
function trocarAba(nome) {
  abas.forEach((a) => {
    const ativa = a.dataset.aba === nome;
    a.classList.toggle("ativa", ativa);
    a.setAttribute("aria-selected", ativa);
  });
  document.querySelectorAll(".painel").forEach((p) => (p.hidden = p.dataset.painel !== nome));
  $("aviso").textContent = "";
}
abas.forEach((a) => a.addEventListener("click", () => trocarAba(a.dataset.aba)));

/* ---------------- Chamadas à API ---------------- */
async function chamar(rota, opcoes) {
  const resposta = await fetch(rota, opcoes);
  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => ({}));
    throw new Error(typeof erro.detail === "string" ? erro.detail : "Não foi possível analisar. Confira o que você enviou.");
  }
  return resposta.json();
}

const enviarJson = (rota, corpo) =>
  chamar(rota, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });

async function rodar(formulario, tarefa) {
  const botao = formulario.querySelector("button[type=submit]");
  const aviso = $("aviso");
  aviso.textContent = "Invocando a caveira… pode levar alguns segundos.";
  botao.disabled = true;
  try {
    const r = await tarefa();
    aviso.textContent = "";
    mostrar(r);
    carregarHistorico();
  } catch (e) {
    aviso.textContent = "☠ " + e.message;
  } finally {
    botao.disabled = false;
  }
}

$("form-url").addEventListener("submit", (ev) => {
  ev.preventDefault();
  rodar(ev.target, () => enviarJson("/api/url", { url: $("campo-url").value.trim(), usar_internet: $("net-url").checked }));
});

$("form-texto").addEventListener("submit", (ev) => {
  ev.preventDefault();
  rodar(ev.target, () => enviarJson("/api/texto", { texto: $("campo-texto").value, usar_internet: $("net-texto").checked }));
});

$("campo-arquivo").addEventListener("change", () => {
  const arq = $("campo-arquivo").files[0];
  $("nome-arquivo").textContent = arq ? arq.name : "Toque para escolher ou arraste o arquivo aqui";
  $("area-soltar").classList.toggle("cheio", !!arq);
});

$("form-email").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const arq = $("campo-arquivo").files[0];
  if (!arq) return ($("aviso").textContent = "☠ Escolha um arquivo .eml primeiro.");
  if (!arq.name.toLowerCase().endsWith(".eml")) return ($("aviso").textContent = "☠ O arquivo precisa terminar em .eml.");
  if (arq.size > LIMITE_EML) return ($("aviso").textContent = "☠ O arquivo passa de 2 MB.");
  const dados = new FormData();
  dados.append("arquivo", arq);
  dados.append("usar_internet", $("net-email").checked ? "true" : "false");
  rodar(ev.target, () => chamar("/api/email", { method: "POST", body: dados }));
});

/* ---------------- Mostrar resultado ---------------- */
function mostrar(r) {
  const caixa = $("resultado");
  caixa.className = "cartao resultado " + (CLASSE[r.nivel] || "");
  caixa.style.setProperty("--pct", r.nota);
  caixa.hidden = false;

  $("veredito").textContent = VEREDITO[r.nivel] || r.nivel;
  $("nota").textContent = r.nota;
  $("alvo").textContent = (r.tipo === "email" ? "E-mail: " : r.tipo === "texto" ? "Mensagem: " : "") + exibir(r.tipo, r.alvo);
  $("fileira").querySelectorAll("svg").forEach((s, i) => s.classList.toggle("acesa", i < (CAVEIRAS[r.nivel] || 0)));

  const lista = $("sinais");
  lista.replaceChildren();
  if (!r.sinais.length) {
    const li = criar("li", null, "limpo");
    li.appendChild(caveira());
    li.appendChild(criar("span", r.tipo === "url" ? "Nenhum sinal suspeito no endereço." : "Nenhum sinal suspeito no texto/cabeçalho."));
    lista.appendChild(li);
  }
  for (const s of r.sinais) {
    const li = criar("li", null, s.pontos >= 25 ? "forte" : "leve");
    li.appendChild(caveira());
    li.appendChild(criar("span", s.motivo));
    li.appendChild(criar("span", "+" + s.pontos, "pontos"));
    lista.appendChild(li);
  }

  const redir = r.redirecionamentos || [];
  $("bloco-redir").hidden = redir.length < 2;
  $("redir").replaceChildren(...redir.map((u) => criar("li", desarmar(u))));

  const temLinks = Array.isArray(r.links);
  $("bloco-links").hidden = !temLinks;
  const links = $("links");
  links.replaceChildren();
  if (temLinks) {
    if (!r.links.length) links.appendChild(criar("li", "Nenhum link encontrado."));
    for (const l of r.links) {
      const li = document.createElement("li");
      li.appendChild(criar("span", desarmar(l.alvo), "url"));
      li.appendChild(selo(l.nivel, l.nivel + " · " + l.nota));
      if (l.sinais.length) {
        const det = document.createElement("details");
        det.appendChild(criar("summary", l.sinais.length + " sinal(is)"));
        const ul = document.createElement("ul");
        l.sinais.forEach((s) => ul.appendChild(criar("li", s.motivo + " (+" + s.pontos + ")")));
        det.appendChild(ul);
        li.appendChild(det);
      }
      links.appendChild(li);
    }
    if (r.links_ignorados > 0) links.appendChild(criar("li", "+ " + r.links_ignorados + " link(s) não analisado(s) (limite de 20)."));
  }

  caixa.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------------- Histórico ---------------- */
const ROTULO = { url: "Link", email: "E-mail", texto: "Mensagem" };

async function carregarHistorico() {
  let itens;
  try {
    itens = await chamar("/api/historico?limite=15");
  } catch {
    return;
  }
  const lista = $("historico");
  lista.replaceChildren();
  if (!itens.length) return lista.appendChild(criar("li", "Nenhuma análise ainda.", "vazio"));
  for (const it of itens) {
    const li = document.createElement("li");
    const quando = new Date(it.quando).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
    li.appendChild(criar("span", (ROTULO[it.tipo] || it.tipo) + " · " + quando, "quando"));
    li.appendChild(selo(it.nivel, String(it.nota)));
    li.appendChild(criar("span", exibir(it.tipo, it.alvo), "oque"));
    lista.appendChild(li);
  }
}

$("limpar").addEventListener("click", async () => {
  if (!confirm("Apagar todo o histórico de análises?")) return;
  await chamar("/api/historico", { method: "DELETE" }).catch(() => {});
  carregarHistorico();
});

carregarHistorico();
