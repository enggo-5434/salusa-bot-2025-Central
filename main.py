import discord
from discord import ui
from discord.ext import commands
import os
import requests

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

ADMIN_CHANNEL_ID = 1361241867798446171  # Channel ID ห้องแอดมิน
REGISTER_CHANNEL_ID = 1361242784509726791  # Channel ID ห้องลงทะเบียน

# Role IDs
NEWBIE_ROLE_ID = 1361182119069749310         # สำหรับสมาชิกใหม่
PLAYER_ROLE_ID = 1361186568416657593         # สำหรับผู้เล่นที่ลงทะเบียนแล้ว
PVP_ROLE_ID = 1391706430339547158            # สำหรับสาย PVP
PVE_ROLE_ID = 1391706869671661659            # สำหรับสาย PVE

STEAM_API_KEY = os.getenv("STEAM_API_KEY")  # ตั้งค่า Steam API Key ใน Environment Variable

def get_steam_profile(steam_id64):
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id64}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'response' in data and 'players' in data['response'] and len(data['response']['players']) > 0:
            player = data['response']['players'][0]
            return {
                'steamid': player.get('steamid'),
                'personaname': player.get('personaname'),
                'profileurl': player.get('profileurl'),
                'avatar': player.get('avatarfull'),
                'realname': player.get('realname', 'N/A'),
                'country': player.get('loccountrycode', 'N/A')
            }
    return None

# ------------------ เพิ่ม Role ให้สมาชิกใหม่ ------------------
@bot.event
async def on_member_join(member):
    guild = member.guild
    role = guild.get_role(NEWBIE_ROLE_ID)
    if role:
        await member.add_roles(role, reason="สมาชิกใหม่เข้าร่วมเซิร์ฟเวอร์")

# ------------------ Registration Modal ------------------

class RegistrationForm(ui.Modal, title="ลงทะเบียนผู้เล่น SALUSA"):
    steam_id = ui.TextInput(label="Steam ID", placeholder="กรุณากรอก Steam ID ของคุณ", required=True)
    character_name = ui.TextInput(label="ชื่อตัวละคร", placeholder="กรุณากรอกชื่อตัวละคร", required=True)
    player_type = ui.TextInput(label="ประเภทผู้เล่น (PVP หรือ PVE)", placeholder="กรุณาพิมพ์ PVP หรือ PVE เท่านั้น", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        try:
            # ถอด role สมาชิกใหม่ เพิ่ม role ผู้เล่น
            guild = interaction.guild
            member = interaction.user

            newbie_role = guild.get_role(NEWBIE_ROLE_ID)
            player_role = guild.get_role(PLAYER_ROLE_ID)
            pvp_role = guild.get_role(PVP_ROLE_ID)
            pve_role = guild.get_role(PVE_ROLE_ID)

            # ถอด role สมาชิกใหม่ ถ้ามี
            if newbie_role in member.roles:
                await member.remove_roles(newbie_role, reason="ลงทะเบียนสำเร็จ")

            # เพิ่ม role ผู้เล่น
            if player_role and player_role not in member.roles:
                await member.add_roles(player_role, reason="ลงทะเบียนสำเร็จ")

            # ตรวจสอบประเภทผู้เล่น (ไม่สนตัวพิมพ์)
            player_type_value = self.player_type.value.strip().lower()
            if player_type_value == "pvp" and pvp_role and pvp_role not in member.roles:
                await member.add_roles(pvp_role, reason="ลงทะเบียนเป็น PVP")
            elif player_type_value == "pve" and pve_role and pve_role not in member.roles:
                await member.add_roles(pve_role, reason="ลงทะเบียนเป็น PVE")

            # ตอบกลับผู้ใช้
            await interaction.response.send_message(
                "ลงทะเบียนเรียบร้อยแล้ว! ข้อมูลของคุณถูกส่งไปยังแอดมินแล้ว",
                ephemeral=True
            )

            # ส่ง Embed ไปที่ห้องแอดมิน
            admin_channel = interaction.client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                embed = discord.Embed(
                    title="การลงทะเบียนใหม่",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Steam ID (ที่กรอก)", value=self.steam_id.value, inline=False)
                embed.add_field(name="ชื่อตัวละคร", value=self.character_name.value, inline=False)
                embed.add_field(name="ประเภทผู้เล่น", value=self.player_type.value.strip().upper(), inline=False)
                embed.add_field(name="Discord User", value=f"{interaction.user} (ID: {interaction.user.id})", inline=False)
                embed.add_field(name="ข้อมูล Steam ที่ตรวจสอบ", value=steam_info, inline=False)
                embed.set_footer(text=f"ลงทะเบียนโดย {interaction.user.display_name}")
                await admin_channel.send(embed=embed)

            # ตอบกลับผู้ใช้ (ephemeral)
            await interaction.response.send_message(
                "ลงทะเบียนเรียบร้อยแล้ว! ข้อมูลของคุณถูกส่งไปยังแอดมินแล้ว",
                ephemeral=True
            )

            # ส่ง DM ยืนยัน
            try:
                await member.send("การลงทะเบียนสำเร็จ ยินดีต้อนรับเข้าสู่ SALUSA")
            except Exception:
                pass  # กรณีผู้ใช้ปิด DM

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
                "สำหรับผู้เล่น PvP โปรดอ่าน https://discord.com/channels/1360583634481975327/1390025183149949028 \n"
                "สำหรับผู้เล่น PvE โปรดอ่าน https://discord.com/channels/1360583634481975327/1390025018167267368 \n"
                "กรุณากดปุ่ม 'ลงทะเบียนที่นี่' ด้านล่าง"
            ),
            color=discord.Color.blue()
        )
        await register_channel.send(embed=embed, view=RegisterButton())

# ------------------ รันบอท ------------------

bot.run(os.getenv('discordkey'))