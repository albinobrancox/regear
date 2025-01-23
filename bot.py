import discord
from discord.ext import commands
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from keep_alive import keep_alive
import datetime

keep_alive()

# --- Constants ---
# TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
CATEGORY_ID = YOUR_CATEGORY_ID
GOOGLE_SHEETS_ID = os.environ.get('YOUR_GOOGLE_SHEETS_ID')
CREDENTIALS_FILE = 'path/to/your/credentials.json'

# --- Google Sheets Setup ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# --- Helper Functions ---
def create_sheet(sheet_name):
    body = {
        'requests': [{
            'addSheet': {
                'properties': {
                    'title': sheet_name
                }
            }
        }]
    }
    sheet.batchUpdate(spreadsheetId=GOOGLE_SHEETS_ID, body=body).execute()
    headers = [['Data', 'Nick', 'Build', 'Link']]
    sheet.values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f"{sheet_name}!A1:D1",
        valueInputOption="RAW",
        body={"values": headers}
    ).execute()

def add_to_sheet(sheet_name, data):
    sheet.values().append(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f"{sheet_name}!A:D",
        valueInputOption="RAW",
        body={"values": [data]}
    ).execute()

# --- Commands ---
@bot.command()
async def regear(ctx, member: discord.Member, *, message: str):
    if not ctx.message.attachments:
        await ctx.send("Por favor, anexe uma imagem para completar o registro.")
        return

    attachment = ctx.message.attachments[0]
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    link = attachment.url

    # Save to Google Sheets
    data = [timestamp, member.name, message, link]
    sheet_name = ctx.channel.name  # Assumes sheet exists with the channel name
    add_to_sheet(sheet_name, data)

    await ctx.send(f"Mensagem registrada para {member.mention}! Link: {link}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def criar_regear(ctx, *, name: str):
    # Create text channel
    category = discord.utils.get(ctx.guild.categories, id=CATEGORY_ID)
    if category is None:
        await ctx.send("Categoria não encontrada.")
        return

    channel = await category.create_text_channel(name)
    await ctx.send(f"Canal criado: {channel.mention}")

    # Create Google Sheets page
    create_sheet(name)
    await ctx.send(f"Página na planilha criada: {name}")

# --- Error Handlers ---
@regear.error
async def regear_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Uso correto: /regear @nick mensagem")
    else:
        await ctx.send("Erro ao processar o comando.")

@criar_regear.error
async def criar_regear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Uso correto: /criar_regear nome_do_canal")
    else:
        await ctx.send("Erro ao processar o comando.")

# --- Run the Bot ---
if __name__ == '__main__':
    tokenx = os.environ.get('token')
    bot.run(tokenx)
