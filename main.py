import discord
from discord import ui
from discord.ext import commands
import os

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

ADMIN_CHANNEL_ID = 1361241867798446171  # Channel ID ห้องแอดมิน
REGISTER_CHANNEL_ID = 1361242784509726791  # Channel ID ห้องลงทะเบียน

# ------------------ Registration Modal ------------------

class RegistrationForm(ui.Modal, title="ลงทะเบียนผู้เล่น SALUSA"):
    steam_id = ui.TextInput(label="Steam ID", placeholder="กรุณากรอก Steam ID ของคุณ", required=True)
    character_name = ui.TextInput(label="ชื่อตัวละคร", placeholder="กรุณากรอกชื่อตัวละคร", required=True)
    player_type = ui.TextInput(label="ประเภทผู้เล่น (PVP หรือ PVE)", placeholder="กรุณาพิมพ์ PVP หรือ PVE", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message(
                "ลงทะเบียนเรียบร้อยแล้ว! ข้อมูลของคุณถูกส่งไปยังแอดมินแล้ว",
                ephemeral=True
            )
            admin_channel = interaction.client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                embed = discord.Embed(
                    title="การลงทะเบียนใหม่",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Steam ID", value=self.steam_id.value, inline=False)
                embed.add_field(name="ชื่อตัวละคร", value=self.character_name.value, inline=False)
                embed.add_field(name="ประเภทผู้เล่น", value=self.player_type.value.strip().upper(), inline=False)
                embed.set_footer(text=f"ลงทะเบียนโดย {interaction.user.display_name}")
                await admin_channel.send(embed=embed)
        except Exception as e:
            print(f"Error processing registration: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "เกิดข้อผิดพลาดในการลงทะเบียน โปรดลองใหม่อีกครั้ง",
                    ephemeral=True
                )

# ------------------ Registration Button ------------------

class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ลงทะเบียนที่นี่", style=discord.ButtonStyle.primary, emoji="📝")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationForm())

# ------------------ on_ready Event ------------------

@bot.event
async def on_ready():
    print(f'{bot.user.name} พร้อมใช้งานแล้ว!')
    register_channel = bot.get_channel(REGISTER_CHANNEL_ID)
    if register_channel:
        # ลบข้อความเก่าของบอท
        async for message in register_channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()
        embed = discord.Embed(
            title="ลงทะเบียนเข้าร่วม SALUSA",
            description=(
                "ยินดีต้อนรับสู่เซิร์ฟเวอร์ SALUSA!\n"
                "โปรดอ่านกฎและข้อมูลที่เกี่ยวข้องก่อนลงทะเบียน\n"
                "กรุณากดปุ่ม 'ลงทะเบียนที่นี่' ด้านล่าง"
            ),
            color=discord.Color.blue()
        )
        await register_channel.send(embed=embed, view=RegisterButton())

# ------------------ รันบอท ------------------

bot.run(os.getenv('discordkey'))