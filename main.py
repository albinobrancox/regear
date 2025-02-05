import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import xml.etree.ElementTree as ET
import io
from aiohttp import web

# --- Constants ---
REPORT_CHANNEL_ID = 1332523572018675805
MESSAGE_CHANNEL_ID = REPORT_CHANNEL_ID
TOPIC_CHANNEL_ID = 1311066334360109166
PORT = int(os.environ.get("PORT", 10000))

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True 

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
    tree = ET.parse('builds.xml')
    root = tree.getroot()
    builds = {}
    for build in root.findall('.//build'):
        for nome_build in build.findall('NomeBuild'):
            nome = nome_build.text.strip().lower()
            itens = {
                'Arma': build.find('.//Arma').text or '-',
                'Secundaria': build.find('.//Secundaria').text or '-',
                'Elmo': build.find('.//Elmo').text or '-',
                'Peito': build.find('.//Peito').text or '-',
                'Bota': build.find('.//Bota').text or '-',
                'Capa': build.find('.//Capa').text or '-',
            }
            builds[nome] = itens
    return builds

def truncate(value, limit=1024):
    return value[: limit - 3] + "..." if len(value) > limit else value

# def create_embed(report_data):
    # embed = discord.Embed(title="Regear Report", color=discord.Color.green())
    # limited_data = report_data[:15]  
    # data_values = truncate("\n".join(f"[{i + 1}] {row[0]}" for i, row in enumerate(limited_data)))
    # nick_values = truncate("\n".join(row[1] for row in limited_data))
    # mensagem_values = truncate("\n".join(row[2] for row in limited_data))
    # link_values = truncate("\n".join(f"[{i + 1}] {row[3]}" for i, row in enumerate(limited_data)))
    # emoji_values = truncate("\n".join(row[4] for row in limited_data))
    # build_registrada_values = truncate("\n".join(row[5] for row in limited_data))

    # embed.add_field(name="Data", value=data_values, inline=True)
    # embed.add_field(name="Nick", value=nick_values, inline=True)
    # embed.add_field(name="Build", value=mensagem_values, inline=True)
    # embed.add_field(name="Link", value=link_values, inline=True)
    # embed.add_field(name="Emoji", value=emoji_values, inline=True)
    # embed.add_field(name="Build Registrada", value=build_registrada_values, inline=True)

    # if len(report_data) > 15:
        # embed.set_footer(text="Mostrando apenas as primeiras 15 linhas.")

    # return embed

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
@bot.tree.command(name="criar-relatorio", description="Cria um relatório de regear.")
async def criar_relatorio(interaction: discord.Interaction):
    messages = [message async for message in interaction.channel.history(limit=None)]

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

        build_registrada = "Sim" if content in builds else "Não"
        report_data.append([timestamp, nick, content, link, emoji_status, build_registrada])

        if content in builds:
            for category, item in builds[content].items():
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
        
@bot.tree.command(name="criar-regear", description="Cria um regear de ZvZ.")
@app_commands.describe(mensagem="A mensagem para o regear.")
async def criar_regear(interaction: discord.Interaction, mensagem: str):
    if interaction.channel.id != MESSAGE_CHANNEL_ID:
        error_embed = discord.Embed(
            title="Erro ao criar regear",
            description="Este comando só pode ser usado no canal comandos.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    embed = discord.Embed(
        title=mensagem,
        description="**Copie sua build conforme abaixo, e cole junto com a print do regear!**\n**Se você morreu mais de uma vez, repita o processo para as demais mortes!**\n\n**Não coloque 2 prints em 1 mensagem.**\n\n__Se você tiver a tag \"Core\" escreva junto com a build__\n\nEx: **Segadeira Core**\n\nGolem\nMaça 1H Clapper\nMartelo 1H\nMaça 1H\nMaça Pesada\nEquilibrio\nPara Tempo\nSilence\nDanacao\nExecrado\nLocus\nArvore\nJurador\nOculto\nEntalhada\nQueda Santa\nPostulento\nQuebra Reinos\nCaça Espiritos\nMaos Infernais\nSegadeira\nCravadas\nUrsinas\nAstral\nPrisma",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Regear criado por {interaction.user.display_name}")

    target_channel = bot.get_channel(TOPIC_CHANNEL_ID)
    if target_channel:
        sent_message = await target_channel.send(embed=embed)
        await sent_message.create_thread(name=mensagem)
        confirmation_embed = discord.Embed(
            title="Regear criado com sucesso!",
            description="Regear e tópico criado com sucesso.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
    else:
        error_embed = discord.Embed(
            title="Erro ao criar regeae",
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
