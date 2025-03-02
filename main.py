import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import xml.etree.ElementTree as ET
import io
from aiohttp import web

# --- Constants ---
REPORT_CHANNEL_ID = 1345553404432482335
MESSAGE_CHANNEL_ID = REPORT_CHANNEL_ID
TOPIC_CHANNEL_ID = 1343388028793651281
PORT = int(os.environ.get("PORT", 10000))
GUILD_ID = B5-Vz8JfSjiTd-mS2fJ3BQ  # Substitua pelo ID da guilda do Albion Online
ROLE_ID = 1341584969469792287  # Substitua pelo ID do cargo no Discord

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
            await self.tree.sync()
            print("Comandos sincronizados com sucesso.")
        except Exception as e:
            print(f"Erro ao sincronizar comandos: {e}")

bot = MyBot()

# --- Comando /register ---
@bot.tree.command(name="register", description="Registra o usuário se ele estiver na guilda do Albion.")
async def register(interaction: discord.Interaction):
    member = interaction.user
    guild = interaction.guild
    role = guild.get_role(ROLE_ID)

    if not role:
        await interaction.response.send_message("Cargo não encontrado.", ephemeral=True)
        return

    # Aqui você adicionaria a lógica para verificar se o jogador está na guilda do Albion
    is_in_guild = True  # Simulação, substitua pela verificação real

    if is_in_guild:
        await member.add_roles(role)
        await interaction.response.send_message(f"{member.mention} foi registrado com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("Você não está na guilda do Albion Online.", ephemeral=True)

# --- Comando /unregister ---
@bot.tree.command(name="unregister", description="Remove um usuário do sistema de registro.")
@app_commands.describe(user="Usuário a ser removido.")
async def unregister(interaction: discord.Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Apenas administradores podem usar este comando.", ephemeral=True)
        return

    role = interaction.guild.get_role(ROLE_ID)
    if role and role in user.roles:
        await user.remove_roles(role)
    
    await interaction.response.send_message(f"{user.mention} foi removido do registro.", ephemeral=True)

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
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

async def main():
    await start_http_server()
    await bot.start(os.environ.get('token'))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
