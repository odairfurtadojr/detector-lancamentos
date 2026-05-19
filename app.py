# app.py
# ==========================================================
# DETECTOR DE LANÇAMENTOS UBIQUITI
# ==========================================================

import re
import pandas as pd
import streamlit as st

from datetime import datetime
from sqlalchemy import create_engine

from playwright.sync_api import sync_playwright

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
# FORMATAR NOME
# ==========================================================

def formatar_nome(slug):

    partes_nome = slug.split("-")

    partes_formatadas = []

    for p in partes_nome:

        upper_words = {

            "udm",
            "ucg",
            "u7",
            "u6",
            "u5",
            "u4",
            "u3",
            "u2",
            "u1",
            "nvr",
            "xgs",
            "ai",
            "lte",
            "wan",
            "lan",
            "vpn",
            "dns",
            "dhcp",
            "rgb",
            "led",
            "sfp",
            "sfp+",
            "poe",
            "wifi"
        }

        if p.lower() in upper_words:

            partes_formatadas.append(
                p.upper()
            )

        else:

            partes_formatadas.append(
                p.capitalize()
            )

    nome = "-".join(
        partes_formatadas
    )

    correcoes = {

        "POE":
        "PoE",

        "RJ45":
        "RJ45",

        "USL-Relay":
        "Usl-Relay",

        "Pocketkeyfob":
        "Pocket-Keyfob"
    }

    for antigo, novo in correcoes.items():

        nome = nome.replace(
            antigo,
            novo
        )

    return nome

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

                        m = m.replace("\\/", "/")

                        m = m.split("?")[0]

                        m = m.split("#")[0]

                        m = m.rstrip("/")

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

                        link = (
                            "https://techspecs.ui.com"
                            + m
                        )

                        partes = [

                            p.strip()

                            for p in m.split("/")

                            if p.strip()
                        ]

                        if len(partes) < 3:
                            continue

                        slug = partes[-1]

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

                        chave = link.lower()

                        if chave in visitados:
                            continue

                        visitados.add(chave)

                        nome = formatar_nome(slug)

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

        atuais.reset_index(drop=True).to_sql(

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

    final = pd.concat([

        banco,
        novos
    ])

    final.reset_index(drop=True).to_sql(

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
    "📡 Detector de Lançamentos Ubiquiti"
)

st.divider()

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