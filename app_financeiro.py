import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import io
import unicodedata
from supabase import create_client, Client
from fpdf import FPDF

# ==========================================
# 1. Configuração de Estilos e Layout
# ==========================================
st.set_page_config(page_title="Gestão Financeira", layout="wide")

def aplicar_estilos():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
        h1, h2, h3 { color: #1F2937 !important; }
        [data-testid="stMetric"] {
            background-color: #F3F4F6; border-radius: 10px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        [data-testid="stMetricValue"] { font-weight: 700 !important; color: #111827 !important; }
        </style>
    """, unsafe_allow_html=True)

aplicar_estilos()

# ==========================================
# 2. Conexão com Supabase (Nuvem)
# ==========================================
SUPABASE_URL = "https://ssksykacggaxmofjnfui.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNza3N5a2FjZ2dheG1vZmpuZnVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMzM5MjEsImV4cCI6MjEwMTYwOTkyMX0.qhPOSe665qdQRWsP6zlcI5hoR2e5m1SYLCuIJsDByAg"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def adicionar_transacao(tipo, categoria, descricao, valor, data_vencimento, status):
    data_str = str(data_vencimento)
    dados = {"tipo": tipo, "categoria": categoria, "descricao": descricao, "valor": float(valor), "data_vencimento": data_str, "status": status}
    supabase.table("transacoes").insert(dados).execute()

def atualizar_transacao(id_transacao, tipo, categoria, descricao, valor, data_vencimento, status):
    data_str = str(data_vencimento)
    dados = {"tipo": tipo, "categoria": categoria, "descricao": descricao, "valor": float(valor), "data_vencimento": data_str, "status": status}
    supabase.table("transacoes").update(dados).eq("id", id_transacao).execute()

def deletar_transacao(id_transacao):
    supabase.table("transacoes").delete().eq("id", id_transacao).execute()

def marcar_como_pago(id_transacao):
    supabase.table("transacoes").update({"status": "Pago"}).eq("id", id_transacao).execute()

def carregar_dados():
    resposta = supabase.table("transacoes").select("*").order("data_vencimento", desc=True).execute()
    if resposta.data:
        return pd.DataFrame(resposta.data)
    else:
        return pd.DataFrame(columns=["id", "tipo", "categoria", "descricao", "valor", "data_vencimento", "status"])

def remover_acentos(txt):
    if pd.isna(txt): return ""
    txt = str(txt)
    return unicodedata.normalize('NFKD', txt).encode('ASCII', 'ignore').decode('ASCII')

# ==========================================
# 3. Interface Principal
# ==========================================
st.title("💸 Gestão Financeira - Bem Caseiro")

menu = st.sidebar.selectbox("Navegação", ["Painel Geral", "Lançamentos", "Editar / Excluir", "Contas a Pagar (Alertas)", "Relatórios"])

df = carregar_dados()

# ------------------------------------------
# PAINEL GERAL
# ------------------------------------------
if menu == "Painel Geral":
    st.header("📊 Visão Geral do Fluxo de Caixa")
    if not df.empty:
        receitas = df[(df['tipo'] == 'Receita') & (df['status'] == 'Pago')]['valor'].sum()
        despesas = df[(df['tipo'] == 'Despesa') & (df['status'] == 'Pago')]['valor'].sum()
        saldo = receitas - despesas
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Receitas (Pagas) 🟢", f"R$ {receitas:.2f}")
        col2.metric("Despesas (Pagas) 🔴", f"R$ {despesas:.2f}")
        col3.metric("Saldo em Caixa 💰", f"R$ {saldo:.2f}")
        st.divider()
        
        df_despesas_pagas = df[(df['tipo'] == 'Despesa') & (df['status'] == 'Pago')]
        if not df_despesas_pagas.empty:
            st.subheader("Distribuição de Despesas")
            custo_por_categoria = df_despesas_pagas.groupby('categoria')['valor'].sum().reset_index()
            fig = px.pie(custo_por_categoria, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
            
        st.subheader("Histórico Recente")
        st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True, column_config={"valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")})
    else:
        st.info("Nenhuma transação registrada na nuvem.")

# ------------------------------------------
# LANÇAMENTOS
# ------------------------------------------
elif menu == "Lançamentos":
    st.header("📝 Novo Lançamento")
    tipo = st.selectbox("Tipo de Movimentação", ["Receita", "Despesa"])
    lista_categorias = ["Insumos", "Folha de Pagamento", "Impostos", "Manutenção", "Água/Luz/Internet", "Outros"] if tipo == "Despesa" else ["Vendas de Balcão", "Delivery", "Eventos", "Outros"]
    categoria = st.selectbox("Categoria", lista_categorias)
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", step=10.0)
    data_vencimento = st.date_input("Data de Vencimento/Recebimento")
    status = st.selectbox("Status", ["Pendente", "Pago"])
    
    if st.button("Salvar Lançamento", type="primary"):
        adicionar_transacao(tipo, categoria, descricao, valor, data_vencimento, status)
        st.success("✅ Lançamento registrado na nuvem com sucesso!")

# ------------------------------------------
# EDITAR / EXCLUIR
# ------------------------------------------
elif menu == "Editar / Excluir":
    st.header("✏️ Editar ou Excluir Lançamentos")
    if not df.empty:
        st.write("Filtre o período para localizar o lançamento:")
        df['data_vencimento_date'] = pd.to_datetime(df['data_vencimento']).dt.date
        col_filtro1, col_filtro2 = st.columns(2)
        data_inicio_edit = col_filtro1.date_input("Filtrar a partir de:", value=date.today().replace(day=1), key="edit_inicio")
        data_fim_edit = col_filtro2.date_input("Até:", value=date.today(), key="edit_fim")
        mask = (df['data_vencimento_date'] >= data_inicio_edit) & (df['data_vencimento_date'] <= data_fim_edit)
        df_filtrado_edicao = df.loc[mask]
        st.divider()
        
        if not df_filtrado_edicao.empty:
            opcoes = df_filtrado_edicao.apply(lambda row: f"{row['data_vencimento']} | {row['tipo']} - {row['descricao']} (R$ {row['valor']:.2f})", axis=1).tolist()
            indice_selecionado = st.selectbox("Selecione o lançamento que deseja alterar:", range(len(opcoes)), format_func=lambda x: opcoes[x])
            linha = df_filtrado_edicao.iloc[indice_selecionado]
            id_selecionado = int(linha['id'])
            
            st.subheader("Alterar Dados")
            with st.form("form_edicao"):
                novo_tipo = st.selectbox("Tipo", ["Receita", "Despesa"], index=0 if linha['tipo'] == "Receita" else 1)
                nova_categoria = st.text_input("Categoria", value=linha['categoria'])
                nova_descricao = st.text_input("Descrição", value=linha['descricao'])
                novo_valor = st.number_input("Valor (R$)", min_value=0.01, value=float(linha['valor']), format="%.2f")
                nova_data = st.date_input("Data", value=pd.to_datetime(linha['data_vencimento']).date())
                novo_status = st.selectbox("Status", ["Pendente", "Pago"], index=0 if linha['status'] == "Pendente" else 1)
                
                if st.form_submit_button("💾 Salvar Alterações"):
                    atualizar_transacao(id_selecionado, novo_tipo, nova_categoria, nova_descricao, novo_valor, nova_data, novo_status)
                    st.success("Registro atualizado na nuvem!")
                    st.rerun()
            st.divider()
            st.subheader("Zona de Perigo")
            with st.popover("🗑️ Excluir este lançamento"):
                st.warning("Esta ação não pode ser desfeita. Deseja mesmo excluir?")
                if st.button("Sim, excluir permanentemente", type="primary"):
                    deletar_transacao(id_selecionado)
                    st.rerun()
        else:
            st.warning("Nenhum lançamento encontrado no período selecionado.")
    else:
        st.info("Nenhuma transação cadastrada no sistema.")

# ------------------------------------------
# CONTAS A PAGAR (ALERTAS)
# ------------------------------------------
elif menu == "Contas a Pagar (Alertas)":
    st.header("🔔 Alertas de Vencimento")
    if not df.empty:
        pendentes = df[(df['tipo'] == 'Despesa') & (df['status'] == 'Pendente')].copy()
        if not pendentes.empty:
            pendentes['data_vencimento_date'] = pd.to_datetime(pendentes['data_vencimento']).dt.date
            hoje = date.today()
            limite_alerta = hoje + timedelta(days=3)
            contas_criticas = pendentes[pendentes['data_vencimento_date'] <= limite_alerta].sort_values(by="data_vencimento_date")
            contas_futuras = pendentes[pendentes['data_vencimento_date'] > limite_alerta].sort_values(by="data_vencimento_date")
            
            st.subheader("🔴 Vencendo Hoje ou Atrasadas")
            if not contas_criticas.empty:
                st.error(f"Atenção: {len(contas_criticas)} conta(s) crítica(s)!")
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                col1.write("**Categoria**"); col2.write("**Descrição**"); col3.write("**Valor**"); col4.write("**Vencimento**"); col5.write("**Ação**")
                
                for index, row in contas_criticas.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                    col1.write(row['categoria']); col2.write(row['descricao']); col3.write(f"R$ {row['valor']:.2f}"); col4.write(row['data_vencimento'])
                    with col5:
                        with st.popover("✔️ Dar Baixa"):
                            st.write(f"Confirmar pagamento de R$ {row['valor']:.2f}?")
                            if st.button("Confirmar", key=f"pagar_{row['id']}", type="primary"):
                                marcar_como_pago(row['id'])
                                st.rerun()
            else:
                st.success("Tudo em dia por aqui! Nenhuma conta vencendo agora.")
            st.divider()
            st.subheader("🟡 Próximos Vencimentos")
            if not contas_futuras.empty:
                st.dataframe(contas_futuras[['categoria', 'descricao', 'valor', 'data_vencimento']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma conta programada para os próximos dias.")
        else:
            st.success("Parabéns! Nenhuma conta pendente no sistema.")
    else:
        st.info("Não há transações registradas.")

# ------------------------------------------
# RELATÓRIOS
# ------------------------------------------
elif menu == "Relatórios":
    st.header("📄 Exportar Relatórios")
    if not df.empty:
        df['data_vencimento_date'] = pd.to_datetime(df['data_vencimento']).dt.date
        col1, col2 = st.columns(2)
        data_inicio = col1.date_input("Data de Início", value=date.today().replace(day=1))
        data_fim = col2.date_input("Data Final", value=date.today())
        mask = (df['data_vencimento_date'] >= data_inicio) & (df['data_vencimento_date'] <= data_fim)
        df_filtrado = df.loc[mask].drop(columns=['data_vencimento_date', 'id'])
        st.divider()
        st.subheader(f"Pré-visualização ({len(df_filtrado)} registros encontrados)")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        
        if not df_filtrado.empty:
            col_btn1, col_btn2 = st.columns(2)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name='Bem Caseiro - Relatório')
            col_btn1.download_button(label="📊 Baixar Planilha Excel", data=buffer.getvalue(), file_name=f"Relatorio_{data_inicio}_a_{data_fim}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, txt="Relatório Financeiro - Bem Caseiro", ln=True, align='C')
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(190, 10, txt=f"Período: {data_inicio} até {data_fim}", ln=True, align='C')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 9)
            col_widths = [22, 22, 50, 40, 25, 25] 
            headers = ['Data', 'Tipo', 'Descrição', 'Categoria', 'Valor (R$)', 'Status']
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, remover_acentos(header), border=1, align='C')
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
            for _, row in df_filtrado.iterrows():
                pdf.cell(col_widths[0], 8, str(row['data_vencimento']), border=1, align='C')
                pdf.cell(col_widths[1], 8, remover_acentos(row['tipo']), border=1, align='C')
                pdf.cell(col_widths[2], 8, remover_acentos(row['descricao'])[:25], border=1)
                pdf.cell(col_widths[3], 8, remover_acentos(row['categoria'])[:20], border=1)
                pdf.cell(col_widths[4], 8, f"{row['valor']:.2f}", border=1, align='C')
                pdf.cell(col_widths[5], 8, remover_acentos(row['status']), border=1, align='C')
                pdf.ln()
            
            pdf_bytes = pdf.output(dest="S").encode("latin-1")
            col_btn2.download_button(label="📄 Baixar Documento PDF", data=pdf_bytes, file_name=f"Relatorio_{data_inicio}_a_{data_fim}.pdf", mime="application/pdf", type="primary")