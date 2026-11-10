# ☠ Analisador Caveira

Detector de phishing (golpes) com visual preto e caveiras. Analisa:

- **Links (URL)** — typosquatting (nomes que imitam marcas, como `paypa1` ou `nubank-seguro`), IP no lugar do nome, `@` escondendo o destino, encurtadores, terminações suspeitas (`.xyz`, `.top`...), falta de HTTPS, punycode, muitos subdomínios e palavras de isca. Com a opção "Consultar a internet": idade do domínio (RDAP/WHOIS), certificado SSL e para onde o link redireciona.
- **E-mails (.eml)** — `Reply-To` e `Return-Path` diferentes do remetente, falha de SPF/DKIM/DMARC, nome de marca no remetente sem bater com o domínio, frases de golpe e análise de cada link (até 20).
- **Mensagens coladas** — SMS, WhatsApp, corpo ou código-fonte de e-mail: frases de golpe ("troquei de número", "conta bloqueada", "pix pendente"...) + análise dos links. Ótimo para usar no celular.

A nota vai de 0 a 100: **0–19 tranquilo** (1 caveira), **20–49 suspeito** (2), **50–100 perigo** (3).

## Como rodar (Windows, jeito fácil)

1. Instale o Python 3.10 ou mais novo em https://www.python.org/downloads/ (marque **"Add Python to PATH"** na instalação).
2. Dê dois cliques em **`iniciar.bat`**. Na primeira vez ele instala tudo (demora um pouquinho).
3. Abra **http://127.0.0.1:8000** no navegador.

Para parar, feche a janela preta ou aperte `Ctrl + C` nela.

## Como rodar no Linux (Kali, Ubuntu, Debian)

```bash
sudo apt update && sudo apt install -y python3 python3-venv
cd analisador-caveira
chmod +x iniciar.sh
./iniciar.sh              # ou ./iniciar.sh --celular
```

Se você copiou a pasta do Windows, o script apaga a `.venv` do Windows e cria outra.

## Como rodar (pelo terminal)

```bash
python -m venv .venv
.venv\Scripts\activate        # no Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Usar no celular

1. Celular e computador no **mesmo Wi-Fi**.
2. Rode **`iniciar-celular.bat`** (ou `python app.py --celular`).
3. A janela mostra um endereço como `http://192.168.0.15:8000` — digite ele no navegador do celular.
4. Se o Windows perguntar sobre o Firewall, permita em **Redes privadas**.

> Nesse modo qualquer pessoa no mesmo Wi-Fi consegue abrir o analisador e ver o histórico. Use só em rede de casa.

## Testes

```bash
python -m pytest -q
```

Há exemplos para testar na pasta `exemplos/` (um e-mail de golpe, um e-mail limpo e uma mensagem de WhatsApp).

## Estrutura

```
app.py               servidor web (FastAPI) e rotas /api/...
historico.py         histórico em SQLite (arquivo historico.db)
analise/
  __init__.py        junta tudo: URL, e-mail e texto -> nota de risco
  dominio.py         separa a URL em partes (entende .com.br)
  marcas.py          marcas imitadas e comparação de nomes parecidos
  regras_url.py      regras que olham só o texto do link
  rede.py            idade do domínio, SSL e redirecionamentos (+ proteção SSRF)
site/                interface (HTML, CSS, JS e a caveira em SVG)
exemplos/            arquivos para testar
tests/               testes automáticos
```

## Segurança da ferramenta

- Antes de acessar qualquer endereço, o analisador confere se ele não aponta para a sua rede interna (proteção contra SSRF), inclusive em cada redirecionamento.
- A página do link suspeito **nunca é baixada nem aberta** — só os cabeçalhos de redirecionamento são lidos.
- Arquivos `.eml` de até 2 MB, lidos só na memória (não são salvos).
- Links aparecem desarmados (`hxxp://site[.]com`) e todo texto entra na página com `textContent` (sem risco de XSS).

## Créditos

Inspirado nas ideias do projeto [VitoriaChuarts/analisador-de-phishing](https://github.com/VitoriaChuarts/analisador-de-phishing). Como aquele repositório não tem licença, nenhum código dele foi copiado: tudo aqui foi escrito do zero.

## Licença

**Código aberto** sob a [licença MIT](LICENSE): você pode usar, copiar, modificar e distribuir à vontade, desde que mantenha o aviso de copyright de Hiagor Franklin.

## Aviso

Projeto educacional. A nota é uma estimativa por regras e não substitui um especialista em segurança.
