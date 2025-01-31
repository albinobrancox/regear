import discord
from discord.ext import commands
import datetime
from keep_alive import keep_alive
import os
import xml.etree.ElementTree as ET

keep_alive()

# --- Constants ---
REPORT_CHANNEL_ID = 1332523572018675805
MESSAGE_CHANNEL_ID = REPORT_CHANNEL_ID
TOPIC_CHANNEL_ID = 1311066334360109166

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  # Permitir acesso a informações completas dos membros
bot = commands.Bot(command_prefix='/', intents=intents)

# --- Helper Functions ---
def load_builds():
    tree = ET.parse('builds.txt')
    root = tree.getroot()
    builds = {}
    for build in root.findall('.//build'):
        nome_build = build.find('NomeBuild').text
        arma = build.find('.//Arma').text if build.find('.//Arma') is not None else None
        secundaria = build.find('.//Secundaria').text if build.find('.//Secundaria') is not None else None
        elmo = build.find('.//Elmo').text if build.find('.//Elmo') is not None else None
        peito = build.find('.//Peito').text if build.find('.//Peito') is not None else None
        bota = build.find('.//Bota').text if build.find('.//Bota') is not None else None
        capa = build.find('.//Capa').text if build.find('.//Capa') is not None else None
        builds[nome_build] = {
            'Arma': arma,
            'Secundaria': secundaria,
            'Elmo': elmo,
            'Peito': peito,
            'Bota': bota,
            'Capa': capa
        }
    return builds

def create_embed(report_data):
    embed = discord.Embed(title="Regear Report", color=discord.Color.green())

    def truncate(value, limit=1024):
        """Trunca um valor para não exceder o limite de caracteres do Discord."""
        return value[: limit - 3] + "..." if len(value) > limit else value

    # Construir valores com truncamento para evitar erro de campo muito longo
    data_values = truncate("\n".join(f"[{i + 1}] {row[0]}" for i, row in enumerate(report_data)))
    nick_values = truncate("\n".join(row[1] for row in report_data))
    mensagem_values = truncate("\n".join(row[2] for row in report_data))
    link_values = truncate("\n".join(f"[{i + 1}] {row[3]}" for i, row in enumerate(report_data)))
    emoji_values = truncate("\n".join(row[4] for row in report_data))
    build_registrada_values = truncate("\n".join(row[5] for row in report_data))

    # Adicionar os campos ao embed
    embed.add_field(name="Data", value=data_values, inline=True)
    embed.add_field(name="Nick", value=nick_values, inline=True)
    embed.add_field(name="Mensagem", value=mensagem_values, inline=True)
    embed.add_field(name="Link", value=link_values, inline=True)
    embed.add_field(name="Emoji", value=emoji_values, inline=True)
    embed.add_field(name="Build Registrada", value=build_registrada_values, inline=True)

    # Rodapé com o horário UTC
    embed.set_footer(text=f"Relatório gerado em {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return embed

def format_for_spreadsheet(report_data):
    headers = "Data;Nick;Mensagem;Link;Emoji;Build_Registrada"
    rows = [f'{row[0]};{row[1]};"{row[2]}";{row[3]};{row[4]};{row[5]}' for row in report_data]
    return f"{headers}\n" + "\n".join(rows)

def create_purchase_report(purchase_data):
    report = "**Relatório de Compra**\n\n"
    for category, items in purchase_data.items():
        report += f"**{category}:**\n"
        for item, count in items.items():
            if item:  # Ignorar itens vazios
                report += f"{item};{count}\n"
        report += "\n"
    return report

def get_emoji_status(reactions):
    for reaction in reactions:
        if str(reaction.emoji) == '✅':
            return 'V'
        elif str(reaction.emoji) == '❌':
            return 'X'
    return '-'

# --- Commands ---
@bot.command()
async def criar_relatorio(ctx):
    messages = [message async for message in ctx.channel.history(limit=None)]

    if len(messages) < 3:
        embed = discord.Embed(
            title="Erro ao gerar relatório",
            description="Não há mensagens suficientes para gerar o relatório.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=5)
        return

    first_message = messages[-1]
    last_message = messages[0]

    # Carrega as builds do arquivo builds.txt
    builds = load_builds()

    report_data = []
    purchase_data = {
        'Arma': {},
        'Secundaria': {},
        'Elmo': {},
        'Peito': {},
        'Bota': {},
        'Capa': {}
    }

    for message in messages[1:-1]:
        if not message.content or not message.attachments:
            continue  # Ignora mensagens sem texto ou sem imagem

        timestamp = (message.created_at - datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        nick = message.author.display_name
        content = message.content.replace("\n", " ") if message.content else "-"
        attachment_links = [att.url for att in message.attachments]
        link = attachment_links[0] if attachment_links else "-"
        emoji_status = get_emoji_status(message.reactions)

        # Verifica se a build está registrada no arquivo builds.txt
        build_registrada = "Sim" if content in builds else "Não"
        report_data.append([timestamp, nick, content, link, emoji_status, build_registrada])

        # Se a build estiver registrada, adiciona os itens ao relatório de compra
        if content in builds:
            build_info = builds[content]
            for category, item in build_info.items():
                if item:
                    if item in purchase_data[category]:
                        purchase_data[category][item] += 1
                    else:
                        purchase_data[category][item] = 1

    report_data.sort(key=lambda x: x[0])

    if not report_data:
        embed = discord.Embed(
            title="Erro ao gerar relatório",
            description="Nenhuma mensagem válida encontrada para gerar o relatório.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=5)
        return

    embed = create_embed(report_data)
    spreadsheet_format = format_for_spreadsheet(report_data)
    purchase_report = create_purchase_report(purchase_data)

    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if report_channel:
        await report_channel.send(embed=embed)
        await report_channel.send(f"```{spreadsheet_format}```")
        await report_channel.send(purchase_report)
        confirmation_embed = discord.Embed(
            title="REGEAR CLOSED!",
            description="O relatório foi gerado com sucesso.",
            color=discord.Color.red()
        )
        await ctx.send(embed=confirmation_embed)
    else:
        error_embed = discord.Embed(
            title="Erro ao gerar relatório",
            description="Canal de relatório não encontrado.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=5)

@bot.command()
async def criar_regear(ctx, *, mensagem=None):
    if mensagem is None:
        error_embed = discord.Embed(
            title="Erro ao criar mensagem",
            description="Você precisa fornecer uma mensagem ao usar este comando.\nExemplo: `/regear Sua mensagem personalizada aqui`",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=5)
        return

    if ctx.channel.id != MESSAGE_CHANNEL_ID:
        error_embed = discord.Embed(
            title="Erro ao criar mensagem",
            description="Este comando só pode ser usado no canal designado.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=5)
        return

    embed = discord.Embed(
        title=mensagem,
        description="**Copie sua build conforme abaixo, e cole junto com a print do regear!**\n**Se você morreu mais de uma vez, repita o processo para as demais mortes!**\n\n**Não coloque 2 prints em 1 mensagem.**\n\n__Se você tiver a tag \"Core\" escreva junto com a build__\n\nEx: **Segadeira Core**\n\nGolem\nHeavy Mace\nMartelo 1H\nMaça 1H\nPara-Tempo\nCajado-Runico\nJurador\nCajado-Equilibrio\nSincelo\nPrisma\nSegadeira\nCaça-Espiritos\nQuebra Reino\nPlangente\nManoplas Cravadas\nMãos-Infernais\nQueda-Santa\nPostulento\nRampante\nCorrompido\nCajado Enraizado\nLocus\nEnigmatico\nCajado Astral\nExecrado",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Regear criado por {ctx.author.display_name}")

    target_channel = bot.get_channel(TOPIC_CHANNEL_ID)
    if target_channel:
        sent_message = await target_channel.send(embed=embed)
        await sent_message.create_thread(name=mensagem)
        confirmation_embed = discord.Embed(
            title="Mensagem enviada com sucesso!",
            description="Mensagem enviada e tópico criado com sucesso.",
            color=discord.Color.green()
        )
        await ctx.send(embed=confirmation_embed, delete_after=5)
    else:
        error_embed = discord.Embed(
            title="Erro ao enviar mensagem",
            description="Canal de destino não encontrado.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=5)

@bot.command()
@commands.has_permissions(administrator=True)
async def mensagem(ctx, *, texto):
    await ctx.message.delete()
    await ctx.send(texto)

# --- Run the Bot ---
if __name__ == '__main__':
    token = os.environ.get('token')
    bot.run(token)
