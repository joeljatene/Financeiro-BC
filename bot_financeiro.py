import telebot
import sqlite3
from datetime import date

# COLOQUE O SEU TOKEN AQUI (Mantenha as aspas)
TOKEN = '8937026927:AAGlMnT2iQzJjBqWC73b9JoUqfd-xDqbbIU'
bot = telebot.TeleBot(TOKEN)

# Função para conectar ao banco do restaurante
def conectar_banco():
    return sqlite3.connect('restaurante_financas.db')

@bot.message_handler(commands=['start', 'ajuda'])
def enviar_ajuda(message):
    texto = """
    Bem-vindo ao assistente financeiro do restaurante! 🍽️
    
    Aqui estão os comandos que você pode usar:
    
    1️⃣ Registrar uma despesa para HOJE:
    /despesa Categoria, Descrição, Valor
    Ex: /despesa Insumos, Frutas e verduras, 150.50
    
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
        # Pega o texto removendo o comando '/despesa '
        texto = message.text.replace('/despesa ', '')
        partes = [p.strip() for p in texto.split(',')]
        
        if len(partes) != 3:
            bot.reply_to(message, "⚠️ Formato incorreto. Use: /despesa Categoria, Descrição, Valor\nEx: /despesa Insumos, Gás, 120.00")
            return
            
        categoria = partes[0]
        descricao = partes[1]
        valor = float(partes[2].replace(',', '.')) # Aceita tanto ponto quanto vírgula no valor
        data_hoje = date.today().strftime('%Y-%m-%d')
        
        conn = conectar_banco()
        c = conn.cursor()
        c.execute('''
            INSERT INTO transacoes (tipo, categoria, descricao, valor, data_vencimento, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Despesa", categoria, descricao, valor, data_hoje, "Pendente"))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Despesa registrada com sucesso!\n\nCategoria: {categoria}\nDescrição: {descricao}\nValor: R$ {valor:.2f}\nStatus: Pendente (Vencimento Hoje)")
    
    except Exception as e:
        bot.reply_to(message, "❌ Erro ao registrar. Verifique se digitou o valor corretamente.")

@bot.message_handler(commands=['pendentes'])
def listar_pendentes(message):
    try:
        conn = conectar_banco()
        c = conn.cursor()
        c.execute("SELECT id, descricao, valor, data_vencimento FROM transacoes WHERE tipo='Despesa' AND status='Pendente' ORDER BY data_vencimento ASC")
        contas = c.fetchall()
        conn.close()
        
        if not contas:
            bot.reply_to(message, "🎉 Nenhuma conta pendente!")
            return
            
        texto_resposta = "🔴 *Contas Pendentes:*\n\n"
        for conta in contas:
            # conta = (id, descricao, valor, data_vencimento)
            texto_resposta += f"ID: {conta[0]} | {conta[1]}\nValor: R$ {conta[2]:.2f} | Vence: {conta[3]}\n"
            texto_resposta += "--------------------\n"
            
        texto_resposta += "\nPara dar baixa, digite: /pagar ID"
        bot.reply_to(message, texto_resposta, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, "❌ Erro ao buscar contas.")

@bot.message_handler(commands=['pagar'])
def dar_baixa(message):
    try:
        id_conta = message.text.replace('/pagar ', '').strip()
        
        if not id_conta.isdigit():
            bot.reply_to(message, "⚠️ Por favor, informe apenas o número do ID. Ex: /pagar 15")
            return
            
        conn = conectar_banco()
        c = conn.cursor()
        c.execute("UPDATE transacoes SET status='Pago' WHERE id=?", (id_conta,))
        
        if c.rowcount > 0:
            conn.commit()
            bot.reply_to(message, f"✔️ Conta ID {id_conta} marcada como Paga com sucesso!")
        else:
            bot.reply_to(message, f"⚠️ Nenhuma conta encontrada com o ID {id_conta}.")
            
        conn.close()
        
    except Exception as e:
        bot.reply_to(message, "❌ Erro ao processar o pagamento.")

# Mantém o bot rodando
print("Bot iniciado! Pressione Ctrl+C para parar.")
bot.infinity_polling()