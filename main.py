import discord
from discord.ext import commands
import datetime
import os
import xml.etree.ElementTree as ET
import io

# --- Constants ---
REPORT_CHANNEL_ID = 1332523572018675805
MESSAGE_CHANNEL_ID = REPORT_CHANNEL_ID
TOPIC_CHANNEL_ID = 1311066334360109166

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True  
bot = commands.Bot(command_prefix='/', intents=intents)

# --- Helper Functions ---
def load_builds():
    tree = ET.parse('builds.txt')
    root = tree.getroot()
    builds = {}
    for build in root.findall('.//build'):
        nome_build = build.find('NomeBuild').text
        builds[nome_build] = {tag: build.find(f'.//{tag}').text or '-' for tag in ['Arma', 'Secundaria', 'Elmo', 'Peito', 'Bota', 'Capa']}
    return builds

def truncate(value, limit=1024):
    """Trunca um valor para não exceder o limite de caracteres do Discord."""
    return value[: limit - 3] + "..." if len(value) > limit else value

def create_embed(report_data):
    embed = discord.Embed(title="Regear Report", color=discord.Color.green())

    limited_data = report_data[:15]  
    data_values = truncate("\n".join(f"[{i + 1}] {row[0]}" for i, row in enumerate(limited_data)))
    nick_values = truncate("\n".join(row[1] for row in limited_data))
    mensagem_values = truncate("\n".join(row[2] for row in limited_data))
    link_values = truncate("\n".join(f"[{i + 1}] {row[3]}" for i, row in enumerate(limited_data)))
    emoji_values = truncate("\n".join(row[4] for row in limited_data))
    build_registrada_values = truncate("\n".join(row[5] for row in limited_data))

    embed.add_field(name="Data", value=data_values, inline=True)
    embed.add_field(name="Nick", value=nick_values, inline=True)
    embed.add_field(name="Mensagem", value=mensagem_values, inline=True)
    embed.add_field(name="Link", value=link_values, inline=True)
    embed.add_field(name="Emoji", value=emoji_values, inline=True)
    embed.add_field(name="Build Registrada", value=build_registrada_values, inline=True)

    if len(report_data) > 15:
        embed.set_footer(text="Mostrando apenas as primeiras 15 linhas.")

    return embed

def format_for_spreadsheet(report_data):
    headers = "Data;Nick;Mensagem;Link;Emoji;Build_Registrada"
    rows = [f'{row[0]};{row[1]};"{row[2]}";{row[3]};{row[4]};{row[5]}' for row in report_data]
    return f"{headers}\n" + "\n".join(rows)

def format_purchase_report(purchase_data):
    headers = "Item;Quantidade"
    rows = [f'{item};{count}' for category in purchase_data.values() for item, count in category.items()]
    return f"{headers}\n" + "\n".join(rows)

async def send_long_message(channel, content):
    """Divide e envia uma mensagem longa em múltiplas partes de até 4000 caracteres."""
    parts = [content[i:i+4000] for i in range(0, len(content), 4000)]
    for part in parts:
        await channel.send(f"```{part}```")

def get_emoji_status(reactions):
    for reaction in reactions:
        if str(reaction.emoji) == '✅':
            return 'V'
        elif str(reaction.emoji) == '❌':
            return 'X'
    return '-'

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

    builds = load_builds()
    report_data = []
    purchase_data = {key: {} for key in ['Arma', 'Secundaria', 'Elmo', 'Peito', 'Bota', 'Capa']}

    for message in messages[1:-1]:
        if not message.content or not message.attachments:
            continue

        timestamp = (message.created_at - datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        nick = message.author.display_name
        content = message.content.replace("\n", " ")
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
        await ctx.send(embed=embed, delete_after=5)
        return

    embed = create_embed(report_data)
    spreadsheet_format = format_for_spreadsheet(report_data)
    purchase_report = format_purchase_report(purchase_data)

    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if report_channel:
        await report_channel.send(embed=embed)
        
        if len(spreadsheet_format) > 4000:
            file = io.BytesIO(spreadsheet_format.encode('utf-8'))
            await report_channel.send(file=discord.File(file, "relatorio.csv"))
        else:
            await send_long_message(report_channel, spreadsheet_format)

        if len(purchase_report) > 4000:
            file = io.BytesIO(purchase_report.encode('utf-8'))
            await report_channel.send(file=discord.File(file, "relatorio_compra.csv"))
        else:
            await send_long_message(report_channel, purchase_report)

        confirmation_embed = discord.Embed(
            title="REGEAR CLOSED!",
            description="O relatório foi gerado com sucesso.",
            color=discord.Color.red()
        )
        await ctx.send(embed=confirmation_embed)

@bot.command()
async def mensagem(ctx, *, texto):
    await ctx.message.delete()
    await ctx.send(texto)

if __name__ == '__main__':
    token = os.environ.get('token')
    bot.run(token)
