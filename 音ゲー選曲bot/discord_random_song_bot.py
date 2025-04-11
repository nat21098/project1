import discord
from discord import app_commands
import json
import random
import asyncio
import logging
from discord.ext import commands
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    filename='bot.log',
    encoding='utf-8'
)
logger = logging.getLogger('music_bot')

# 難易度ごとの色を定義
DIFFICULTY_COLORS = {
    'EASY': 0x66DD11,    # 緑 (#66dd11)
    'NORMAL': 0x33BBEE,  # 水色 (#33bbee)
    'HARD': 0xFEAA00,    # オレンジ (#feaa00)
    'EXPERT': 0xEE4466,  # 赤 (#ee4466)
    'MASTER': 0xBB33EE,  # 紫 (#bb33ee)
    'APPEND': 0xFF7DC9   # ピンク (#ff7dc9)
}

# デフォルトの楽曲データ
DEFAULT_SONGS = {
    "Tell Your World": {
        "EASY": 5, "NORMAL": 10, "HARD": 16,
        "EXPERT": 22, "MASTER": 26, "APPEND": 25
    }
}

HELP_MESSAGE = '''音ゲー選曲Bot - コマンド一覧
バージョン: 1.0.0

基本的な使い方
入力欄に /コマンドを入力してください

基本コマンド
/help - このヘルプを表示
/all - 全ての楽曲からランダムに選択

レベル指定の例
/level 26 - レベル26の楽曲をランダムに選択
/level 26- - レベル26以上の楽曲をランダムに選択
/level -31 - レベル31以下の楽曲をランダムに選択
/level 26-31 - レベル26から31までの楽曲をランダムに選択

難易度指定の例
/difficulty EASY - EASY難易度の楽曲をランダムに選択
/difficulty NORMAL - NORMAL難易度の楽曲をランダムに選択
/difficulty HARD - HARD難易度の楽曲をランダムに選択
/difficulty EXPERT - EXPERT難易度の楽曲をランダムに選択
/difficulty MASTER - MASTER難易度の楽曲をランダムに選択
/difficulty APPEND - APPEND難易度の楽曲をランダムに選択

組み合わせの例
/difficulty MASTER 26 - MASTER難易度のレベル26の楽曲をランダムに選択
/difficulty MASTER 26- - MASTER難易度のレベル26以上の楽曲をランダムに選択
/difficulty MASTER -31 - MASTER難易度のレベル31以下の楽曲をランダムに選択
/difficulty MASTER 26-31 - MASTER難易度のレベル26から31までの楽曲をランダムに選択'''

# Discordクライアントの設定
intents = discord.Intents.default()
intents.message_content = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MusicBot()

async def load_songs(max_retries=3):
    """楽曲データを非同期で読み込む"""
    for attempt in range(max_retries):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, 'songs.json')

            if not os.path.exists(json_path):
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(DEFAULT_SONGS, f, ensure_ascii=False, indent=4)
                return DEFAULT_SONGS

            async with asyncio.timeout(5.0):  # 5秒でタイムアウト
                with open(json_path, 'r', encoding='utf-8') as f:
                    songs_data = json.load(f)
                    return songs_data if songs_data else DEFAULT_SONGS

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                return DEFAULT_SONGS
        except Exception as e:
            logger.error(f"読み込みエラー: {e}")
            return DEFAULT_SONGS
    return DEFAULT_SONGS

def get_all_songs(songs_data):
    """すべての楽曲を取得"""
    result = []
    for song_name, difficulties in songs_data.items():
        for diff, level in difficulties.items():
            if level is not None:
                result.append({
                    "name": song_name,
                    "difficulty": diff,
                    "level": int(level)
                })
    return result

def find_songs_by_difficulty(difficulty, songs_data):
    """指定された難易度の楽曲を検索"""
    result = []
    for song_name, difficulties in songs_data.items():
        if difficulty in difficulties and difficulties[difficulty] is not None:
            result.append({
                "name": song_name,
                "difficulty": difficulty,
                "level": int(difficulties[difficulty])
            })
    return result

def find_songs_by_difficulty_and_level(difficulty, level_str, songs_data):
    """指定された難易度とレベルの楽曲を検索"""
    result = []
    try:
        if level_str:
            if '-' in level_str:
                if level_str.endswith('-'):
                    min_level = int(level_str[:-1])
                    max_level = float('inf')
                elif level_str.startswith('-'):
                    min_level = 1
                    max_level = int(level_str[1:])
                else:
                    min_level, max_level = map(int, level_str.split('-'))
            else:
                min_level = max_level = int(level_str)

            for song_name, difficulties in songs_data.items():
                if difficulty in difficulties and difficulties[difficulty] is not None:
                    level = int(difficulties[difficulty])
                    if min_level <= level <= (max_level if max_level != float('inf') else level):
                        result.append({
                            "name": song_name,
                            "difficulty": difficulty,
                            "level": level
                        })
    except ValueError:
        pass
    return result

def find_songs_by_level_range(level_str, songs_data):
    """指定されたレベル範囲の楽曲を検索"""
    result = []
    try:
        if '-' in level_str:
            if level_str.endswith('-'):
                min_level = int(level_str[:-1])
                max_level = float('inf')
            elif level_str.startswith('-'):
                min_level = 1
                max_level = int(level_str[1:])
            else:
                min_level, max_level = map(int, level_str.split('-'))
        else:
            min_level = max_level = int(level_str)

        for song_name, difficulties in songs_data.items():
            for diff, level in difficulties.items():
                if level is not None:
                    level = int(level)
                    if min_level <= level <= (max_level if max_level != float('inf') else level):
                        result.append({
                            "name": song_name,
                            "difficulty": diff,
                            "level": level
                        })
    except ValueError:
        pass
    return result

@bot.tree.command(name="help", description="コマンド一覧を表示")
async def help(interaction: discord.Interaction):
    await interaction.response.defer()

    embed = discord.Embed(
        title="ヘルプ",
        description=HELP_MESSAGE,
        color=0x00FF00
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="all", description="全ての楽曲からランダムに選択")
async def all(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        songs_data = await load_songs()
        level_songs = get_all_songs(songs_data)

        if level_songs:
            selected_song = random.choice(level_songs)
            embed = discord.Embed(
                description=f"{selected_song['name']} / {selected_song['difficulty']} / Lv. {selected_song['level']}",
                color=DIFFICULTY_COLORS.get(selected_song['difficulty'], 0xFFFFFF)
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("楽曲が見つかりませんでした。")
    except Exception as e:
        logger.error(f"allコマンドエラー: {e}")
        await interaction.followup.send("処理中にエラーが発生しました。")

@bot.tree.command(name="level", description="レベルを指定して楽曲を選択")
@app_commands.describe(level="レベルまたはレベル範囲（例: 26, 26-, -31, 26-31）")
async def level(interaction: discord.Interaction, level: str):
    await interaction.response.defer()

    try:
        songs_data = await load_songs()
        level_songs = find_songs_by_level_range(level, songs_data)

        if level_songs:
            selected_song = random.choice(level_songs)
            embed = discord.Embed(
                description=f"{selected_song['name']} / {selected_song['difficulty']} / Lv. {selected_song['level']}",
                color=DIFFICULTY_COLORS.get(selected_song['difficulty'], 0xFFFFFF)
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("条件に合う楽曲が見つかりませんでした。")
    except Exception as e:
        logger.error(f"levelコマンドエラー: {e}")
        await interaction.followup.send("処理中にエラーが発生しました。")

@bot.tree.command(name="difficulty", description="難易度を指定して楽曲を選択")
@app_commands.describe(
    difficulty="難易度（EASY/NORMAL/HARD/EXPERT/MASTER/APPEND）",
    level="レベルまたはレベル範囲（オプション）"
)
@app_commands.choices(difficulty=[
    app_commands.Choice(name="EASY", value="EASY"),
    app_commands.Choice(name="NORMAL", value="NORMAL"),
    app_commands.Choice(name="HARD", value="HARD"),
    app_commands.Choice(name="EXPERT", value="EXPERT"),
    app_commands.Choice(name="MASTER", value="MASTER"),
    app_commands.Choice(name="APPEND", value="APPEND"),
])
async def difficulty(interaction: discord.Interaction, difficulty: str, level: str = None):
    await interaction.response.defer()

    try:
        songs_data = await load_songs()

        if level:
            level_songs = find_songs_by_difficulty_and_level(difficulty, level, songs_data)
        else:
            level_songs = find_songs_by_difficulty(difficulty, songs_data)

        if level_songs:
            selected_song = random.choice(level_songs)
            embed = discord.Embed(
                description=f"{selected_song['name']} / {selected_song['difficulty']} / Lv. {selected_song['level']}",
                color=DIFFICULTY_COLORS.get(selected_song['difficulty'], 0xFFFFFF)
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("条件に合う楽曲が見つかりませんでした。")
    except Exception as e:
        logger.error(f"difficultyコマンドエラー: {e}")
        await interaction.followup.send("処理中にエラーが発生しました。")

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')
    logger.info(f'ボット起動: {bot.user}')

if __name__ == "__main__":
    # 環境変数からトークンを取得
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("環境変数 'DISCORD_TOKEN' が設定されていません")
    bot.run(TOKEN)