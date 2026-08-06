import telebot
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
    return "O Bot Financeiro está rodando 24/7!"

def iniciar_servidor():
    porta = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=porta)

# Roda o servidor web em segundo plano
threading.Thread(target=iniciar_servidor).start()

# ==========================================
# 2. Configurações e Chaves
# ==========================================
TOKEN = '8937026927:AAGlMnT2iQzJjBqWC73b9JoUqfd-xDqbbIU'
bot = telebot.TeleBot(TOKEN)

SUPABASE_URL = "https://ssksykacggaxmofjnfui.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNza3N5a2FjZ2dheG1vZmpuZnVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwMzM5MjEsImV4cCI6MjEwMTYwOTkyMX0.qhPOSe665qdQRWsP6zlcI5hoR2e5m1SYLCuIJsDByAg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 3. Comandos do Bot
# ==========================================
@bot.message_handler(commands=['start', 'ajuda'])
def enviar_ajuda(message):
    texto = """
    Bem-vindo ao assistente financeiro! 🍽️
    
    1️⃣ Registrar uma despesa para HOJE:
    /despesa Categoria, Descrição, Valor
    Ex: /despesa Insumos, Hortifruti, 150.50
    
    2️⃣ Ver as contas pendentes:
    /pendentes
    
    3️⃣ Dar baixa em uma conta:
    /pagar ID
    Ex: /pagar 15
    """
    bot.reply_to(message, texto)

@bot.message_handler(commands=['despesa'])
def registrar_despesa(message):
    try:
        texto = message.text.replace('/despesa ', '')
        partes = [p.strip() for p in texto.split(',')]
        
        if len(partes) != 3:
            bot.reply_to(message, "⚠️ Formato incorreto. Use: /despesa Categoria, Descrição, Valor")
            return
            
        categoria = partes[0]
        descricao = partes[1]
        valor = float(partes[2].replace(',', '.'))
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
        bot.reply_to(message, f"✅ Despesa salva na nuvem!\n\nCategoria: {categoria}\nDescrição: {descricao}\nValor: R$ {valor:.2f}")
    
    except Exception as e:
        bot.reply_to(message, "❌ Erro ao registrar. Verifique se digitou o valor corretamente.")

@bot.message_handler(commands=['pendentes'])
def listar_pendentes(message):
    try:
        resposta = supabase.table("transacoes").select("id, descricao, valor, data_vencimento").eq("tipo", "Despesa").eq("status", "Pendente").order("data_vencimento").execute()
        contas = resposta.data
        
        if not contas:
            bot.reply_to(message, "🎉 Nenhuma conta pendente!")
            return
            
        texto_resposta = "🔴 *Contas Pendentes:*\n\n"
        for conta in contas:
            texto_resposta += f"ID: {conta['id']} | {conta['descricao']}\nValor: R$ {conta['valor']:.2f} | Vence: {conta['data_vencimento']}\n"
            texto_resposta += "--------------------\n"
            
        texto_resposta += "\nPara dar baixa, digite: /pagar ID"
        bot.reply_to(message, texto_resposta, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao buscar contas: {str(e)}")

@bot.message_handler(commands=['pagar'])
def dar_baixa(message):
    try:
        id_conta = message.text.replace('/pagar ', '').strip()
        
        if not id_conta.isdigit():
            bot.reply_to(message, "⚠️ Informe apenas o número. Ex: /pagar 15")
            return
            
        resposta = supabase.table("transacoes").update({"status": "Pago"}).eq("id", id_conta).execute()
        
        if resposta.data:
            bot.reply_to(message, f"✔️ Conta ID {id_conta} marcada como Paga na nuvem!")
        else:
            bot.reply_to(message, f"⚠️ Nenhuma conta encontrada com o ID {id_conta}.")
            
    except Exception as e:
        bot.reply_to(message, "❌ Erro ao processar o pagamento.")

print("Bot iniciado...")
bot.infinity_polling()