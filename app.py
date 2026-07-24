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

_db_url = st.secrets["DATABASE_URL"]
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    _db_url,
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

    import json as _json

    produtos = []

    categorias = {

        "Cloud Gateways":
        "https://techspecs.ui.com/unifi/cloud-gateways",

        "Switching":
        "https://techspecs.ui.com/unifi/switching",

        "WiFi":
        "https://techspecs.ui.com/unifi/wifi",

        "Camera Security":
        "https://techspecs.ui.com/unifi/physical-security",

        "Door Access":
        "https://techspecs.ui.com/unifi/door-access",

        "Integrations":
        "https://techspecs.ui.com/unifi/integrations",

        "Advanced Hosting":
        "https://techspecs.ui.com/unifi/advanced-hosting",

        "Accessories":
        "https://techspecs.ui.com/unifi/accessories"
    }

    blacklist = {
        "switching", "wifi", "cloud-gateways", "cameras-nvrs",
        "physical-security", "door-access", "integrations",
        "advanced-hosting", "accessories", "compare", "builder",
        "matrix", "store", "downloads", "support", "products", "all"
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

            cat_path = url.split("/unifi/")[-1]

            print("=" * 60)
            print(f"VARRENDO: {categoria}")
            print("=" * 60)

            try:

                page.goto(
                    url,
                    timeout=120000,
                    wait_until="networkidle"
                )

                page.wait_for_timeout(2000)

                # ==================================================
                # EXTRAI SLUGS DO __NEXT_DATA__ (JSON embutido)
                # ==================================================

                next_data = page.evaluate(
                    "JSON.parse(document.getElementById('__NEXT_DATA__').textContent)"
                )

                raw = _json.dumps(next_data)

                slugs_brutos = set(
                    re.findall(r'"slug"\s*:\s*"([^"]+)"', raw)
                )

                encontrados = 0

                visitados_categoria = set()

                for slug in slugs_brutos:

                    slug_lower = slug.lower()

                    if slug_lower in blacklist:
                        continue

                    if slug_lower in visitados_categoria:
                        continue

                    visitados_categoria.add(slug_lower)

                    link = (
                        "https://techspecs.ui.com"
                        f"/unifi/{cat_path}/{slug}"
                    )

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

                print(f"PRODUTOS: {encontrados}")

            except Exception as e:

                print(f"ERRO: {e}")

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

    slugs_existentes = set(
        banco["link"]
        .str.rstrip("/")
        .str.split("/")
        .str[-1]
        .str.lower()
        .tolist()
    )

    atuais["_slug"] = (
        atuais["link"]
        .str.rstrip("/")
        .str.split("/")
        .str[-1]
        .str.lower()
    )

    novos = atuais[
        ~atuais["_slug"].isin(slugs_existentes)
    ].drop(columns=["_slug"]).copy()

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
# LIMPAR DUPLICATAS
# ==========================================================

def limpar_duplicatas():

    try:
        banco = pd.read_sql("SELECT * FROM produtos", engine)
    except Exception:
        return 0

    if banco.empty:
        return 0

    banco["_slug"] = (
        banco["link"]
        .str.rstrip("/")
        .str.split("/")
        .str[-1]
        .str.lower()
    )

    banco_limpo = (
        banco
        .sort_values("primeira_detecao")
        .drop_duplicates(subset=["_slug"], keep="first")
        .drop(columns=["_slug"])
        .reset_index(drop=True)
    )

    removidos = len(banco) - len(banco_limpo)

    if removidos > 0:

        banco_limpo.to_sql(
            "produtos",
            engine,
            if_exists="replace",
            index=False
        )

    return removidos

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


def marcar_todos_identificados():

    with engine.connect() as conn:

        conn.execute(
            text(
                "UPDATE produtos SET novo = FALSE WHERE novo = TRUE"
            )
        )

        conn.commit()

# ==========================================================
# STREAMLIT
# ==========================================================

st.set_page_config(

    page_title="Detector de Lançamentos Ubiquiti",
    layout="wide"
)

try:
    criar_banco()
    limpar_duplicatas()
except Exception as _e:
    st.error(f"Erro de conexão com banco de dados:\n\n{_e}")
    st.stop()

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

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Produtos",
    len(df)
)

qtd_novos = int(df["novo"].fillna(False).astype(bool).sum())

with col2:

    if st.button("✅ Identificar Lançamentos"):
        marcar_todos_identificados()
        st.rerun()

    st.metric(
        "Novos Produtos",
        qtd_novos
    )

with col3:

    if st.button("🧹 Remover Duplicatas"):
        removidos = limpar_duplicatas()
        st.success(f"{removidos} duplicatas removidas.")
        st.rerun()

st.divider()

# ==========================================================
# NOVOS LANÇAMENTOS
# ==========================================================

novos_df = df[df["novo"].fillna(False).astype(bool)].copy()

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

    if bool(linha["novo"]):

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
