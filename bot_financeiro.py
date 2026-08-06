import telebot
from telebot import types
from supabase import create_client, Client
from datetime import date
import os
import threading
from flask import Flask

# ==========================================
# 1. Servidor "Fantasma" (Mantém o bot online)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "O Bot Financeiro está rodando 24/7 com botões interativos!"

def iniciar_servidor():
    porta = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=porta)

threading.Thread(target=iniciar_servidor).start()

# ==========================================
# 2. Configurações e Chaves
# ==========================================
TOKEN = '8937026927:AAGlMnT2iQzJjBqWC73b9JoUqfd-xDqbbIU'  # <--- Coloque a chave do BotFather aqui!
bot = telebot.TeleBot(TOKEN)

SUPABASE_URL = "https://ssksykacggaxmofjnfui.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNza3N5a2FjZ2dheG1vZmpuZnVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMzM5MjEsImV4cCI6MjEwMTYwOTkyMX0.qhPOSe665qdQRWsP6zlcI5hoR2e5m1SYLCuIJsDByAg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 3. Criação dos Menus (Botões)
# ==========================================
def menu_principal():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_despesa = types.KeyboardButton('💸 Nova Despesa')
    btn_pendentes = types.KeyboardButton('📋 Ver Pendentes')
    markup.add(btn_despesa, btn_pendentes)
    return markup

def menu_categorias():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    markup.add("Insumos", "Folha de Pagamento", "Impostos", "Manutenção", "Água/Luz/Internet", "Outros", "❌ Cancelar")
    return markup

# ==========================================
# 4. Comandos e Fluxos do Bot
# ==========================================
@bot.message_handler(commands=['start', 'ajuda'])
def enviar_ajuda(message):
    bot.send_message(
        message.chat.id, 
        "Bem-vindo ao assistente financeiro! 🍽️\nUse os botões abaixo para navegar:",
        reply_markup=menu_principal()
    )

# --- FLUXO: NOVA DESPESA ---
@bot.message_handler(func=lambda message: message.text == '💸 Nova Despesa')
def iniciar_despesa(message):
    msg = bot.reply_to(message, "Escolha a CATEGORIA da despesa:", reply_markup=menu_categorias())
    bot.register_next_step_handler(msg, pegar_categoria)

def pegar_categoria(message):
    if message.text == '❌ Cancelar':
        bot.send_message(message.chat.id, "Lançamento cancelado.", reply_markup=menu_principal())
        return
        
    categoria = message.text
    msg = bot.reply_to(message, f"Categoria: *{categoria}*\n\nAgora, digite a DESCRIÇÃO (ex: Fornecedor de Hortifruti):", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, pegar_descricao, categoria)

def pegar_descricao(message, categoria):
    descricao = message.text
    msg = bot.reply_to(message, f"Descrição: *{descricao}*\n\nPor fim, digite o VALOR (ex: 150.50):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, salvar_despesa, categoria, descricao)

def salvar_despesa(message, categoria, descricao):
    try:
        valor = float(message.text.replace(',', '.'))
        data_hoje = date.today().isoformat()
        
        dados = {
            "tipo": "Despesa",
            "categoria": categoria,
            "descricao": descricao,
            "valor": valor,
            "data_vencimento": data_hoje,
            "status": "Pendente"
        }
        
        supabase.table("transacoes").insert(dados).execute()
        
        resumo = f"✅ *Despesa Salva!*\n\n📁 {categoria}\n📝 {descricao}\n💰 R$ {valor:.2f}"
        bot.send_message(message.chat.id, resumo, parse_mode="Markdown", reply_markup=menu_principal())
        
    except ValueError:
        msg = bot.reply_to(message, "⚠️ Valor inválido! Digite apenas números (ex: 150.50).\nTente digitar o valor novamente:")
        bot.register_next_step_handler(msg, salvar_despesa, categoria, descricao)
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Erro ao salvar na nuvem.", reply_markup=menu_principal())

# --- FLUXO: VER PENDENTES E DAR BAIXA ---
@bot.message_handler(func=lambda message: message.text == '📋 Ver Pendentes')
def listar_pendentes(message):
    try:
        resposta = supabase.table("transacoes").select("*").eq("tipo", "Despesa").eq("status", "Pendente").order("data_vencimento").execute()
        contas = resposta.data
        
        if not contas:
            bot.send_message(message.chat.id, "🎉 Nenhuma conta pendente!", reply_markup=menu_principal())
            return
            
        bot.send_message(message.chat.id, "🔴 *Contas Pendentes:*", parse_mode='Markdown')
        
        for conta in contas:
            texto_conta = f"📝 {conta['descricao']}\n📁 {conta['categoria']}\n💰 R$ {conta['valor']:.2f}\n📅 Vence: {conta['data_vencimento']}"
            
            markup_inline = types.InlineKeyboardMarkup()
            botao_pagar = types.InlineKeyboardButton("✔️ Dar Baixa", callback_data=f"pagar_{conta['id']}")
            markup_inline.add(botao_pagar)
            
            bot.send_message(message.chat.id, texto_conta, reply_markup=markup_inline)
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Erro ao buscar contas.", reply_markup=menu_principal())

# --- AÇÃO DO BOTÃO "DAR BAIXA" ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('pagar_'))
def processar_pagamento(call):
    id_conta = call.data.split('_')[1]
    try:
        supabase.table("transacoes").update({"status": "Pago"}).eq("id", id_conta).execute()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=f"✔️ {call.message.text}\n\n*(PAGO)*",
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "Erro ao dar baixa na conta.")

print("Bot iniciado...")
bot.infinity_polling()