import discord
import os
from flask import Flask
from discord import ui, SelectOption
from discord.ext import commands
from myserver import keep_alive

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import json
from discord import ui
from datetime import datetime

# แก้ไขส่วน intents
intents = discord.Intents.default()
intents.members = True  # new member in Dis
intents.message_content = True  # Read text

bot = commands.Bot(command_prefix='/', intents=intents)

WELCOME_CHANNEL_ID = 1375102199327363083  
REGISTER_CHANNEL_ID = 1361242784509726791 
ADMIN_CHANNEL_ID = 1361241867798446171
AUTOROLE_ID = 1361182119069749310  
PLAYER_ROLE_ID = 1361186568416657593
ADMIN_ROLE_ID = 1360585582832521236
PROFESSION_DISPLAY_CHANNEL_ID = 1384193675566776391
BANNER_TEMPLATE = "welcome_SalusaBG2.png"  
REGISTRATIONS_FILE = "registrations.json"  
CONFIG_FILE = "config.json"

# Dictionary สำหรับเก็บข้อมูลอาชีพและ Role ID
PROFESSIONS = {
    1361305826798604440: "ผู้พิทักษ์แห่ง SALUSA",
    1361303692766216313: "อันธพาลแห่ง SALUSA", 
    1361303934563778751: "เพลงดาบทมิฬแห่ง SALUSA",
    1361304137979002991: "เสียงกรีดร้องแห่ง SALUSA",
    1361304383345918022: "แสงยานุภาพแห่ง SALUSA",
    1361304546068005064: "สายธารแห่ง SALUSA",
    1361304712061648908: "มุมมืดแห่ง SALUSA",
    1361304887253667921: "เปลวเพลิงแห่ง SALUSA",
    1361305463718936616: "สายฟ้าแห่ง SALUSA",
    1361305165336150096: "สายลมแห่ง SALUSA",
    1361305687103111238: "ปากท้องแห่ง SALUSA",
    1361306017438109808: "ฟันเฟืองแห่ง SALUSA",
    1361306190868516897: "เมล็ดพันธุ์แห่ง SALUSA",
    1361306485409190061: "นักตกปลาแห่ง SALUSA",
    1361306651054968994: "แสงสีทองแห่ง SALUSA"
}

# เก็บ Message ID ของข้อความแสดงรายชื่อแต่ละอาชีพ
profession_messages = {}

# Load all log registrations
def load_registrations():
    try:
        with open(REGISTRATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save all log registrations
def save_registrations(data):
    with open(REGISTRATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Load config 
def load_config():
    global AUTOROLE_ID, ADMIN_ROLE_ID
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if 'AUTOROLE_ID' in config:
                AUTOROLE_ID = config['AUTOROLE_ID']
            if 'ADMIN_ROLE_ID' in config:
                ADMIN_ROLE_ID = config['ADMIN_ROLE_ID']
    except (FileNotFoundError, json.JSONDecodeError):
        # Use default value 
        pass

# Save config
def save_config():
    global AUTOROLE_ID, ADMIN_ROLE_ID
    config = {
        'AUTOROLE_ID': AUTOROLE_ID,
        'ADMIN_ROLE_ID': ADMIN_ROLE_ID
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# เพิ่ม event listener สำหรับตรวจจับการเข้า-ออกของสมาชิก
@bot.event
async def on_member_join(member):
    """เรียกเมื่อมีสมาชิกใหม่เข้าร่วมเซิร์ฟเวอร์"""
    # เพิ่ม Auto Role ให้สมาชิกใหม่
    try:
        autorole = member.guild.get_role(AUTOROLE_ID)
        if autorole:
            await member.add_roles(autorole)
            print(f"เพิ่ม Auto Role ให้ {member.name} สำเร็จ")
        else:
            print(f"ไม่พบ Auto Role (ID: {AUTOROLE_ID})")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเพิ่ม Auto Role: {str(e)}")
    
    # รับข้อมูลช่องต้อนรับ
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    
    if welcome_channel and not member.bot:  # ไม่ต้อนรับบอท
        # สร้างแบนเนอร์ต้อนรับ
        welcome_banner = await create_welcome_banner(member)
        
        # ส่งข้อความต้อนรับพร้อมแบนเนอร์
        await welcome_channel.send(
            f"**ยินดีต้อนรับ {member.mention} สู่ SALUSA!** 🎉\n"
            f"กรุณาเข้าไปที่ <#{REGISTER_CHANNEL_ID}> เพื่อลงทะเบียนเข้าร่วมเซิร์ฟเวอร์",
            file=welcome_banner
        )

# Create registrations form Modal
class RegistrationForm(ui.Modal, title="ลงทะเบียนผู้เล่น SALUSA"):
    steam_id = ui.TextInput(label="Steam ID", placeholder="กรุณากรอก Steam ID ของคุณ", required=True)
    character_name = ui.TextInput(label="ชื่อตัวละคร", placeholder="กรุณากรอกชื่อตัวละคร", required=True)
    player_type = ui.TextInput(label="ประเภทผู้เล่น (PVP หรือ PVE)", placeholder="กรุณาพิมพ์ PVP หรือ PVE", required=True)


async def on_submit(self, interaction: discord.Interaction):
    try:
        data = {
            "user_id": interaction.user.id,
            "username": interaction.user.name,
            "steam_id": self.steam_id.value,
            "character_name": self.character_name.value,
            "player_type": self.player_type.value.strip().upper(),  # แปลงเป็นตัวพิมพ์ใหญ่และตัดช่องว่าง
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        registrations = load_registrations()
        registrations[str(interaction.user.id)] = data
        save_registrations(registrations)

        # ส่ง DM ขอบคุณ
        try:
            await interaction.user.send(
                f"ขอบคุณสำหรับการลงทะเบียน!\nSteam ID: {data['steam_id']}\n"
                f"ชื่อตัวละคร: {data['character_name']}\nประเภทผู้เล่น: {data['player_type']}"
            )
        except:
            pass

        # ส่ง embed แจ้งแอดมิน
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            embed = discord.Embed(title="การลงทะเบียนใหม่", color=discord.Color.blue())
            embed.add_field(name="Steam ID", value=data['steam_id'], inline=False)
            embed.add_field(name="ชื่อตัวละคร", value=data['character_name'], inline=False)
            embed.add_field(name="ประเภทผู้เล่น", value=data['player_type'], inline=False)
            embed.set_footer(text=f"ลงทะเบียนเมื่อ {data['timestamp']}")
            await admin_channel.send(embed=embed)

        # เพิ่ม Role และตั้งชื่อเล่น
        guild = interaction.guild or (await bot.fetch_guild(interaction.guild_id))
        member = guild.get_member(interaction.user.id)
        if member:
            player_role = guild.get_role(PLAYER_ROLE_ID)
            if player_role:
                await member.add_roles(player_role)

            # ตั้งชื่อเล่นตามเงื่อนไข PVP หรือ PVE
            prefix = ""
            if data['player_type'] == "PVP":
                prefix = "PVP"
            elif data['player_type'] == "PVE":
                prefix = "PVE"
            else:
                prefix = data['player_type']  # กรณีอื่นๆ ใช้ตามที่กรอกมา

            new_nick = f"{prefix}_{data['character_name']}"
            try:
                await member.edit(nick=new_nick)
            except Exception as e:
                print(f"ไม่สามารถเปลี่ยนชื่อเล่นได้: {e}")

        await interaction.response.send_message("ลงทะเบียนเรียบร้อยแล้ว! คุณได้รับบทบาทผู้เล่นแล้ว", ephemeral=True)

    except Exception as e:
        print(f"Error processing registration: {str(e)}")
        try:
            await interaction.response.send_message("เกิดข้อผิดพลาดในการลงทะเบียน โปรดลองใหม่อีกครั้ง", ephemeral=True)
        except:
            pass

# ปุ่มลงทะเบียน
class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ลงทะเบียนที่นี่", style=discord.ButtonStyle.primary, emoji="📝")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationForm())

@bot.event
async def on_ready():
    """เรียกเมื่อบอทเริ่มทำงานและพร้อมใช้งาน"""
    print(f'{bot.user.name} พร้อมใช้งานแล้ว!')
    
    # ตรวจสอบและสร้างข้อความลงทะเบียนในช่องลงทะเบียน
    register_channel = bot.get_channel(REGISTER_CHANNEL_ID)
    if register_channel:
        # ลบข้อความเก่าและสร้างข้อความใหม่
        async for message in register_channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()
        
        embed = discord.Embed(
            title="ลงทะเบียนเข้าร่วม SALUSA",
            description=(
                "ยินดีต้อนรับสู่เซิร์ฟเวอร์ SALUSA!\n"
                "โปรดอ่าน https://discord.com/channels/1360583634481975327/1390020203898998957 \n"
                "สำหรับผู้เล่น PvE โปรดอ่าน https://discord.com/channels/1360583634481975327/1390025018167267368 \n"
                "สำหรับผู้เล่น PvP โปรดอ่าน https://discord.com/channels/1360583634481975327/1390025183149949028 \n"
                "กรุณาลงทะเบียนเพื่อเข้าร่วมเซิร์ฟเวอร์ของเรา โดยคลิกที่ปุ่ม 'ลงทะเบียนที่นี่' ด้านล่าง\n"
            ),
            color=discord.Color.blue()
        )
        
        await register_channel.send(embed=embed, view=RegisterButton())

async def create_welcome_banner(member):
    """สร้างแบนเนอร์ต้อนรับสําหรับสมาชิกใหม่"""
    # โหลดรูปโปรไฟล์ของสมาชิก
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_response = requests.get(avatar_url)
    avatar_image = Image.open(BytesIO(avatar_response.content)).convert('RGBA')
    avatar_size = 255
    mask_size = 255
    
    # ปรับขนาดรูปโปรไฟล์และทําให้เป็นวงกลม
    avatar_image = avatar_image.resize((avatar_size, avatar_size))
    
    # สร้างหน้ากากวงกลมสําหรับรูปโปรไฟล์
    mask = Image.new('L', (255, 255), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, mask_size, mask_size), fill=255)
    
    # โหลดแม่แบบแบนเนอร์
    try:
        template = Image.open(BANNER_TEMPLATE).convert('RGBA')
    except FileNotFoundError:
        # สร้างแบนเนอร์เริ่มต้นหากไม่พบแม่แบบ
        template = Image.new('RGBA', (1024, 500), (47, 49, 54, 255))
        
    # วางรูปโปรไฟล์ในวงกลมลงบนแบนเนอร์
    avatar_with_mask = Image.new('RGBA', (mask_size, mask_size))
    avatar_with_mask.paste(avatar_image, (0, 0), mask)
    pos_x = 512 - (mask_size // 2)
    template.paste(avatar_with_mask, (pos_x, 70), avatar_with_mask)
    
    # เพิ่มข้อความต้อนรับและชื่อผู้ใช้
    draw = ImageDraw.Draw(template)
    
    # พยายามโหลดฟอนต์ที่สนับสนุนภาษาไทย (อาจต้องดาวน์โหลดและติดตั้งก่อน)
    try:
        title_font = ImageFont.truetype("NotoSans-Regular.ttf", 48)
        user_font = ImageFont.truetype("NotoSans-Regular.ttf", 36)
        watermark_font = ImageFont.truetype("NotoSans-Regular.ttf", 10)  # เพิ่มฟอนต์สำหรับลายน้ำ
    except IOError:
        # ใช้ฟอนต์เริ่มต้นหากไม่พบฟอนต์ที่ต้องการ
        title_font = ImageFont.load_default()
        user_font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()
    
    draw.text((512, 365), "Welcome into SALUSA", fill=(255, 255, 255, 255), font=title_font, anchor="mm")
    draw.text((512, 420), f"{member.display_name}", fill=(230, 126, 32, 255), font=user_font, anchor="mm")
    
    watermark_text = "©2025 All Rights Reserved, Salusa"
    watermark_color = (255, 255, 255, 255) 
    
    watermark_x = template.width // 2  
    watermark_y = template.height - 20  
    
    draw.text((watermark_x, watermark_y), watermark_text, fill=watermark_color, font=watermark_font, anchor="ms")
    
    # บันทึกแบนเนอร์ลงในไฟล์ชั่วคราว
    buffer = BytesIO()
    template.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(buffer, filename='welcome.png')

@bot.command()
@commands.has_permissions(administrator=True)
async def setautorole(ctx, role: discord.Role = None):
    """ตั้งค่า Role ที่จะให้สมาชิกใหม่โดยอัตโนมัติ"""
    global AUTOROLE_ID
    if role is None:
        # ถ้าไม่ระบุ Role จะแสดง Role ปัจจุบัน
        current_role = ctx.guild.get_role(AUTOROLE_ID)
        if current_role:
            await ctx.send(f"Auto Role ปัจจุบันคือ: {current_role.mention}")
        else:
            await ctx.send("ไม่ได้ตั้งค่า Auto Role")
        return
    
    # อัปเดตค่า AUTOROLE_ID
    AUTOROLE_ID = role.id
    
    # บันทึกการตั้งค่า
    save_config()
    
    await ctx.send(f"ตั้งค่า Auto Role เป็น {role.mention} สำเร็จ")

# เพิ่มคำสั่งสำหรับตั้งค่า Admin Role
@bot.command()
@commands.has_permissions(administrator=True)
async def setadminrole(ctx, role: discord.Role = None):
    """ตั้งค่า Admin Role ที่จะถูก mention เมื่อมีการลงทะเบียนใหม่"""
    global ADMIN_ROLE_ID
    if role is None:
        # ถ้าไม่ระบุ Role จะแสดง Role ปัจจุบัน
        current_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        if current_role:
            await ctx.send(f"Admin Role ปัจจุบันคือ: {current_role.mention}")
        else:
            await ctx.send("ไม่ได้ตั้งค่า Admin Role")
        return
    
    # อัปเดตค่า ADMIN_ROLE_ID
    ADMIN_ROLE_ID = role.id
    
    # บันทึกการตั้งค่า
    save_config()
    
    await ctx.send(f"ตั้งค่า Admin Role เป็น {role.mention} สำเร็จ")

# คำสั่งสำหรับทีมงานในการจัดการการลงทะเบียน
@bot.command()
@commands.has_permissions(administrator=True)
async def registrations(ctx):
    """แสดงรายการผู้ใช้ที่รอการอนุมัติ"""
    registrations_data = load_registrations()
    
    if not registrations_data:
        await ctx.send("ไม่มีคำขอลงทะเบียนที่รอการอนุมัติ")
        return
    
    embed = discord.Embed(
        title="รายการคำขอลงทะเบียนที่รอการอนุมัติ",
        color=discord.Color.blue()
    )
    
    for user_id, data in registrations_data.items():
        embed.add_field(
            name=f"ผู้ใช้: {data['username']}",
            value=f"ชื่อในเกม: {data['in_game_name']}\nSteam ID: {data['steam_id']}\nวันที่ลงทะเบียน: {data['timestamp']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

async def create_profession_embed(role_id, guild):
    """สร้าง embed สำหรับอาชีพหนึ่งๆ"""
    role = guild.get_role(role_id)
    if not role:
        return None

    profession_name = PROFESSIONS[role_id]
    
    # สร้าง embed สำหรับอาชีพนี้
    embed = discord.Embed(
        color=role.color if role.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # ใช้ set_author() เพื่อแสดง role icon และชื่ออาชีพ
    if role.display_icon:
        embed.set_author(
            name=f" อาชีพ: {profession_name}",
            icon_url=role.display_icon.url
        )
    else:
        # หาก role ไม่มี icon ให้ใช้ title แบบเดิม
        embed.title = f" อาชีพ: {profession_name}"
    
    # ส่วนที่เหลือของโค้ดเดิม...
    if role.members:
        member_list = []
        for member in role.members:
            join_date = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "ไม่ทราบ"
            member_info = f"{member.mention} • **{member.display_name}** • `{join_date}`"
            member_list.append(member_info)

        if len(member_list) <= 15:
            embed.add_field(
                name=f"📗 รายชื่อสมาชิก ({len(member_list)} คน)",
                value="\n".join(member_list),
                inline=False
            )
        else:
            for i in range(0, len(member_list), 15):
                chunk = member_list[i:i+15]
                field_name = f"📗 รายชื่อสมาชิก ({i+1}-{min(i+15, len(member_list))})"
                embed.add_field(
                    name=field_name,
                    value="\n".join(chunk),
                    inline=False
                )
    else:
        embed.add_field(
            name="📗 รายชื่อสมาชิก",
            value="*ยังไม่มีสมาชิกในอาชีพนี้*",
            inline=False
        )

    embed.set_footer(text="อัปเดตล่าสุด")
    return embed


async def update_profession_display():
    """อัปเดตการแสดงผลรายชื่อผู้ใช้ตามอาชีพทั้งหมด"""
    channel = bot.get_channel(PROFESSION_DISPLAY_CHANNEL_ID)
    if not channel:
        return
    
    # ลบข้อความเก่าทั้งหมดของบอท
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()
    
    profession_messages.clear()
    
    # สร้างข้อความใหม่สำหรับแต่ละอาชีพ
    for role_id in PROFESSIONS.keys():
        embed = await create_profession_embed(role_id, channel.guild)
        if embed:
            message = await channel.send(embed=embed)
            profession_messages[role_id] = message.id

async def update_single_profession_display(role_id, guild):
    """อัปเดตการแสดงผลของอาชีพเดียว"""
    channel = bot.get_channel(PROFESSION_DISPLAY_CHANNEL_ID)
    if not channel or role_id not in PROFESSIONS:
        return
    
    embed = await create_profession_embed(role_id, guild)
    if not embed:
        return
    
    # อัปเดตข้อความเดิมหรือสร้างใหม่
    if role_id in profession_messages:
        try:
            message = await channel.fetch_message(profession_messages[role_id])
            await message.edit(embed=embed)
        except discord.NotFound:
            # ข้อความเก่าถูกลบแล้ว สร้างใหม่
            message = await channel.send(embed=embed)
            profession_messages[role_id] = message.id
    else:
        message = await channel.send(embed=embed)
        profession_messages[role_id] = message.id

# Event สำหรับตรวจจับการเปลี่ยนแปลง role
@bot.event
async def on_member_update(before, after):
    """ตรวจจับการเปลี่ยนแปลง role ของสมาชิก"""
    # เช็คว่า role เปลี่ยนแปลงหรือไม่
    before_roles = set(role.id for role in before.roles)
    after_roles = set(role.id for role in after.roles)
    
    # หา role ที่เพิ่มหรือลบ
    added_roles = after_roles - before_roles
    removed_roles = before_roles - after_roles
    
    # อัปเดตการแสดงผลสำหรับ role ที่เปลี่ยนแปลง
    changed_profession_roles = (added_roles | removed_roles) & set(PROFESSIONS.keys())
    
    for role_id in changed_profession_roles:
        await update_single_profession_display(role_id, after.guild)

# คำสั่งสำหรับทีมงานในการรีเฟรชการแสดงผล
@bot.command()
@commands.has_permissions(administrator=True)
async def refresh_professions(ctx):
    """รีเฟรชการแสดงผลรายชื่อผู้ใช้ตามอาชีพ"""
    await ctx.send("กำลังอัปเดตการแสดงผลรายชื่อผู้ใช้ตามอาชีพ...")
    await update_profession_display()
    await ctx.send("✅ อัปเดตการแสดงผลเรียบร้อยแล้ว!")

# คำสั่งตั้งค่าช่องแสดงผล
@bot.command()
@commands.has_permissions(administrator=True)
async def set_profession_channel(ctx, channel: discord.TextChannel = None):
    """ตั้งค่าช่องสำหรับแสดงรายชื่อผู้ใช้ตามอาชีพ"""
    global PROFESSION_DISPLAY_CHANNEL_ID
    
    if channel is None:
        channel = ctx.channel
    
    PROFESSION_DISPLAY_CHANNEL_ID = channel.id
    await ctx.send(f"✅ ตั้งค่าช่องแสดงรายชื่อผู้ใช้ตามอาชีพเป็น {channel.mention} แล้ว")
    
    # อัปเดตการแสดงผลทันที
    await update_profession_display()

# คำสั่งแสดงสถิติอาชีพ
@bot.command()
@commands.has_permissions(administrator=True)
async def profession_stats(ctx):
    """แสดงสถิติจำนวนสมาชิกในแต่ละอาชีพ"""
    embed = discord.Embed(
        title="📊 สถิติสมาชิกตามอาชีพ",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    total_members = 0
    stats_list = []
    
    for role_id, profession_name in PROFESSIONS.items():
        role = ctx.guild.get_role(role_id)
        if role:
            member_count = len(role.members)
            total_members += member_count
            stats_list.append(f"**{profession_name}**: {member_count} คน")
    
    embed.add_field(
        name="จำนวนสมาชิกในแต่ละอาชีพ",
        value="\n".join(stats_list) if stats_list else "ไม่มีข้อมูล",
        inline=False
    )
    
    embed.add_field(
        name="รวมทั้งหมด",
        value=f"**{total_members}** คน",
        inline=False
    )
    
    embed.set_footer(text="สถิติ ณ เวลา")
    await ctx.send(embed=embed)



# งานหลักตอนเริ่มบอท
load_config()
keep_alive()

bot.run(os.getenv('discordkey'))