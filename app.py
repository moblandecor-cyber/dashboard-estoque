import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Dashboard de Estoque", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

SHEET_ID = "19lLWSJBYvuTzQn58mjD9P1i6pgx8M8T8Mputx5dceRY"
URL_LOG = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet=Estoque%20atual"
URL_CAT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Estoque+atual"

CORES = {
    "SUEDE":  ["AMARELO", "AZUL-MARINHO", "BEGE", "CAPPUCCINO", "CINZA", "MARROM", "PRETO", "ROSA", "TERRACOTA", "TIFFANY", "VERMELHO", "VERDE"],
    "VELUDO": ["AZUL-MARINHO", "BEGE", "CAPPUCCINO", "CINZA", "MARROM", "PRETO", "ROSA ESCURO", "ROSE", "TERRACOTA", "VERMELHO", "VERDE-MUSGO"],
    "CORANO": ["AZUL-MARINHO", "BEGE", "CAPPUCCINO", "CINZA", "PRETO", "ROSA", "MARROM", "TERRACOTA", "VERDE OLIVA", "VERMELHO"],
    "BOUCLE": ["BEGE", "CAPPUCCINO", "CINZA", "PRETO", "TERRACOTA"],
    "LINHO":  ["CINZA", "BEGE"],
}

def detecta_tecido(nome):
    n = nome.upper()
    for tecido in CORES:
        if tecido in n:
            return tecido
    return None

@st.cache_data(ttl=300)
def load_data():
    raw = pd.read_csv(URL_LOG, header=None, dtype=str)
    mov = raw[raw[1].notna() & (raw[1].str.strip() != "") & (raw[1].str.strip() != "PRODUTO")][[0,1,2,5]].copy()
    mov.columns = ["Data","Produto","Cor","Estoque"]
    mov["Data"]    = pd.to_datetime(mov["Data"], format="%d/%m/%Y", errors="coerce")
    mov["Estoque"] = pd.to_numeric(mov["Estoque"].str.replace(",","."), errors="coerce")
    mov = mov.dropna(subset=["Produto","Estoque"])
    mov["Produto"] = mov["Produto"].str.strip().str.upper()
    mov["Cor"]     = mov["Cor"].fillna("").str.strip().str.upper()
    atual = mov.sort_values("Data", na_position="first").groupby(["Produto","Cor"], as_index=False).last()[["Produto","Cor","Estoque","Data"]]

    cat_raw = pd.read_csv(URL_CAT, header=None, dtype=str)
    prefixos = ("POLTRONA", "PUFF", "NAMORADEIRA", "KIT")
    produtos_cat = cat_raw[1].dropna().str.strip().str.upper().pipe(lambda s: s[s.str.startswith(prefixos)]).unique().tolist()
    produtos_log = atual["Produto"].unique().tolist()
    todos_produtos = list(set(produtos_cat + produtos_log))

    registros = []
    for produto in todos_produtos:
        tecido = detecta_tecido(produto)
        if tecido:
            cores = CORES[tecido]
        else:
            cores = atual[atual["Produto"] == produto]["Cor"].unique().tolist()
        for cor in cores:
            registros.append({"Produto": produto, "Cor": cor})

    completo = pd.DataFrame(registros)
    df = completo.merge(atual, on=["Produto","Cor"], how="left")
    df["Estoque"] = df["Estoque"].fillna(0).astype(int)
    df["Data"]    = df["Data"].dt.strftime("%d/%m/%Y").fillna("sem registro")
    df["Nome"]    = df["Produto"] + " — " + df["Cor"]
    return df.sort_values(["Produto","Cor"]).reset_index(drop=True)

def status(row):
    if row["Estoque"] == 0:   return "🔴 Zerado"
    elif row["Estoque"] <= 2: return "🟠 Crítico"
    elif row["Estoque"] <= 5: return "🟡 Baixo"
    else:                      return "🟢 OK"

with st.sidebar:
    st.title("📦 Estoque")
    st.markdown("---")
    if st.button("🔄 Atualizar agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption("Atualização automática: 5 min")
    st.caption(f"Verificado em: {datetime.now().strftime('%d/%m %H:%M')}")

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar planilha: {e}")
    st.stop()

if df.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

df["Status"] = df.apply(status, axis=1)
zerados  = df[df["Estoque"] == 0]
criticos = df[df["Estoque"].between(1,2)]
baixos   = df[df["Estoque"].between(3,5)]
ok       = df[df["Estoque"] > 5]

st.title("📦 Dashboard de Estoque em Tempo Real")
st.markdown("---")
if not zerados.empty:
    st.error(f"🔴 **{len(zerados)} variação(ões) com ESTOQUE ZERADO**")
if not criticos.empty:
    st.warning(f"🟠 **{len(criticos)} variação(ões) com ESTOQUE CRÍTICO (1–2 un.)**")

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("📦 Total de itens",      f"{df['Estoque'].sum():,}".replace(",","."))
c2.metric("🏷️ Variações",           len(df))
c3.metric("🟢 OK (>5)",             len(ok))
c4.metric("🟡 Baixo (3–5)",         len(baixos))
c5.metric("🔴 Zerado / 🟠 Crítico", f"{len(zerados)} / {len(criticos)}")
st.markdown("---")

col_f1, col_f2, col_f3 = st.columns([2,1,1])
with col_f1:
    produtos = sorted(df["Produto"].unique())
    sel = st.multiselect("Filtrar produto(s):", produtos, default=produtos[:8] if len(produtos)>8 else produtos)
with col_f2:
    sel_st = st.selectbox("Status:", ["Todos","🟢 OK","🟡 Baixo","🟠 Crítico","🔴 Zerado"])
with col_f3:
    sel_tec = st.selectbox("Tecido:", ["Todos"] + list(CORES.keys()))

df_view = df[df["Produto"].isin(sel)] if sel else df.copy()
if sel_st  != "Todos": df_view = df_view[df_view["Status"] == sel_st]
if sel_tec != "Todos": df_view = df_view[df_view["Produto"].str.contains(sel_tec, na=False)]

st.subheader("📊 Estoque por Produto e Cor")
color_map = {"🔴 Zerado":"#e74c3c","🟠 Crítico":"#e67e22","🟡 Baixo":"#f1c40f","🟢 OK":"#2ecc71"}

if df_view.empty:
    st.info("Nenhum produto para exibir com os filtros selecionados.")
else:
    df_sorted = df_view.sort_values(["Produto","Estoque"])
    fig = px.bar(df_sorted, x="Estoque", y="Cor", orientation="h", color="Status",
                 color_discrete_map=color_map, text="Estoque", facet_row="Produto",
                 facet_row_spacing=0.03, labels={"Estoque":"Quantidade","Cor":""})
    fig.update_traces(textposition="outside")
    fig.update_yaxes(matches=None, showticklabels=True)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font_size=10))
    fig.update_layout(height=max(500, len(df_view)*32 + df_view["Produto"].nunique()*28),
                      showlegend=True, legend_title="Status",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=80))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("🔴 Zerados / 🟠 Críticos")
    urgentes = df[df["Status"].isin(["🔴 Zerado","🟠 Crítico"])].copy()
    if urgentes.empty: st.success("Nenhum produto zerado ou crítico!")
    else:
        st.dataframe(urgentes[["Produto","Cor","Estoque","Status","Data"]].rename(columns={"Data":"Últ. mov."}).sort_values(["Status","Produto"]), use_container_width=True, hide_index=True)
with col_b:
    st.subheader("🟡 Estoque Baixo (3–5 un.)")
    if baixos.empty: st.success("Nenhum produto com estoque baixo!")
    else:
        st.dataframe(baixos[["Produto","Cor","Estoque","Data"]].rename(columns={"Data":"Últ. mov."}).sort_values(["Produto","Estoque"]), use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("📋 Tabela Completa")
st.dataframe(df_view[["Produto","Cor","Estoque","Status","Data"]].rename(columns={"Data":"Últ. mov."}), use_container_width=True, hide_index=True)
st.caption(f"{len(df_view)} variação(ões) · {df_view['Produto'].nunique()} produto(s) · Fonte: Google Sheets")
