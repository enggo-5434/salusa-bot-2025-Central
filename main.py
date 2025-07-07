import discord
from discord import ui
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import requests

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

ADMIN_CHANNEL_ID = 1361241867798446171
BOTCONSOLE_CHANNEL_ID = 1391816083136319659
REGISTER_CHANNEL_ID = 1361242784509726791
WELCOME_CHANNEL_ID = 1375102199327363083
NEWBIE_ROLE_ID = 1361182119069749310
PLAYER_ROLE_ID = 1361186568416657593
PVP_ROLE_ID = 1391706430339547158
PVE_ROLE_ID = 1391706869671661659

STEAM_API_KEY = os.getenv("STEAM_API_KEY")

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

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import discord

async def report_to_admin(bot, message):
    admin_channel = bot.get_channel(BOTCONSOLE_CHANNEL_ID)
    if admin_channel:
        await admin_channel.send(message)

async def create_welcome_banner(member):
    # โหลดเลเยอร์ 1 (พื้นหลัง)
    try:
        layer1 = Image.open("welcome_Salusa_Layer1.png").convert('RGBA')
    except FileNotFoundError:
        layer1 = Image.new('RGBA', (1024, 500), (47, 49, 54, 255))

    base = layer1.copy()

    # โหลดและวางรูปโปรไฟล์ผู้ใช้ (วงกลม)
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_response = requests.get(avatar_url)
    avatar_image = Image.open(BytesIO(avatar_response.content)).convert('RGBA')
    avatar_size = 255
    mask = Image.new('L', (avatar_size, avatar_size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar_image = avatar_image.resize((avatar_size, avatar_size))
    avatar_circle = Image.new('RGBA', (avatar_size, avatar_size))
    avatar_circle.paste(avatar_image, (0, 0), mask)
    pos_x = 512 - (avatar_size // 2)
    pos_y = 65
    base.paste(avatar_circle, (pos_x, pos_y), avatar_circle)

    # โหลดและซ้อนทับเลเยอร์ 2
    try:
        layer2 = Image.open("welcome_Salusa_Layer2.png").convert('RGBA')
        base = Image.alpha_composite(base, layer2)
    except FileNotFoundError:
        pass  # ข้ามถ้าไม่มีไฟล์

    # โหลดและซ้อนทับเลเยอร์ 3
    try:
        layer3 = Image.open("welcome_Salusa_Layer3.png").convert('RGBA')
        base = Image.alpha_composite(base, layer3)
    except FileNotFoundError:
        pass  # ข้ามถ้าไม่มีไฟล์

    # เพิ่มข้อความต้อนรับและชื่อผู้ใช้
    draw = ImageDraw.Draw(base)
    try:
        title_font = ImageFont.truetype("NotoSans-Regular.ttf", 48)
        user_font = ImageFont.truetype("NotoSans-Regular.ttf", 36)
        watermark_font = ImageFont.truetype("NotoSans-Regular.ttf", 10)
    except IOError:
        title_font = ImageFont.load_default()
        user_font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()

    draw.text((512, 365), "Welcome into SALUSA", fill=(255, 255, 255, 255), font=title_font, anchor="mm")
    draw.text((512, 420), f"{member.display_name}", fill=(255, 237, 223, 255), font=user_font, anchor="mm")
    watermark_text = "©2025 All Rights Reserved, Salusa"
    draw.text((base.width // 2, base.height - 20), watermark_text, fill=(255, 255, 255, 255), font=watermark_font, anchor="ms")

    buffer = BytesIO()
    base.save(buffer, format='PNG')
    buffer.seek(0)
    return discord.File(buffer, filename='welcome.png')

@bot.event
async def on_member_join(member):
    guild = member.guild
    role = guild.get_role(NEWBIE_ROLE_ID)
    if role:
        await member.add_roles(role, reason="สมาชิกใหม่เข้าร่วมเซิร์ฟเวอร์")
        await report_to_admin(bot, f"สมาชิกใหม่: {member} (ID: {member.id}) เข้าร่วมเซิร์ฟเวอร์ และได้รับ role newbie")

    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel and not member.bot:
        welcome_banner = await create_welcome_banner(member)
        await welcome_channel.send(
            f"**ยินดีต้อนรับ {member.mention} สู่ SALUSA!** 🎉\n"
            f"กรุณาเข้าไปที่ <#{REGISTER_CHANNEL_ID}> เพื่อลงทะเบียนเข้าร่วมเซิร์ฟเวอร์",
            file=welcome_banner
        )

class RegistrationForm(ui.Modal, title="ลงทะเบียนผู้เล่น SALUSA"):
    steam_id = ui.TextInput(label="Steam ID", required=True)
    character_name = ui.TextInput(label="ชื่อตัวละคร", required=True)
    player_type = ui.TextInput(label="ประเภทผู้เล่น (PVP หรือ PVE)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            member = interaction.user
            newbie_role = guild.get_role(NEWBIE_ROLE_ID)
            player_role = guild.get_role(PLAYER_ROLE_ID)
            pvp_role = guild.get_role(PVP_ROLE_ID)
            pve_role = guild.get_role(PVE_ROLE_ID)

            # ถอด role สมาชิกใหม่
            if newbie_role in member.roles:
                await member.remove_roles(newbie_role, reason="ลงทะเบียนสำเร็จ")
                await report_to_admin(interaction.client, f"ลบ role 'newbie' จาก {member.display_name}")

            # เพิ่ม role ผู้เล่น
            if player_role and player_role not in member.roles:
                await member.add_roles(player_role, reason="ลงทะเบียนสำเร็จ")
                await report_to_admin(interaction.client, f"เพิ่ม role 'player' ให้กับ {member.display_name}")

            # เพิ่ม role PVP/PVE
            player_type_value = self.player_type.value.strip().lower()
            if player_type_value == "pvp" and pvp_role and pvp_role not in member.roles:
                await member.add_roles(pvp_role, reason="ลงทะเบียนเป็น PVP")
                await report_to_admin(interaction.client, f"เพิ่ม role 'PVP' ให้กับ {member.display_name}")
            elif player_type_value == "pve" and pve_role and pve_role not in member.roles:
                await member.add_roles(pve_role, reason="ลงทะเบียนเป็น PVE")
                await report_to_admin(interaction.client, f"เพิ่ม role 'PVE' ให้กับ {member.display_name}")

            # เปลี่ยน nickname เป็นชื่อตัวละคร
            await member.edit(nick=self.character_name.value.strip(), reason="เปลี่ยนชื่อเล่นเป็นชื่อตัวละคร")
            await report_to_admin(interaction.client, f"เปลี่ยน nickname ของ {member.display_name} เป็น {self.character_name.value.strip()}")

            # ตรวจสอบ Steam
            steam_profile = get_steam_profile(self.steam_id.value.strip())
            if steam_profile:
                await report_to_admin(interaction.client, f"ตรวจสอบ Steam สำเร็จ: {steam_profile['personaname']} ({steam_profile['steamid']})")
            else:
                await report_to_admin(interaction.client, "ตรวจสอบ Steam ไม่สำเร็จ หรือ Steam API Key ไม่ถูกต้อง")

            # ส่ง Embed ไปที่ห้องแอดมิน
            admin_channel = interaction.client.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                embed = discord.Embed(
                    title="การลงทะเบียนใหม่",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Steam ID", value=self.steam_id.value, inline=False)
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
            await report_to_admin(interaction.client, f"เกิดข้อผิดพลาด: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "เกิดข้อผิดพลาดในการลงทะเบียน โปรดลองใหม่อีกครั้ง",
                    ephemeral=True
                )
        pass    

class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ลงทะเบียนที่นี่", style=discord.ButtonStyle.primary, emoji="📝")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationForm())

@bot.event
async def on_ready():
    print(f'{bot.user.name} พร้อมใช้งานแล้ว!')
    register_channel = bot.get_channel(REGISTER_CHANNEL_ID)
    if register_channel:
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

bot.run(os.getenv('discordkey'))
