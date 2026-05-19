# app.py
# ==========================================================
# UBIQUITI TECHSPECS MONITOR
# ==========================================================

import re
import time

import pandas as pd
import streamlit as st

from datetime import datetime
from sqlalchemy import create_engine

from playwright.sync_api import sync_playwright

import yagmail

# ==========================================================
# EMAIL
# ==========================================================

EMAIL = "seu_email@empresa.com"
SENHA = "sua_senha"

DESTINATARIOS = [
    "seu_email@empresa.com"
]

# ==========================================================
# DATABASE
# ==========================================================

engine = create_engine(
    "sqlite:///ubiquiti_history.db"
)

# ==========================================================
# CRIAR BANCO
# ==========================================================

def criar_banco():

    try:

        pd.read_sql(
            "produtos",
            engine
        )

    except:

        vazio = pd.DataFrame(columns=[

            "nome",
            "categoria",
            "link",
            "primeira_detecao",
            "novo"
        ])

        vazio.to_sql(

            "produtos",
            engine,
            if_exists="replace",
            index=False
        )

# ==========================================================
# EMAIL
# ==========================================================

def enviar_email(
    assunto,
    mensagem
):

    try:

        yag = yagmail.SMTP(

            user=EMAIL,
            password=SENHA,
            host="smtp.office365.com",
            port=587,
            smtp_starttls=True,
            smtp_ssl=False
        )

        yag.send(

            to=DESTINATARIOS,
            subject=assunto,
            contents=mensagem
        )

        return True

    except Exception as e:

        st.error(
            f"Erro ao enviar e-mail: {e}"
        )

        return False

# ==========================================================
# EMAIL NOVO PRODUTO
# ==========================================================

def email_novo_produto(row):

    enviar_email(

        "[UBIQUITI] Novo Produto Detectado",

        f"""
Novo produto detectado.

Produto:
{row['nome']}

Categoria:
{row['categoria']}

Link:
{row['link']}

Data:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    )

# ==========================================================
# SCRAPER
# ==========================================================

def buscar_produtos():

    produtos = []

    visitados = set()

    categorias = {

        "Cloud Gateways":
        "https://techspecs.ui.com/unifi/cloud-gateways",

        "Switching":
        "https://techspecs.ui.com/unifi/switching",

        "WiFi":
        "https://techspecs.ui.com/unifi/wifi",

        "Camera Security":
        "https://techspecs.ui.com/unifi/cameras-nvrs",

        "Door Access":
        "https://techspecs.ui.com/unifi/door-access",

        "Integrations":
        "https://techspecs.ui.com/unifi/integrations",

        "Advanced Hosting":
        "https://techspecs.ui.com/unifi/advanced-hosting",

        "Accessories":
        "https://techspecs.ui.com/unifi/accessories"
    }

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        for categoria, url in categorias.items():

            try:

                print("=" * 60)
                print(f"VARRENDO: {categoria}")
                print("=" * 60)

                page.goto(
                    url,
                    timeout=120000,
                    wait_until="networkidle"
                )

                page.wait_for_timeout(5000)

                # ==================================================
                # SCROLL COMPLETO
                # ==================================================

                for _ in range(100):

                    page.mouse.wheel(
                        0,
                        50000
                    )

                    page.wait_for_timeout(300)

                page.wait_for_timeout(3000)

                # ==================================================
                # HTML
                # ==================================================

                html = page.content()

                # ==================================================
                # REGEX
                # ==================================================

                regex = r'\/unifi\/[^"\']+'

                matches = re.findall(
                    regex,
                    html
                )

                encontrados = 0

                for m in matches:

                    try:

                        # ==========================================
                        # LIMPEZA
                        # ==========================================

                        m = m.replace("\\/", "/")

                        m = m.split("?")[0]

                        m = m.split("#")[0]

                        m = m.rstrip("/")

                        # ==========================================
                        # IGNORA ARQUIVOS
                        # ==========================================

                        extensoes = [

                            ".svg",
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".gif",
                            ".webp",
                            ".css",
                            ".js",
                            ".json"
                        ]

                        if any(
                            ext in m.lower()
                            for ext in extensoes
                        ):
                            continue

                        # ==========================================
                        # URL
                        # ==========================================

                        link = (
                            "https://techspecs.ui.com"
                            + m
                        )

                        partes = [

                            p.strip()

                            for p in m.split("/")

                            if p.strip()
                        ]

                        # ==========================================
                        # VALIDA
                        # ==========================================

                        if len(partes) < 3:
                            continue

                        slug = partes[-1]

                        # ==========================================
                        # BLACKLIST
                        # ==========================================

                        blacklist = [

                            "switching",
                            "wifi",
                            "cloud-gateways",
                            "cameras-nvrs",
                            "door-access",
                            "integrations",
                            "advanced-hosting",
                            "accessories",

                            "compare",
                            "builder",
                            "matrix",

                            "store",
                            "downloads",
                            "support",

                            "products",
                            "all"
                        ]

                        if slug.lower() in blacklist:
                            continue

                        # ==========================================
                        # DUPLICADOS
                        # ==========================================

                        chave = link.lower()

                        if chave in visitados:
                            continue

                        visitados.add(chave)

                        # ==========================================
                        # NOME
                        # ==========================================

                        nome = (

                            slug
                            .replace("-", " ")
                            .replace("_", " ")
                            .title()
                        )

                        # ==========================================
                        # CORREÇÕES
                        # ==========================================

                        correcoes = {

                            "8 Poe":
                            "8 PoE",

                            "Ucg Fiber":
                            "UCG Fiber",

                            "U7 Pro Xgs":
                            "U7 Pro XGS",

                            "Rj45 Inline Coupler Indoor":
                            "RJ45 Inline Coupler Indoor",

                            "Rj45 Inline Coupler Outdoor":
                            "RJ45 Inline Coupler Outdoor",

                            "Pocketkeyfob":
                            "Pocket Keyfob"
                        }

                        if nome in correcoes:

                            nome = correcoes[nome]

                        produtos.append({

                            "nome":
                            nome,

                            "categoria":
                            categoria,

                            "link":
                            link
                        })

                        encontrados += 1

                    except Exception as e:

                        print(
                            f"ERRO MATCH: {e}"
                        )

                print(
                    f"PRODUTOS: {encontrados}"
                )

            except Exception as e:

                print(
                    f"ERRO: {e}"
                )

        browser.close()

    # ======================================================
    # DATAFRAME
    # ======================================================

    df = pd.DataFrame(produtos)

    if df.empty:

        return pd.DataFrame(columns=[

            "nome",
            "categoria",
            "link"
        ])

    # ======================================================
    # REMOVE DUPLICADOS
    # ======================================================

    df = (
        df
        .drop_duplicates(
            subset=["link"]
        )
        .reset_index(drop=True)
    )

    # ======================================================
    # LOG FINAL
    # ======================================================

    print("\n" + "=" * 60)
    print("CONTAGEM FINAL")
    print("=" * 60)

    print(
        df["categoria"]
        .value_counts()
        .sort_index()
    )

    print("=" * 60)

    print(
        f"TOTAL PRODUTOS: {len(df)}"
    )

    print("=" * 60)

    return df

# ==========================================================
# HISTÓRICO
# ==========================================================

def atualizar_historico():

    atuais = buscar_produtos()

    if atuais.empty:
        return 0

    banco = pd.read_sql(
        "produtos",
        engine
    )

    if banco.empty:

        atuais["primeira_detecao"] = datetime.now()

        atuais["novo"] = False

        atuais.to_sql(

            "produtos",
            engine,
            if_exists="replace",
            index=False
        )

        return 0

    existentes = set(
        banco["link"].tolist()
    )

    novos = atuais[
        ~atuais["link"].isin(
            existentes
        )
    ].copy()

    if novos.empty:
        return 0

    novos["primeira_detecao"] = datetime.now()

    novos["novo"] = True

    for _, row in novos.iterrows():

        email_novo_produto(row)

    final = pd.concat([

        banco,
        novos
    ])

    final.to_sql(

        "produtos",
        engine,
        if_exists="replace",
        index=False
    )

    return len(novos)

# ==========================================================
# STREAMLIT
# ==========================================================

st.set_page_config(

    page_title="Detector de Lançamentos Ubiquiti",
    layout="wide"
)

criar_banco()

st.title(
    "📡 Ubiquiti TechSpecs Monitor"
)

# ==========================================================
# UPDATE
# ==========================================================

if st.button(
    "🔄 Atualizar Agora"
):

    with st.spinner(
        "Executando varredura..."
    ):

        qtd = atualizar_historico()

    st.success(
        f"{qtd} novos produtos encontrados."
    )

# ==========================================================
# LEITURA
# ==========================================================

df = pd.read_sql(
    "produtos",
    engine
)

# ==========================================================
# KPIS
# ==========================================================

st.subheader("📊 Indicadores")

col1, col2 = st.columns(2)

col1.metric(
    "Total Produtos",
    len(df)
)

col2.metric(

    "Novos Produtos",

    len(
        df[df["novo"] == True]
    )
)

st.divider()

# ==========================================================
# CATEGORIAS
# ==========================================================

st.subheader(
    "📂 Categorias"
)

cats = (
    df["categoria"]
    .value_counts()
)

for cat, qtd in cats.items():

    st.write(
        f"• {cat}: {qtd}"
    )

st.divider()

# ==========================================================
# HISTÓRICO
# ==========================================================

st.subheader(
    "📦 Produtos"
)

st.dataframe(

    df.sort_values([
        "categoria",
        "nome"
    ]),

    width="stretch"
)

st.divider()

st.caption(

    f"""
Última atualização:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
)