import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client
import os
from datetime import datetime
from flask import Flask
import threading

# ==========================================
# 1. Configurações (Substitua por suas chaves)
# ==========================================
TOKEN = '8937026927:AAGlMnT2iQzJjBqWC73b9JoUqfd-xDqbbIU'
SUPABASE_URL = "https://ssksykacggaxmofjnfui.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNza3N5a2FjZ2dheG1vZmpuZnVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMzM5MjEsImV4cCI6MjEwMTYwOTkyMX0.qhPOSe665qdQRWsP6zlcI5hoR2e5m1SYLCuIJsDByAg"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Dicionário para guardar as respostas do usuário temporariamente
dados_temp = {}

# ==========================================
# 2. Servidor Web (Garante que o Render não desligue o bot)
# ==========================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot Financeiro - Bem Caseiro está online!"

def rodar_servidor():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 3. Menus e Interface do Telegram
# ==========================================
def menu_principal():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🔴 Nova Despesa"),
        KeyboardButton("🟢 Nova Receita"),
        KeyboardButton("🔔 Ver Pendentes"),
        KeyboardButton("📊 Fluxo de Caixa"),
        KeyboardButton("🗑️ Excluir Lançamento")
    )
    return markup

@bot.message_handler(commands=['start'])
def enviar_boas_vindas(message):
    bot.reply_to(message, "Olá! Sou o assistente financeiro do Bem Caseiro. O que deseja fazer?", reply_markup=menu_principal())

# ==========================================
# 4. Inserir Receitas e Despesas
# ==========================================
@bot.message_handler(func=lambda message: message.text in ["🔴 Nova Despesa", "🟢 Nova Receita"])
def iniciar_lancamento(message):
    tipo = "Despesa" if message.text == "🔴 Nova Despesa" else "Receita"
    dados_temp[message.chat.id] = {'tipo': tipo}
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    if tipo == "Despesa":
        categorias = ["Insumos", "Folha de Pagamento", "Impostos", "Manutenção", "Água/Luz/Internet", "Outros"]
    else:
        categorias = ["Vendas de Balcão", "Delivery", "Eventos", "Outros"]
        
    for cat in categorias:
        markup.add(KeyboardButton(cat))
        
    msg = bot.send_message(message.chat.id, f"Qual a categoria da {tipo}?", reply_markup=markup)
    bot.register_next_step_handler(msg, pegar_categoria)

def pegar_categoria(message):
    dados_temp[message.chat.id]['categoria'] = message.text
    msg = bot.send_message(message.chat.id, "Digite uma breve descrição:")
    bot.register_next_step_handler(msg, pegar_descricao)

def pegar_descricao(message):
    dados_temp[message.chat.id]['descricao'] = message.text
    msg = bot.send_message(message.chat.id, "Digite o valor (Ex: 150.50):")
    bot.register_next_step_handler(msg, pegar_valor)

def pegar_valor(message):
    try:
        valor = float(message.text.replace(",", "."))
        dados_temp[message.chat.id]['valor'] = valor
        msg = bot.send_message(message.chat.id, "Digite a data (DD/MM/AAAA):")
        bot.register_next_step_handler(msg, pegar_data)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Formato inválido. Digite apenas números, como 150.50:")
        bot.register_next_step_handler(msg, pegar_valor)

def pegar_data(message):
    try:
        data_formatada = datetime.strptime(message.text, "%d/%m/%Y").strftime("%Y-%m-%d")
        dados_temp[message.chat.id]['data_vencimento'] = data_formatada
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("Pago"), KeyboardButton("Pendente"))
        msg = bot.send_message(message.chat.id, "Qual o status deste lançamento?", reply_markup=markup)
        bot.register_next_step_handler(msg, finalizar_lancamento)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Data inválida. Tente no formato DD/MM/AAAA (ex: 25/12/2026):")
        bot.register_next_step_handler(msg, pegar_data)

def finalizar_lancamento(message):
    dados = dados_temp[message.chat.id]
    dados['status'] = message.text
    
    try:
        supabase.table("transacoes").insert(dados).execute()
        bot.send_message(message.chat.id, f"✅ {dados['tipo']} registrada com sucesso!", reply_markup=menu_principal())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro na nuvem: {str(e)}", reply_markup=menu_principal())

# ==========================================
# 5. Ver Pendentes e Dar Baixa (Inline Buttons)
# ==========================================
@bot.message_handler(func=lambda message: message.text == "🔔 Ver Pendentes")
def listar_pendentes(message):
    try:
        response = supabase.table("transacoes").select("*").eq("tipo", "Despesa").eq("status", "Pendente").order("data_vencimento").execute()
        pendentes = response.data
        
        if pendentes:
            bot.send_message(message.chat.id, "🔔 *Contas a Pagar (Pendentes):*", parse_mode="Markdown")
            for p in pendentes:
                texto = f"📅 {p['data_vencimento']} | 📝 {p['descricao']}\n💰 R$ {p['valor']:.2f}"
                
                # Cria um botão flutuante para cada conta
                markup_inline = InlineKeyboardMarkup()
                botao_baixa = InlineKeyboardButton("✔️ Dar Baixa", callback_data=f"baixa_{p['id']}")
                markup_inline.add(botao_baixa)
                
                bot.send_message(message.chat.id, texto, reply_markup=markup_inline)
            
            # Envia o menu principal de volta para o usuário não ficar preso
            bot.send_message(message.chat.id, "Selecione uma ação no botão acima ou no menu abaixo:", reply_markup=menu_principal())
        else:
            bot.send_message(message.chat.id, "Tudo em dia! Nenhuma conta pendente. 🎉", reply_markup=menu_principal())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro: {str(e)}", reply_markup=menu_principal())

# Ação de responder ao clique no botão "Dar Baixa"
@bot.callback_query_handler(func=lambda call: call.data.startswith('baixa_'))
def processar_baixa(call):
    id_transacao = int(call.data.split('_')[1])
    try:
        # Atualiza o status para "Pago" no Supabase
        supabase.table("transacoes").update({"status": "Pago"}).eq("id", id_transacao).execute()
        
        # Edita a mensagem original para avisar que foi pago
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=f"~~{call.message.text}~~\n\n✅ *PAGO E BAIXADO NA NUVEM!*", 
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.answer_callback_query(call.id, f"Erro ao dar baixa: {str(e)}")

# ==========================================
# 6. Fluxo de Caixa
# ==========================================
@bot.message_handler(func=lambda message: message.text == "📊 Fluxo de Caixa")
def exibir_fluxo_caixa(message):
    try:
        # Busca todas as receitas pagas
        res_receitas = supabase.table("transacoes").select("valor").eq("tipo", "Receita").eq("status", "Pago").execute()
        total_receitas = sum(item['valor'] for item in res_receitas.data) if res_receitas.data else 0.0

        # Busca todas as despesas pagas
        res_despesas = supabase.table("transacoes").select("valor").eq("tipo", "Despesa").eq("status", "Pago").execute()
        total_despesas = sum(item['valor'] for item in res_despesas.data) if res_despesas.data else 0.0
        
        saldo = total_receitas - total_despesas
        
        texto = "📊 *Resumo do Fluxo de Caixa (Lançamentos Pagos)*\n\n"
        texto += f"🟢 *Receitas:* R$ {total_receitas:.2f}\n"
        texto += f"🔴 *Despesas:* R$ {total_despesas:.2f}\n"
        texto += "------------------------\n"
        texto += f"💰 *Saldo em Caixa: R$ {saldo:.2f}*"
        
        bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=menu_principal())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao calcular fluxo: {str(e)}", reply_markup=menu_principal())

# ==========================================
# 7. Excluir Lançamentos
# ==========================================
@bot.message_handler(func=lambda message: message.text == "🗑️ Excluir Lançamento")
def iniciar_exclusao(message):
    try:
        response = supabase.table("transacoes").select("*").order("id", desc=True).limit(10).execute()
        registros = response.data
        
        if not registros:
            bot.send_message(message.chat.id, "Não há lançamentos recentes no sistema.", reply_markup=menu_principal())
            return
            
        texto = "Aqui estão os 10 lançamentos mais recentes:\n\n"
        for r in registros:
            simbolo = "🔴" if r['tipo'] == "Despesa" else "🟢"
            texto += f"ID: {r['id']} | {simbolo} {r['descricao']} - R$ {r['valor']}\n"
            
        texto += "\n➡️ Digite apenas o **NÚMERO DO ID** que você deseja excluir (ou '0' para cancelar):"
        msg = bot.send_message(message.chat.id, texto)
        bot.register_next_step_handler(msg, processar_exclusao)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao buscar registros: {str(e)}", reply_markup=menu_principal())

def processar_exclusao(message):
    if message.text.strip() == "0":
        bot.send_message(message.chat.id, "Ação cancelada.", reply_markup=menu_principal())
        return
        
    try:
        id_deletar = int(message.text.strip())
        supabase.table("transacoes").delete().eq("id", id_deletar).execute()
        bot.send_message(message.chat.id, f"✅ Lançamento excluído com sucesso!", reply_markup=menu_principal())
    except ValueError:
        bot.send_message(message.chat.id, "Você precisa digitar um número válido.", reply_markup=menu_principal())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Erro ao excluir: {str(e)}", reply_markup=menu_principal())

# Inicialização conjunta (Web + Bot)
if __name__ == "__main__":
    threading.Thread(target=rodar_servidor).start()
    bot.polling(none_stop=True)