# app.py
# ==========================================================
# UBIQUITI TECHSPECS MONITOR
# ==========================================================

import re
import pandas as pd
import streamlit as st

from datetime import datetime
from sqlalchemy import create_engine

from playwright.sync_api import sync_playwright

import yagmail

# ==========================================================
# DATABASE
# ==========================================================

engine = create_engine(
    "sqlite:///ubiquiti_history.db"
)

# ==========================================================
# SESSION STATE
# ==========================================================

if "email_remetente" not in st.session_state:

    st.session_state.email_remetente = ""

if "senha_email" not in st.session_state:

    st.session_state.senha_email = ""

if "emails_destino" not in st.session_state:

    st.session_state.emails_destino = ""

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

        email = (
            st.session_state
            .email_remetente
            .strip()
        )

        senha = (
            st.session_state
            .senha_email
            .strip()
        )

        destinos = [

            x.strip()

            for x in (
                st.session_state
                .emails_destino
                .splitlines()
            )

            if x.strip()
        ]

        if not email:

            st.error(
                "Informe o e-mail remetente."
            )

            return False

        if not senha:

            st.error(
                "Informe a senha."
            )

            return False

        if not destinos:

            st.error(
                "Informe ao menos um destinatário."
            )

            return False

        yag = yagmail.SMTP(

            user=email,
            password=senha,
            host="smtp.office365.com",
            port=587,
            smtp_starttls=True,
            smtp_ssl=False
        )

        yag.send(

            to=destinos,
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

    for _, row in novos.iterrows():

        email_novo_produto(row)

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

    page_title="Ubiquiti TechSpecs Monitor",
    layout="wide"
)

criar_banco()

st.title(
    "📡 Ubiquiti TechSpecs Monitor"
)

# ==========================================================
# CONFIGURAÇÃO E-MAIL
# ==========================================================

st.subheader(
    "📧 Configuração de Notificações"
)

col1, col2 = st.columns(2)

with col1:

    st.session_state.email_remetente = st.text_input(

        "E-mail Remetente",

        value=st.session_state.email_remetente,

        placeholder="usuario@empresa.com"
    )

with col2:

    st.session_state.senha_email = st.text_input(

        "Senha",

        value=st.session_state.senha_email,

        type="password"
    )

st.session_state.emails_destino = st.text_area(

    "Destinatários (1 por linha)",

    value=st.session_state.emails_destino,

    height=120,

    placeholder="""
usuario1@empresa.com
usuario2@empresa.com
usuario3@empresa.com
"""
)

# ==========================================================
# TESTE E-MAIL
# ==========================================================

if st.button(
    "📨 Testar Notificação"
):

    ok = enviar_email(

        "[UBIQUITI] Teste de Notificação",

        f"""
Teste de envio realizado com sucesso.

Horário:
{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    )

    if ok:

        st.success(
            "E-mail enviado com sucesso."
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