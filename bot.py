import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados para o ConversationHandler
ESCOLHENDO, REGISTRANDO = range(2)

# Dicionário para armazenar os treinos (em produção, use um banco de dados)
treinos_usuarios = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o bot e mostra as opções disponíveis."""
    user = update.effective_user
    await update.message.reply_text(
        f"Olá, {user.first_name}! Bem-vindo ao Bot de Registro de Treinos.\n\n"
        "Comandos disponíveis:\n"
        "/registrar - Registrar um novo treino\n"
        "/historico - Ver histórico de treinos\n"
        "/cancelar - Cancelar operação atual"
    )
    return ESCOLHENDO

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o processo de registro de treino."""
    await update.message.reply_text(
        "Vamos registrar seu treino! Por favor, descreva seu treino no formato:\n\n"
        "Exercício: Séries x Repetições x Peso\n\n"
        "Exemplo:\n"
        "Supino: 3x12x50kg\n"
        "Agachamento: 4x10x70kg\n"
        "Rosca Direta: 3x15x15kg\n\n"
        "Digite /finalizar quando terminar ou /cancelar para cancelar."
    )
    
    # Inicializa uma lista vazia para o treino atual do usuário
    user_id = update.effective_user.id
    if user_id not in treinos_usuarios:
        treinos_usuarios[user_id] = []
    
    context.user_data['treino_atual'] = []
    return REGISTRANDO

async def receber_exercicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe os exercícios do treino."""
    texto = update.message.text
    
    if texto == '/finalizar':
        # Finaliza o registro do treino
        user_id = update.effective_user.id
        data_atual = datetime.now().strftime("%d/%m/%Y")
        
        treino = {
            'data': data_atual,
            'exercicios': context.user_data['treino_atual']
        }
        
        treinos_usuarios[user_id].append(treino)
        
        await update.message.reply_text(
            f"Treino registrado com sucesso em {data_atual}!\n"
            "Use /historico para ver seus treinos."
        )
        return ESCOLHENDO
    
    # Adiciona o exercício à lista do treino atual
    context.user_data['treino_atual'].append(texto)
    await update.message.reply_text(
        f"Exercício registrado: {texto}\n"
        "Continue adicionando exercícios ou digite /finalizar quando terminar."
    )
    return REGISTRANDO

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra o histórico de treinos do usuário."""
    user_id = update.effective_user.id
    
    if user_id not in treinos_usuarios or not treinos_usuarios[user_id]:
        await update.message.reply_text("Você ainda não registrou nenhum treino.")
        return ESCOLHENDO
    
    resposta = "Seu histórico de treinos:\n\n"
    
    for i, treino in enumerate(treinos_usuarios[user_id], 1):
        resposta += f"Treino {i} - {treino['data']}:\n"
        for exercicio in treino['exercicios']:
            resposta += f"- {exercicio}\n"
        resposta += "\n"
    
    await update.message.reply_text(resposta)
    return ESCOLHENDO

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual."""
    await update.message.reply_text(
        "Operação cancelada. O que deseja fazer agora?\n"
        "/registrar - Registrar um novo treino\n"
        "/historico - Ver histórico de treinos"
    )
    return ESCOLHENDO

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata erros do bot."""
    logger.error(f"Erro: {context.error} - Update: {update}")
    if update:
        await update.message.reply_text("Ocorreu um erro. Por favor, tente novamente.")

# Função para manter o bot ativo (ping a cada 25 minutos)
async def keep_alive(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Função para manter o bot ativo no Heroku."""
    logger.info("Bot ainda está ativo!")

def main() -> None:
    """Função principal para iniciar o bot."""
    # Obtém o token do ambiente (para segurança)
    TOKEN = os.environ.get("TOKEN", "SEU_TOKEN_AQUI")
    
    # Cria a aplicação
    application = Application.builder().token(TOKEN).build()
    
    # Configura o conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('registrar', registrar),
            CommandHandler('historico', historico)
        ],
        states={
            ESCOLHENDO: [
                CommandHandler('registrar', registrar),
                CommandHandler('historico', historico)
            ],
            REGISTRANDO: [
                CommandHandler('finalizar', receber_exercicio),
                CommandHandler('cancelar', cancelar),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_exercicio)
            ]
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    # Adiciona job para manter o bot ativo (a cada 25 minutos)
    job_queue = application.job_queue
    job_queue.run_repeating(keep_alive, interval=1500, first=10)
    
    # Inicia o bot com polling (sem webhook)
    application.run_polling(poll_interval=3.0, timeout=30)

if __name__ == '__main__':
    main()
