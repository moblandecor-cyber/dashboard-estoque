import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Dashboard de Estoque",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

SHEET_ID = "19lLWSJBYvuTzQn58mjD9P1i6pgx8M8T8Mputx5dceRY"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet=Estoque%20atual"

@st.cache_data(ttl=300)
def load_data():
    raw = pd.read_csv(URL, header=None, dtype=str)

    # Filtra apenas linhas com produto preenchido (ignora cabeçalho e vazios)
    df = raw[
        raw[1].notna() &
        (raw[1].str.strip() != "") &
        (raw[1].str.strip() != "PRODUTO")
    ][[0, 1, 2, 5]].copy()

    df.columns = ["Data", "Produto", "Cor", "Estoque"]
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df["Estoque"] = pd.to_numeric(df["Estoque"].str.replace(",", "."), errors="coerce")
    df = df.dropna(subset=["Produto", "Estoque"])
    df["Produto"] = df["Produto"].str.strip()
    df["Cor"] = df["Cor"].fillna("").str.strip()

    # Estoque atual = último registro de cada Produto + Cor
    atual = (
        df.sort_values("Data", na_position="first")
        .groupby(["Produto", "Cor"], as_index=False)
        .last()
    )
    atual["Estoque"] = atual["Estoque"].astype(int)
    atual["Nome"] = atual.apply(
        lambda r: f"{r['Produto']} — {r['Cor']}" if r["Cor"] else r["Produto"], axis=1
    )
    return atual.sort_values(["Produto", "Cor"]).reset_index(drop=True)


def status(row):
    if row["Estoque"] == 0:
        return "🔴 Zerado"
    elif row["Estoque"] <= 2:
        return "🟠 Crítico"
    elif row["Estoque"] <= 5:
        return "🟡 Baixo"
    else:
        return "🟢 OK"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📦 Estoque")
    st.markdown("---")
    if st.button("🔄 Atualizar agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption("Atualização automática: 5 min")
    st.caption(f"Verificado em: {datetime.now().strftime('%d/%m %H:%M')}")

# ── Carregar dados ─────────────────────────────────────────────────────────────
try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Erro ao carregar planilha: {e}")
    st.stop()

if df.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

df["Status"] = df.apply(status, axis=1)

zerados  = df[df["Estoque"] == 0]
criticos = df[df["Estoque"].between(1, 2)]
baixos   = df[df["Estoque"].between(3, 5)]
ok       = df[df["Estoque"] > 5]

# ── Alertas ───────────────────────────────────────────────────────────────────
st.title("📦 Dashboard de Estoque em Tempo Real")
st.markdown("---")

if not zerados.empty:
    st.error("🔴 **ESTOQUE ZERADO:** " + " · ".join(zerados["Nome"].tolist()))
if not criticos.empty:
    st.warning("🟠 **ESTOQUE CRÍTICO (1–2 un.):** " + " · ".join(criticos["Nome"].tolist()))

# ── Métricas ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📦 Total de itens", f"{df['Estoque'].sum():,}".replace(",", "."))
c2.metric("🏷️ Combinações", len(df))
c3.metric("🟢 OK (>5)", len(ok))
c4.metric("🟡 Baixo (3–5)", len(baixos))
c5.metric("🔴 Zerado / 🟠 Crítico", f"{len(zerados)} / {len(criticos)}")

st.markdown("---")

# ── Filtros ───────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    produtos = sorted(df["Produto"].unique())
    sel_produtos = st.multiselect("Filtrar produto(s):", produtos, default=produtos[:10] if len(produtos) > 10 else produtos)
with col_f2:
    sel_status = st.selectbox("Filtrar por status:", ["Todos", "🟢 OK", "🟡 Baixo", "🟠 Crítico", "🔴 Zerado"])

df_view = df[df["Produto"].isin(sel_produtos)] if sel_produtos else df
if sel_status != "Todos":
    df_view = df_view[df_view["Status"] == sel_status]

# ── Gráfico ───────────────────────────────────────────────────────────────────
st.subheader("📊 Estoque por Produto e Cor")

color_map = {"🔴 Zerado": "#e74c3c", "🟠 Crítico": "#e67e22", "🟡 Baixo": "#f1c40f", "🟢 OK": "#2ecc71"}

if df_view.empty:
    st.info("Nenhum produto para exibir com os filtros selecionados.")
else:
    df_sorted = df_view.sort_values(["Produto", "Estoque"])
    fig = px.bar(
        df_sorted,
        x="Estoque",
        y="Nome",
        orientation="h",
        color="Status",
        color_discrete_map=color_map,
        text="Estoque",
        facet_row="Produto",
        facet_row_spacing=0.04,
        labels={"Estoque": "Quantidade", "Nome": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_yaxes(matches=None, showticklabels=True)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font_size=11))
    fig.update_layout(
        height=max(500, len(df_view) * 38 + len(sel_produtos) * 25),
        showlegend=True,
        legend_title="Status",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=80),
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Produtos zerados / críticos ───────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🔴 Zerados / 🟠 Críticos")
    urgentes = df[df["Status"].isin(["🔴 Zerado", "🟠 Crítico"])].copy()
    if urgentes.empty:
        st.success("Nenhum produto zerado ou crítico!")
    else:
        st.dataframe(
            urgentes[["Produto", "Cor", "Estoque", "Status", "Data"]].rename(
                columns={"Data": "Últ. mov."}
            ).sort_values("Estoque"),
            use_container_width=True, hide_index=True,
        )

with col_b:
    st.subheader("🟡 Estoque Baixo (3–5 un.)")
    if baixos.empty:
        st.success("Nenhum produto com estoque baixo!")
    else:
        st.dataframe(
            baixos[["Produto", "Cor", "Estoque", "Data"]].rename(
                columns={"Data": "Últ. mov."}
            ).sort_values("Estoque"),
            use_container_width=True, hide_index=True,
        )

st.markdown("---")

# ── Tabela completa ────────────────────────────────────────────────────────────
st.subheader("📋 Tabela Completa")
st.dataframe(
    df_view[["Produto", "Cor", "Estoque", "Status", "Data"]].rename(
        columns={"Data": "Últ. mov."}
    ),
    use_container_width=True, hide_index=True,
)
st.caption(f"{len(df_view)} variação(ões) · {len(df_view['Produto'].unique())} produto(s) · Fonte: Google Sheets")
