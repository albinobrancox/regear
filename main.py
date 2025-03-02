import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import os
import xml.etree.ElementTree as ET
import io
from aiohttp import web
import requests

# --- Constants ---
REPORT_CHANNEL_ID = 1345553404432482335
MESSAGE_CHANNEL_ID = REPORT_CHANNEL_ID
TOPIC_CHANNEL_ID = 1343388028793651281
PORT = int(os.environ.get("PORT", 10000))
GUILD_ID = 'B5-Vz8JfSjiTd-mS2fJ3BQ'  # ID da guilda no Albion Online
MEMBER_ROLE_ID = 1341584969469792287  # ID do cargo de Membro no Discord
ALBION_API_URL = f'https://gameinfo.albiononline.com/api/gameinfo/guilds/{GUILD_ID}/members'
ID_DO_SERVIDOR_DISCORD = 1341574057761443840

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

# Dicionário para armazenar nicks registrados (mapeia ID do usuário para nick)
registered_nicks = {}

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Bot {self.user} está online!')
        try:
            await self.tree.sync()  # Sincroniza os comandos slash
            print("Comandos sincronizados com sucesso.")
        except Exception as e:
            print(f"Erro ao sincronizar comandos: {e}")

bot = MyBot()

# --- Helper Functions ---
def load_builds():
    tree = ET.parse("builds.xml")
    root = tree.getroot()
    builds = {}

    for build in root.findall(".//build"):
        for set_element in build.findall("set"):
            nome_build = set_element.find("NomeBuild")
            h2_element = set_element.find("h2")

            if nome_build is None or h2_element is None or nome_build.text is None:
                continue  # Pula entradas inválidas

            nome = nome_build.text.strip().lower()  # Normaliza o nome da build

            itens = {
                "Arma": h2_element.find("Arma").text.strip() if h2_element.find("Arma") is not None and h2_element.find("Arma").text else "-",
                "Secundaria": h2_element.find("Secundaria").text.strip() if h2_element.find("Secundaria") is not None and h2_element.find("Secundaria").text else "-",
                "Elmo": h2_element.find("Elmo").text.strip() if h2_element.find("Elmo") is not None and h2_element.find("Elmo").text else "-",
                "Peito": h2_element.find("Peito").text.strip() if h2_element.find("Peito") is not None and h2_element.find("Peito").text else "-",
                "Bota": h2_element.find("Bota").text.strip() if h2_element.find("Bota") is not None and h2_element.find("Bota").text else "-",
                "Capa": h2_element.find("Capa").text.strip() if h2_element.find("Capa") is not None and h2_element.find("Capa").text else "-",
            }

            builds[nome] = itens  # Salva a build corretamente

    print("Builds carregadas:", builds)  # Depuração
    return builds

def truncate(value, limit=1024):
    return value[: limit - 3] + "..." if len(value) > limit else value

def format_for_spreadsheet(report_data):
    headers = "Data;Nick;Build;Link;Emoji;Build_Registrada"
    rows = [f'{row[0]};{row[1]};"{row[2]}";{row[3]};{row[4]};{row[5]}' for row in report_data]
    return f"{headers}\n" + "\n".join(rows)

def format_purchase_report(purchase_data):
    headers = "Categoria;Item;Quantidade"
    rows = []
    for category, items in purchase_data.items():
        for item, count in items.items():
            rows.append(f'{category};{item};{count}')
    return f"{headers}\n" + "\n".join(rows)

async def send_long_message(channel, content, filename="relatorio.txt"):
    max_length = 2000
    if len(content) <= max_length:
        await channel.send(f"```{content}```")
    else:
        file = io.BytesIO(content.encode('utf-8'))
        await channel.send(file=discord.File(file, filename))

def get_emoji_status(reactions):
    for reaction in reactions:
        if str(reaction.emoji) == '✅':
            return 'V'
        elif str(reaction.emoji) == '❌':
            return 'X'
    return '-'

# --- Comandos Slash ---
@bot.tree.command(name="criar_relatorio", description="Cria um relatório de regear.")
async def criar_relatorio(interaction: discord.Interaction):
    messages = [message async for message in interaction.channel.history(limit=None)]  # Pega todas as mensagens do canal

    # Ordena as mensagens do mais antigo para o mais recente
    messages.reverse()  
    
    # Filtra apenas as mensagens enviadas antes do comando
    messages = [msg for msg in messages if msg.created_at < interaction.created_at]
    
    # Pega a última mensagem antes do comando ser executado
    last_message = messages[-1] if messages else None

    if len(messages) < 2:
        embed = discord.Embed(
            title="Erro ao gerar relatório",
            description="Não há mensagens suficientes para gerar o relatório.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    builds = load_builds()
    report_data = []
    purchase_data = {key: {} for key in ['Arma', 'Secundaria', 'Elmo', 'Peito', 'Bota', 'Capa']}

    for message in messages[1:]:
        if not message.content or not message.attachments:
            continue

        timestamp = (message.created_at - datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        nick = message.author.display_name
        content = message.content.strip().lower()
        attachment_links = [att.url for att in message.attachments]
        link = attachment_links[0] if attachment_links else "-"
        emoji_status = get_emoji_status(message.reactions)

        build_registrada = "Sim" if content.lower().strip() in builds else "Não"
        report_data.append([timestamp, nick, content, link, emoji_status, build_registrada])

        content_normalized = content.lower().strip()  # Normaliza a build antes da busca
        if content_normalized in builds:
            for category, item in builds[content_normalized].items():
                if item and item != "-":
                    purchase_data[category][item] = purchase_data[category].get(item, 0) + 1

    report_data.sort(key=lambda x: x[0])

    if not report_data:
        embed = discord.Embed(
            title="Erro ao gerar relatório",
            description="Nenhuma mensagem válida encontrada para gerar o relatório.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    spreadsheet_format = format_for_spreadsheet(report_data)
    purchase_report = format_purchase_report(purchase_data)

    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if report_channel:
        await send_long_message(report_channel, spreadsheet_format, filename="relatorio.txt")
        await send_long_message(report_channel, purchase_report, filename="relatorio_compra.txt")

        confirmation_embed = discord.Embed(
            title="REGEAR CLOSED!",
            description="O relatório foi gerado com sucesso.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=confirmation_embed)
        
@bot.tree.command(name="criar_regear", description="Cria um regear de ZvZ.")
@app_commands.describe(nome_regear="Ex: REGEAR 01/01 23UTC")
async def criar_regear(interaction: discord.Interaction, nome_regear: str):
    if interaction.channel.id != MESSAGE_CHANNEL_ID:
        error_embed = discord.Embed(
            title="Erro ao criar regear",
            description="Este comando só pode ser usado no canal comandos.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    embed = discord.Embed(
        title=nome_regear,  # Alterado de mensagem para nome_regear
        description="**Copie sua build conforme abaixo, e cole junto com a print do regear!**\n**Se você morreu mais de uma vez, repita o processo para as demais mortes!**\n\n**Não coloque 2 prints em 1 mensagem.**\n\n__Se você tiver a tag \"Core\" escreva junto com a build__\n\nEx: **Segadeira Core**\n\nGolem\nMaça 1H Clapper\nMartelo 1H\nMaça 1H\nMaça Pesada\nEquilibrio\nPara Tempo\nSilence\nDanacao\nExecrado\nLocus\nArvore\nJurador\nOculto\nEntalhada\nQueda Santa\nPostulento\nQuebra Reinos\nCaça Espiritos\nMaos Infernais\nSegadeira\nCravadas\nUrsinas\nAstral\nPrisma",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Regear criado por {interaction.user.display_name}")

    target_channel = bot.get_channel(TOPIC_CHANNEL_ID)
    if target_channel:
        sent_message = await target_channel.send(embed=embed)
        await sent_message.create_thread(name=nome_regear)  # Alterado para nome_regear
        confirmation_embed = discord.Embed(
            title="Regear criado com sucesso!",
            description="Regear e tópico criado com sucesso.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
    else:
        error_embed = discord.Embed(
            title="Erro ao criar regear",
            description="Canal de destino não encontrado.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
@bot.tree.command(name="mensagem", description="Envia uma mensagem no canal usando bot.")
@app_commands.describe(texto="mensagem.")
async def mensagem(interaction: discord.Interaction, texto: str):
    # Verifica se o usuário tem permissão de administrador
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return

    # Se o usuário for administrador, envia a mensagem
    await interaction.response.send_message(texto)

@bot.tree.command(name="register", description="Registra um usuário na guilda do Albion Online.")
@app_commands.describe(nick="Seu nome no Albion Online")
async def register(interaction: discord.Interaction, nick: str):
    print(f"[LOG] Comando /register acionado por {interaction.user} com nick: {nick}")
    
    try:
        # Verifica se o nick já está registrado por outro membro no Discord
        if nick in registered_nicks.values():
            print(f"[LOG] Tentativa de registro com nick já usado: {nick}")
            embed = discord.Embed(
                title="Erro no registro",
                description="Este nick já foi registrado por outro membro. Se esse for seu nick, contate um administrador.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verifica se o jogador está na guilda no Albion Online
        response = requests.get(ALBION_API_URL)
        response.raise_for_status()
        members = response.json()
        print("[LOG] Lista de membros da guilda obtida com sucesso.")

        player = next((m for m in members if m['Name'] == nick), None)
        if not player:
            print(f"[LOG] O usuário {nick} não foi encontrado na guilda.")
            embed = discord.Embed(
                title="Erro no registro",
                description=f"O {nick} não está na guilda Ethereal, ou a API do Albion ainda não está atualizada",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        # Atribui o cargo de Membro e renomeia o usuário
        member = interaction.guild.get_member(interaction.user.id)
        if member:
            print(f"[LOG] Usuário {interaction.user} encontrado no servidor.")
            role = interaction.guild.get_role(MEMBER_ROLE_ID)
            if role:
                await member.add_roles(role)
                await member.edit(nick=nick)
                registered_nicks[interaction.user.id] = nick  # Salva o nick como registrado
                print(f"[LOG] Cargo atribuído e nome alterado para {nick}.")
                embed = discord.Embed(
                    title="Registro bem-sucedido!",
                    description=f"Registrado com sucesso! Bem-vindo, {nick}.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                print("[ERRO] Cargo de Membro não encontrado.")
                embed = discord.Embed(
                    title="Erro no registro",
                    description="Cargo de Membro não encontrado.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            print("[ERRO] Usuário não encontrado no servidor.")
            embed = discord.Embed(
                title="Erro no registro",
                description="Erro ao encontrar seu usuário no servidor.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"[ERRO] Erro no comando /register: {e}")
        embed = discord.Embed(
            title="Erro inesperado",
            description="Ocorreu um erro ao processar seu registro. Tente novamente mais tarde.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Servidor HTTP Simples ---
async def handle(request):
    return web.Response(text="Alive")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"Servidor HTTP rodando na porta {PORT}")

# --- Inicialização do Bot e Servidor HTTP ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online!')
    try:
        synced = await bot.tree.sync()  # Sincroniza os comandos slash
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

async def main():
    await start_http_server()
    await bot.start(os.environ.get('token'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
