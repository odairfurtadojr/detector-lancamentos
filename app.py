# app.py
# ==========================================================
# DETECTOR DE LANÇAMENTOS UBIQUITI - UNIFI ONLY
# ==========================================================

import re
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from playwright.sync_api import sync_playwright
import yagmail

# ==========================================================
# CONFIGURAÇÕES DE E-MAIL
# ==========================================================

EMAIL = "seu_email@empresa.com"
SENHA = "sua_senha"

DESTINATARIOS = [
    "destinatario1@empresa.com",
    "destinatario2@empresa.com"
]

# ==========================================================
# BANCO
# ==========================================================

engine = create_engine(
    "sqlite:///ubiquiti_history.db"
)

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
# STREAMLIT
# ==========================================================

st.set_page_config(
    page_title="Detector de Lançamentos Ubiquiti",
    layout="wide"
)

# ==========================================================
# CSS
# ==========================================================

st.markdown("""
<style>

.block-container{
    padding-top:1.5rem;
}

div[data-testid="metric-container"]{
    background:#111827;
    border:1px solid #1f2937;
    border-radius:12px;
    padding:15px;
}

.email-button button{
    background:#111827 !important;
    color:white !important;
    border:1px solid #374151 !important;
}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# EMAIL
# ==========================================================

def enviar_email(assunto, mensagem):

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

        st.error(f"Erro ao enviar e-mail: {e}")

        return False


def email_teste():

    return enviar_email(
        "[UBIQUITI] Teste",
        f"""
Teste de notificação.

Horário:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    )


def email_novo_produto(nome, categoria, link):

    return enviar_email(
        "[UBIQUITI] Novo Produto Detectado",
        f"""
Novo produto detectado.

Produto:
{nome}

Categoria:
{categoria}

Link:
{link}

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

        "Switching":
        "https://techspecs.ui.com/unifi/switching",

        "WiFi":
        "https://techspecs.ui.com/unifi/wifi",

        "Routing":
        "https://techspecs.ui.com/unifi/routing",

        "Cameras":
        "https://techspecs.ui.com/unifi/cameras-nvrs",

        "Access":
        "https://techspecs.ui.com/unifi/door-access",

        "Phones":
        "https://techspecs.ui.com/unifi/phones",

        "Power":
        "https://techspecs.ui.com/unifi/power-tech",

        "Cloud Gateways":
        "https://techspecs.ui.com/unifi/cloud-gateways",

        "Accessories":
        "https://techspecs.ui.com/unifi/accessories",

        "Integrations":
        "https://techspecs.ui.com/unifi/integrations",

        "Advanced Hosting":
        "https://techspecs.ui.com/unifi/advanced-hosting"
    }

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        for categoria, url in categorias.items():

            try:

                print(f"VARRENDO: {categoria}")

                page.goto(
                    url,
                    timeout=120000
                )

                page.wait_for_timeout(5000)

                # ==================================================
                # SCROLL
                # ==================================================

                for _ in range(50):

                    page.mouse.wheel(0, 50000)

                    page.wait_for_timeout(300)

                # ==================================================
                # CARDS
                # ==================================================

                cards = page.locator(
                    "a[href*='/unifi/']"
                )

                total_cards = cards.count()

                print(f"CARDS: {total_cards}")

                for i in range(total_cards):

                    try:

                        card = cards.nth(i)

                        # ==================================================
                        # LINK REAL DO PRODUTO
                        # ==================================================

                        href = None

                        links = card.locator("a").all()

                        for lnk in links:

                            try:

                                h = lnk.get_attribute("href")

                                if not h:
                                    continue

                                path_tmp = h.replace(
                                    "https://techspecs.ui.com/",
                                    ""
                                ).strip("/")

                                partes_tmp = path_tmp.split("/")

                                if len(partes_tmp) >= 3:

                                    href = h
                                    break

                            except:
                                pass

                        if not href:
                            href = card.get_attribute("href")

                        if not href:
                            continue

                        # ==================================================
                        # URL COMPLETA
                        # ==================================================

                        if "techspecs.ui.com" not in href:

                            href = (
                                "https://techspecs.ui.com"
                                + href
                            )

                        href = href.split("#")[0]

                        # ==================================================
                        # PRODUTO REAL
                        # ==================================================

                        path = href.replace(
                            "https://techspecs.ui.com/",
                            ""
                        ).strip("/")

                        partes = path.split("/")

                        if len(partes) < 3:
                            continue

                        slug = partes[-1]

                        blacklist = [
                            "unifi",
                            "switching",
                            "wifi",
                            "routing",
                            "cameras-nvrs",
                            "door-access",
                            "phones",
                            "power-tech",
                            "cloud-gateways",
                            "accessories",
                            "integrations",
                            "advanced-hosting"
                        ]

                        if slug in blacklist:
                            continue

                        # ==================================================
                        # NOME PELO SLUG (FONTE PRINCIPAL)
                        # ==================================================

                        slug_limpo = slug.split("?")[0]

                        nome = (
                            slug_limpo
                            .replace("-", " ")
                            .replace("_", " ")
                            .title()
                        )

                        # ==================================================
                        # CORREÇÕES MANUAIS
                        # ==================================================

                        correcoes = {

                            "Pocketkeyfob":
                            "Pocket Keyfob",

                            "Rj45 Inline Coupler Indoor":
                            "RJ45 Inline Coupler Indoor",

                            "Rj45 Inline Coupler Outdoor":
                            "RJ45 Inline Coupler Outdoor",

                            "Easy Cable":
                            "Easy Cable",

                            "8 Poe":
                            "8 PoE"
                        }

                        if nome in correcoes:
                            nome = correcoes[nome]

                        nome = nome.strip()

                        if len(nome) < 3:
                            continue

                        chave = f"{nome}|{href}"

                        if chave in visitados:
                            continue

                        visitados.add(chave)

                        produtos.append({
                            "nome": nome,
                            "categoria": categoria,
                            "link": href
                        })

                    except:
                        pass

            except Exception as e:

                print(e)

        browser.close()

    df = pd.DataFrame(produtos)

    if df.empty:

        return pd.DataFrame(columns=[
            "nome",
            "categoria",
            "link"
        ])

    df = df.drop_duplicates()

    print(f"TOTAL PRODUTOS: {len(df)}")

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
        ~atuais["link"].isin(existentes)
    ].copy()

    if novos.empty:
        return 0

    novos["primeira_detecao"] = datetime.now()

    novos["novo"] = True

    for _, row in novos.iterrows():

        email_novo_produto(
            row["nome"],
            row["categoria"],
            row["link"]
        )

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
# INICIALIZAÇÃO
# ==========================================================

criar_banco()

# ==========================================================
# HEADER
# ==========================================================

col1, col2 = st.columns([8,1])

with col1:

    st.title(
        "📡 Detector de Lançamentos Ubiquiti"
    )

with col2:

    st.markdown(
        '<div class="email-button">',
        unsafe_allow_html=True
    )

    if st.button("📧 Teste"):

        if email_teste():

            st.toast(
                "E-mail enviado."
            )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# ==========================================================
# UPDATE
# ==========================================================

if st.button("🔄 Atualizar Agora"):

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

total = len(df)

novos = len(
    df[df["novo"] == True]
)

categorias_contagem = (
    df["categoria"]
    .value_counts()
)

st.subheader("📊 Indicadores")

cols = st.columns(4)

cols[0].metric(
    "Total Produtos",
    total
)

cols[1].metric(
    "Novos Lançamentos",
    novos
)

i = 2

for categoria, qtd in categorias_contagem.items():

    if i >= 4:

        cols = st.columns(4)

        i = 0

    cols[i].metric(
        categoria,
        qtd
    )

    i += 1

st.divider()

# ==========================================================
# EXPORTAÇÃO CSV
# ==========================================================

st.subheader("📥 Exportação")

exportar_df = df.copy()

exportar_df["primeira_detecao"] = (
    exportar_df["primeira_detecao"]
    .astype(str)
)

csv = exportar_df.to_csv(
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

st.download_button(
    label="📄 Exportar CSV Completo",
    data=csv,
    file_name=f"""
ubiquiti_produtos_{
datetime.now().strftime('%Y%m%d_%H%M%S')
}.csv
""".replace("\n", ""),
    mime="text/csv"
)

st.divider()

# ==========================================================
# FILTROS
# ==========================================================

st.subheader("🔎 Filtros")

categorias_lista = sorted(
    df["categoria"]
    .dropna()
    .unique()
)

categoria_filtro = st.selectbox(
    "Categoria",
    ["Todas"] + categorias_lista
)

busca = st.text_input(
    "Buscar Produto"
)

filtrado = df.copy()

if categoria_filtro != "Todas":

    filtrado = filtrado[
        filtrado["categoria"]
        == categoria_filtro
    ]

if busca:

    filtrado = filtrado[
        filtrado["nome"]
        .str.contains(
            busca,
            case=False,
            na=False
        )
    ]

# ==========================================================
# NOVOS LANÇAMENTOS
# ==========================================================

st.subheader("🆕 Novos Lançamentos")

novos_df = filtrado[
    filtrado["novo"] == True
]

if novos_df.empty:

    st.info(
        "Nenhum lançamento novo."
    )

else:

    st.dataframe(
        novos_df.sort_values(
            "primeira_detecao",
            ascending=False
        ),
        width="stretch"
    )

# ==========================================================
# HISTÓRICO
# ==========================================================

st.subheader("📦 Histórico Completo")

st.dataframe(
    filtrado.sort_values(
        "nome"
    ),
    width="stretch"
)

st.divider()

st.caption(
    f"""
Última atualização:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
)