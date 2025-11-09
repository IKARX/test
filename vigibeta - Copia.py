# ================================================
# LOL STATS BOT - VERSÃO CORRIGIDA
# ================================================

import discord
from discord.ext import commands
import requests
from typing import Optional
import time

# ================================================
# CONFIGURAÇÕES
# ================================================
TOKEN_BOT = ''
API_KEY = ''

PLATFORMS = {
    'br': 'https://br1.api.riotgames.com',
    'na': 'https://na1.api.riotgames.com',
    'eu': 'https://euw1.api.riotgames.com',
    'kr': 'https://kr.api.riotgames.com',
    'jp': 'https://jp1.api.riotgames.com'
}

# ================================================
# BOT SETUP
# ================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Bot ONLINE: {bot.user}')
    synced = await bot.tree.sync()
    print(f'Comandos sincronizados: {len(synced)}')
    await bot.tree.sync()
    print("READY")

# ================================================
# FUNÇÃO AUXILIAR (RETORNO CONSISTENTE)
# ================================================
def riot_request(url, max_retries=3):
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code == 200:
                return r.json(), 200
            
            return None, r.status_code

        except:
            if attempt == max_retries - 1:
                return None, 0
            time.sleep(1)

    return None, 0

# ================================================
# COMANDO /lol
# ================================================
@bot.tree.command(name='lol', description='Rank, winrate e K/D/A das últimas 5 partidas')
async def lol(interaction: discord.Interaction, jogador: str, região: Optional[str] = 'br'):
    await interaction.response.defer()

    if região not in PLATFORMS:
        await interaction.followup.send('Região inválida (use: br, na, eu, kr, jp).')
        return
    
    base_url = PLATFORMS[região]

    try:
        # Summoner
        summoner_url = f'{base_url}/lol/summoner/v4/summoners/by-name/{jogador}'
        summoner_data, code = riot_request(summoner_url)

        if summoner_data is None:
            if code == 404:
                await interaction.followup.send("Jogador não encontrado.")
            elif code == 401:
                await interaction.followup.send("Chave expirada.")
            elif code == 403:
                await interaction.followup.send("Chave bloqueada.")
            elif code == 429:
                await interaction.followup.send("Rate limit excedido.")
            else:
                await interaction.followup.send("Erro de conexão.")
            return
        
        summoner_id = summoner_data['id']
        puuid = summoner_data['puuid']
        level = summoner_data['summonerLevel']
        icon = summoner_data['profileIconId']

        # Rank
        league_url = f'{base_url}/lol/league/v4/entries/by-summoner/{summoner_id}'
        league_data, code = riot_request(league_url)

        rank = "Unranked"
        lp = wins = losses = 0

        if league_data:
            for e in league_data:
                if e['queueType'] == 'RANKED_SOLO_5x5':
                    rank = f"{e['tier']} {e['rank']}"
                    lp = e['leaguePoints']
                    wins = e['wins']
                    losses = e['losses']
                    break

        winrate = round(wins / (wins + losses) * 100, 1) if wins + losses > 0 else 0

        # Match history
        matchlist_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count=5'
        match_ids, code = riot_request(matchlist_url)

        k = d = a = recent_w = 0

        if match_ids:
            for mid in match_ids[:5]:
                match_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/{mid}'
                match_data, code = riot_request(match_url)

                if match_data is None:
                    continue

                for p in match_data['info']['participants']:
                    if p['puuid'] == puuid:
                        k += p['kills']
                        d += p['deaths']
                        a += p['assists']
                        recent_w += 1 if p['win'] else 0
                        break

        kd = round(k / d, 2) if d > 0 else k
        recent_wr = round((recent_w / len(match_ids)) * 100, 1) if match_ids else 0

        # Embed
        embed = discord.Embed(title=f"LoL • {jogador}", color=0xC19A6B)
        embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/15.24.1/img/profileicon/{icon}.png")
        embed.add_field(name="Rank", value=f"{rank} • {lp} LP", inline=True)
        embed.add_field(name="Winrate", value=f"{wins}W/{losses}L ({winrate}%)", inline=True)
        embed.add_field(name="Nível", value=f"{level}", inline=True)
        embed.add_field(name="Últimas 5", value=f"{recent_w}/5 ({recent_wr}%)", inline=True)
        embed.add_field(name="K/D/A", value=f"{k}/{d}/{a} • {kd}", inline=False)
        embed.set_footer(text="Dados via Riot API")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"Erro interno: {str(e)}")

# ================================================
# /ajuda
# ================================================
@bot.tree.command(name='ajuda', description='Como usar o bot')
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="Comando", color=0xC19A6B)
    embed.add_field(name="/lol jogador região", value="Exemplo: `/lol Faker kr`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

print("Iniciando bot...")
bot.run(TOKEN_BOT)
