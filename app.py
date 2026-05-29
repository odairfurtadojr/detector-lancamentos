# app.py
# ==========================================================
# DETECTOR DE LANÇAMENTOS UBIQUITI
# ==========================================================

import os
import re
import subprocess
import sys

import pandas as pd
import streamlit as st

from datetime import datetime
from sqlalchemy import create_engine, inspect as sa_inspect, text

# ==========================================================
# AUTO INSTALL PLAYWRIGHT CHROMIUM
# ==========================================================

PLAYWRIGHT_PATH = os.path.expanduser("~/.cache/ms-playwright")

if not os.path.exists(PLAYWRIGHT_PATH):

    try:

        subprocess.run(

            [
                sys.executable,
                "-m",
                "playwright",
                "install",
                "chromium"
            ],

            check=False
        )

    except Exception as e:

        print(
            f"ERRO INSTALL PLAYWRIGHT: {e}"
        )

# ==========================================================
# PLAYWRIGHT
# ==========================================================

from playwright.sync_api import sync_playwright

# ==========================================================
# DATABASE
# ==========================================================

engine = create_engine(
    st.secrets["DATABASE_URL"],
    pool_pre_ping=True
)

# ==========================================================
# CRIAR BANCO
# ==========================================================

def criar_banco():

    inspector = sa_inspect(engine)

    if not inspector.has_table("produtos"):

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

    for p in partes_nome:

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

            headless=True,

            args=[

                "--no-sandbox",

                "--disable-setuid-sandbox",

                "--disable-dev-shm-usage",

                "--disable-gpu",

                "--disable-software-rasterizer",

                "--disable-extensions",

                "--disable-background-networking",

                "--disable-background-timer-throttling",

                "--disable-renderer-backgrounding",

                "--disable-features=site-per-process"
            ]
        )

        page = browser.new_page(

            viewport={

                "width": 1920,
                "height": 1080
            },

            user_agent=(

                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

        for categoria, url in categorias.items():

            try:

                print("=" * 60)
                print(f"VARRENDO: {categoria}")
                print("=" * 60)

                page.goto(

                    url,

                    timeout=120000,

                    wait_until="domcontentloaded"
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

                            parte.strip()

                            for parte in m.split("/")

                            if parte.strip()
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

        return 0, pd.DataFrame()

    try:
        banco = pd.read_sql(
            "SELECT * FROM produtos",
            engine
        )
    except Exception:
        banco = pd.DataFrame(columns=[
            "nome",
            "categoria",
            "link",
            "primeira_detecao",
            "novo"
        ])

    if banco.empty:

        atuais["primeira_detecao"] = datetime.now()

        atuais["novo"] = False

        atuais.reset_index(drop=True).to_sql(

            "produtos",
            engine,
            if_exists="replace",
            index=False
        )

        return 0, pd.DataFrame()

    existentes = set(
        banco["link"].tolist()
    )

    novos = atuais[
        ~atuais["link"].isin(
            existentes
        )
    ].copy()

    if novos.empty:

        return 0, pd.DataFrame()

    novos["primeira_detecao"] = datetime.now()

    novos["novo"] = True

    banco["novo"] = False

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

    return len(novos), novos

# ==========================================================
# MARCAR IDENTIFICADO
# ==========================================================

def marcar_identificado(link):

    with engine.connect() as conn:

        conn.execute(
            text(
                "UPDATE produtos SET novo = FALSE WHERE link = :link"
            ),
            {"link": link}
        )

        conn.commit()

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
# SESSION STATE
# ==========================================================

if "ultimos_novos" not in st.session_state:

    st.session_state.ultimos_novos = pd.DataFrame()

# ==========================================================
# UPDATE
# ==========================================================

if st.button(
    "🔄 Atualizar Agora"
):

    with st.spinner(
        "Executando varredura..."
    ):

        qtd, novos = atualizar_historico()

    st.session_state.ultimos_novos = novos

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
# NOVOS LANÇAMENTOS
# ==========================================================

novos_df = st.session_state.ultimos_novos

if not novos_df.empty:

    st.subheader(
        "🆕 Novos Lançamentos Detectados"
    )

    for i, row in novos_df.iterrows():

        with st.container(border=True):

            st.markdown(
                f"## {row['nome']}"
            )

            col1, col2, col3 = st.columns([3, 3, 2])

            col1.markdown(
                f"**Categoria:** {row['categoria']}"
            )

            col2.markdown(
                f"""
                [🔗 Abrir Produto]({row['link']})
                """
            )

            if col3.button(
                "✅ Identificar lançamento",
                key=f"identificar_{i}"
            ):

                marcar_identificado(row["link"])

                st.session_state.ultimos_novos = (
                    st.session_state.ultimos_novos[
                        st.session_state.ultimos_novos["link"] != row["link"]
                    ]
                )

                st.rerun()

            st.success(
                "Novo produto detectado!"
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

# ==========================================================
# DESTAQUE VISUAL
# ==========================================================

def destacar_novos(linha):

    if linha["novo"] == True:

        return [
            "background-color: #16351c; color: #7CFC00;"
        ] * len(linha)

    return [""] * len(linha)

styled_df = (
    df
    .sort_values([
        "categoria",
        "nome"
    ])
    .style
    .apply(
        destacar_novos,
        axis=1
    )
)

st.dataframe(

    styled_df,

    use_container_width=True
)

st.divider()

st.caption(

    f"""
Última atualização:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
)
