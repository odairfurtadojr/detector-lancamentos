# app.py
# ==========================================================
# DETECTOR DE LANÇAMENTOS UBIQUITI
# ==========================================================
#
# EXECUÇÃO:
#
# py -3.11 -m streamlit run app.py
#
# IMPORTANTE:
#
# Delete o arquivo:
# ubiquiti_history.db
#
# antes da primeira execução.
#
# ==========================================================

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from playwright.sync_api import sync_playwright
import yagmail

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

EMAIL = "odair.furtado@ui.com"
SENHA = "ww852000000"

DESTINATARIOS = [
    "odair.furtado@ui.com"
]

engine = create_engine(
    "sqlite:///ubiquiti_history.db"
)

# ==========================================================
# ESTILO
# ==========================================================

st.set_page_config(
    page_title="Detector de Lançamentos Ubiquiti",
    layout="wide"
)

st.markdown("""
<style>

.block-container{
    padding-top: 1.5rem;
}

div[data-testid="metric-container"]{
    background-color:#111827;
    border:1px solid #1f2937;
    padding:15px;
    border-radius:12px;
}

div[data-testid="metric-container"] label{
    color:#9ca3af !important;
}

div[data-testid="metric-container"] div{
    color:white !important;
}

.stButton > button{
    border-radius:10px;
}

.email-button button{
    background-color:#111827 !important;
    color:white !important;
    border:1px solid #374151 !important;
}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# BANCO
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

        st.error(f"Erro e-mail: {e}")

        return False


def email_teste():

    assunto = "[UBIQUITI] Teste de Notificação"

    mensagem = f"""
Teste do sistema de monitoramento.

Horário:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""

    return enviar_email(
        assunto,
        mensagem
    )


def email_novo_produto(nome, categoria, link):

    assunto = "[UBIQUITI] Novo Produto Detectado"

    mensagem = f"""
Novo produto detectado no TechSpecs.

Produto:
{nome}

Categoria:
{categoria}

Link:
{link}

Data:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""

    return enviar_email(
        assunto,
        mensagem
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

        "UISP Wireless":
        "https://techspecs.ui.com/uisp/wireless",

        "UISP Switching":
        "https://techspecs.ui.com/uisp/switching",

        "UISP Routing":
        "https://techspecs.ui.com/uisp/routing",

        "UISP Accessories":
        "https://techspecs.ui.com/uisp/accessories"
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

                # ======================================
                # SCROLL
                # ======================================

                for _ in range(50):

                    page.mouse.wheel(0, 50000)

                    page.wait_for_timeout(300)

                # ======================================
                # PEGA TODOS LINKS
                # ======================================

                hrefs = page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.href)"
                )

                print(f"HREFS ENCONTRADOS: {len(hrefs)}")

                for href in hrefs:

                    try:

                        if not href:
                            continue

                        if "techspecs.ui.com" not in href:
                            continue

                        partes = href.replace(
                            "https://techspecs.ui.com/",
                            ""
                        ).split("/")

                        # produto real:
                        # unifi/switching/produto
                        if len(partes) < 3:
                            continue

                        slug = partes[-1]

                        nome = (
                            slug
                            .replace("-", " ")
                            .title()
                        )

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

        print("NENHUM PRODUTO ENCONTRADO")

        return pd.DataFrame(columns=[
            "nome",
            "categoria",
            "link"
        ])

    df = df.drop_duplicates(
        subset=["nome", "link"]
    )

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

    # primeira execução
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
# STREAMLIT
# ==========================================================

criar_banco()

# ==========================================================
# HEADER
# ==========================================================

col1, col2 = st.columns([8,1])

with col1:

    st.title("📡 Detector de Lançamentos Ubiquiti")

with col2:

    st.markdown(
        '<div class="email-button">',
        unsafe_allow_html=True
    )

    if st.button("📧 Teste"):

        ok = email_teste()

        if ok:

            st.toast(
                "E-mail enviado."
            )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# ==========================================================
# BOTÃO UPDATE
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
# KPIs
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
# HISTÓRICO COMPLETO
# ==========================================================

st.subheader("📦 Histórico Completo")

st.dataframe(
    filtrado.sort_values(
        "nome"
    ),
    width="stretch"
)

# ==========================================================
# RODAPÉ
# ==========================================================

st.divider()

st.caption(
    f"""
Última atualização:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
)