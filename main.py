import discord
from discord.ext import commands
import datetime
from keep_alive import keep_alive
import os

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
def create_embed(report_data):
    embed = discord.Embed(title="Regear Report", color=discord.Color.blue())

    # Numerar os campos Data e Link
    data_values = "\n".join(f"[{i + 1}] {row[0]}" for i, row in enumerate(report_data))
    nick_values = "\n".join(row[1] for row in report_data)
    mensagem_values = "\n".join(row[2] for row in report_data)
    link_values = "\n".join(f"[{i + 1}] {row[3]}" for i, row in enumerate(report_data))

    # Adicionar os campos ao embed
    embed.add_field(name="Data", value=data_values, inline=True)
    embed.add_field(name="Nick", value=nick_values, inline=True)
    embed.add_field(name="Mensagem", value=mensagem_values, inline=True)
    embed.add_field(name="Link", value=link_values, inline=True)

    # Rodapé com o horário UTC
    embed.set_footer(text=f"Relatório gerado em {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return embed

def format_for_spreadsheet(report_data):
    headers = "Data;Nick;Mensagem;Link"
    rows = [f'{row[0]};{row[1]};"{row[2]}";{row[3]}' for row in report_data]
    return f"{headers}\n" + "\n".join(rows)

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

    report_data = []
    for message in messages[1:-1]:
        timestamp = (message.created_at - datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        nick = message.author.display_name
        print(f"Relatorio gerado - {timestamp}")  # Log para depuração
        content = message.content.replace("\n", " ") if message.content else "-"
        attachment_links = [att.url for att in message.attachments]
        link = attachment_links[0] if attachment_links else "-"
        report_data.append([timestamp, nick, content, link])

    report_data.sort(key=lambda x: x[0])

    embed = create_embed(report_data)
    spreadsheet_format = format_for_spreadsheet(report_data)
    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if report_channel:
        await report_channel.send(embed=embed)
        await report_channel.send(f"```{spreadsheet_format}```")
        confirmation_embed = discord.Embed(
            title="REGEAR CLOSED!",
            description="O relatório foi gerado com sucesso.",
            color=discord.Color.green()
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
        description="**Copie sua build conforme abaixo, e cole junto com a print do regear!**\n**Se você morreu mais de uma vez, repita o processo para as demais mortes**\n\n**Não coloque 2 prints em 1 mensagem.**\n\n__Se você tiver a tag \"Core\" escreva junto com a build__\n\nEx: **Segadeira Core**\n\nHeavy Mace\nMartelo 1H\nCajado Runico\nJurador\nSegadeira\nQuebra Reino\nPlangente\nManoplas Cravadas\nMãos Infernais\nQueda Santa\nPostulento\nCajado Enraizado\nLocus\nCajado Astral\nExecrado",
        color=discord.Color.green()
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
