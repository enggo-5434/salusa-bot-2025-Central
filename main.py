import discord
import os
from discord.ext import commands, tasks  # เพิ่ม tasks สำหรับทำงานเบื้องหลัง
from myserver import keep_alive

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import json
from discord import ui
from datetime import datetime

# แก้ไขส่วน intents ให้เพิ่ม presence intent
intents = discord.Intents.default()
intents.members = True  # new member in Dis
intents.message_content = True  # Read text
intents.presences = True  # เพิ่ม presence intent เพื่อให้สามารถตรวจจับสถานะของบอทอื่นๆ ได้


bot = commands.Bot(command_prefix='!', intents=intents)

WELCOME_CHANNEL_ID = 1375102199327363083  
REGISTER_CHANNEL_ID = 1361242784509726791 
ADMIN_CHANNEL_ID = 1361241867798446171
BOT_STATUS_CHANNEL_ID = 1374821568839942258 
AUTOROLE_ID = 1361182119069749310  
PLAYER_ROLE_ID = 1361186568416657593
ADMIN_ROLE_ID = 1360585582832521236
BANNER_TEMPLATE = "welcome_SalusaBG2.png"  
REGISTRATIONS_FILE = "registrations.json"  
CONFIG_FILE = "config.json"

# เพิ่มตัวแปรสำหรับเก็บสถานะบอทก่อนหน้า
bot_status_cache = {}

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
    global AUTOROLE_ID, ADMIN_ROLE_ID, BOT_STATUS_CHANNEL_ID
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if 'AUTOROLE_ID' in config:
                AUTOROLE_ID = config['AUTOROLE_ID']
            if 'ADMIN_ROLE_ID' in config:
                ADMIN_ROLE_ID = config['ADMIN_ROLE_ID']
            if 'BOT_STATUS_CHANNEL_ID' in config:
                BOT_STATUS_CHANNEL_ID = config['BOT_STATUS_CHANNEL_ID']
    except (FileNotFoundError, json.JSONDecodeError):
        # Use default value 
        pass

# ฟังก์ชันเพื่อสร้าง cache key สำหรับบอท
def get_bot_cache_key(bot_member):
    """สร้าง key สำหรับ cache ข้อมูลบอท"""
    activity_info = None
    if bot_member.activity:
        activity_info = {
            'type': bot_member.activity.type,
            'name': bot_member.activity.name
        }
    
    return {
        'status': bot_member.status,
        'activity': activity_info
    }

# ฟังก์ชันตรวจสอบว่าสถานะบอทเปลี่ยนแปลงหรือไม่  
def has_bot_status_changed(guild):
    """ตรวจสอบว่ามีการเปลี่ยนแปลงสถานะของบอทหรือไม่"""
    current_bots = [member for member in guild.members if member.bot]
    
    # ถ้าจำนวนบอทเปลี่ยน
    if len(current_bots) != len(bot_status_cache.get(guild.id, {})):
        return True
    
    # ตรวจสอบสถานะของแต่ละบอท
    for bot_member in current_bots:
        bot_id = bot_member.id
        current_status = get_bot_cache_key(bot_member)
        cached_status = bot_status_cache.get(guild.id, {}).get(bot_id)
        
        if cached_status != current_status:
            return True
    
    return False

# ฟังก์ชันอัพเดต cache สถานะบอท
def update_bot_status_cache(guild):
    """อัพเดต cache สถานะของบอททั้งหมดในเซิร์ฟเวอร์"""
    if guild.id not in bot_status_cache:
        bot_status_cache[guild.id] = {}
    
    current_bots = [member for member in guild.members if member.bot]
    new_cache = {}
    
    for bot_member in current_bots:
        new_cache[bot_member.id] = get_bot_cache_key(bot_member)
    
    bot_status_cache[guild.id] = new_cache

# ปรับปรุงฟังก์ชันสำหรับแสดงสถานะบอท
async def generate_bot_status_embed(guild):
    """สร้าง Embed สำหรับแสดงสถานะของบอททั้งหมด"""
    # รวบรวมบอททั้งหมดในเซิร์ฟเวอร์
    bots = [member for member in guild.members if member.bot]
    
    # ถ้าไม่มีบอทในเซิร์ฟเวอร์
    if not bots:
        embed = discord.Embed(
            title="📊 ข้อมูลเซิฟเวอร์",
            description="ไม่พบบอทในเซิร์ฟเวอร์นี้",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        return embed
    
    # สร้าง embed สำหรับแสดงสถานะบอท
    embed = discord.Embed(
        title="📊 ข้อมูลเซิร์ฟเวอร์",
        description=f"พบบอททั้งหมด {len(bots)} ตัว",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # เพิ่มไอคอนสำหรับแต่ละสถานะ
    status_icons = {
        discord.Status.online: "🟢 ออนไลน์",
        discord.Status.idle: "🟡 ไม่อยู่",
        discord.Status.dnd: "🔴 ห้ามรบกวน",
        discord.Status.offline: "⚫ ออฟไลน์",
        discord.Status.invisible: "⚪ ซ่อนตัว",
        None: "⚫ ไม่ทราบสถานะ"
    }
    
    # เรียงลำดับบอทตามสถานะ: ออนไลน์ -> ไม่อยู่ -> ห้ามรบกวน -> ออฟไลน์
    status_order = {
        discord.Status.online: 0,
        discord.Status.idle: 1,
        discord.Status.dnd: 2,
        discord.Status.offline: 3,
        discord.Status.invisible: 4,
        None: 5
    }
    
    # แยกบอทตามสถานะก่อนนำมาแสดงผล
    online_bots = []
    offline_bots = []
    
    for bot in bots:
        if bot.status == discord.Status.offline or bot.status is None:
            offline_bots.append(bot)
        else:
            online_bots.append(bot)
    
    # เรียงลำดับบอทแต่ละกลุ่มตามชื่อ
    online_bots.sort(key=lambda b: b.name.lower())
    offline_bots.sort(key=lambda b: b.name.lower())
    
    # เพิ่มหัวข้อสำหรับบอทออนไลน์
    if online_bots:
        embed.add_field(
            name="🟢 บอทที่ออนไลน์",
            value="บอทต่อไปนี้กำลังทำงานอยู่",
            inline=False
        )
        
        # เพิ่มข้อมูลบอทออนไลน์
        for bot in online_bots:
            status_text = status_icons.get(bot.status, "🟢 ออนไลน์")  # เพิ่มค่าเริ่มต้นเพื่อป้องกันกรณีสถานะ None
            
            # ตรวจสอบกิจกรรมของบอท
            activity_text = ""
            if bot.activity:
                activity_type = {
                    discord.ActivityType.playing: "กำลังเล่น",
                    discord.ActivityType.streaming: "กำลังสตรีม",
                    discord.ActivityType.listening: "กำลังฟัง",
                    discord.ActivityType.watching: "กำลังดู",
                    discord.ActivityType.custom: "",
                    discord.ActivityType.competing: "กำลังแข่งขัน"
                }.get(bot.activity.type, "")
                
                if activity_type:
                    activity_text = f"{activity_type} {bot.activity.name}"
                elif isinstance(bot.activity, discord.CustomActivity) and bot.activity.name:
                    activity_text = bot.activity.name
            
            # สร้างข้อความสถานะ
            status_display = status_text
            if activity_text:
                status_display += f" | {activity_text}"
            
            embed.add_field(
                name=f"{bot.display_name}",
                value=status_display,
                inline=False
            )
    
    # เพิ่มหัวข้อสำหรับบอทออฟไลน์
    if offline_bots:
        embed.add_field(
            name="⚫ บอทที่ออฟไลน์",
            value="บอทต่อไปนี้ไม่ได้ทำงานอยู่",
            inline=False
        )
        
        # เพิ่มข้อมูลบอทออฟไลน์
        for bot in offline_bots:
            embed.add_field(
                name=f"{bot.display_name}",
                value="⚫ ออฟไลน์",
                inline=False
            )
    
    # เพิ่ม Server Info หลังจากแสดงสถานะบอท
    embed.add_field(
        name="IP และ Password",
        value="# **IP:** ```79.127.213.68:7082```\n# **Password:** ```PlayerIsPrisoner```",
        inline=False
    )
    
    # ลบ footer timestamp ออก (ไม่ใส่ set_footer)
    
    return embed

# สร้างฟังก์ชันสำหรับอัปเดตข้อความสถานะบอท (ปรับปรุงให้ตรวจสอบการเปลี่ยนแปลงก่อน)
async def update_bot_status_message(guild, force_update=False):
    """อัปเดตข้อความสถานะบอทในช่องที่กำหนด (เฉพาะเมื่อมีการเปลี่ยนแปลง)"""
    channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
    if not channel:
        print(f"ไม่พบช่องสำหรับแสดงสถานะบอท (ID: {BOT_STATUS_CHANNEL_ID})")
        return
    
    # ตรวจสอบการเปลี่ยนแปลงก่อนอัพเดต (ยกเว้นกรณีบังคับอัพเดต)
    if not force_update and not has_bot_status_changed(guild):
        return  # ไม่มีการเปลี่ยนแปลง ไม่ต้องอัพเดต
    
    # ตรวจสอบว่ามีข้อความสถานะอยู่แล้วหรือไม่
    status_message = None
    async for message in channel.history(limit=50):
        if message.author == bot.user and message.embeds and "ข้อมูลเซิฟเวอร์" in message.embeds[0].title:
            status_message = message
            break
    
    # สร้าง embed สถานะบอท
    embed = await generate_bot_status_embed(guild)
    
    # อัปเดตหรือส่งข้อความใหม่
    try:
        if status_message:
            await status_message.edit(embed=embed)
            print(f"อัพเดตสถานะบอทในเซิร์ฟเวอร์ {guild.name}")
        else:
            await channel.send(embed=embed)
            print(f"สร้างข้อความสถานะบอทใหม่ในเซิร์ฟเวอร์ {guild.name}")
        
        # อัพเดต cache หลังจากอัพเดตข้อความสำเร็จ
        update_bot_status_cache(guild)
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการอัพเดตสถานะบอท: {e}")

# เพิ่ม event listener สำหรับตรวจจับการเปลี่ยนแปลงสถานะของสมาชิก (รวมบอท)
@bot.event
async def on_member_update(before, after):
    """ตรวจจับการเปลี่ยนแปลงสถานะของสมาชิก (รวมบอท)"""
    # ตรวจสอบว่าเป็นบอทและมีการเปลี่ยนแปลงสถานะหรือกิจกรรม
    if after.bot and (before.status != after.status or 
                     (before.activity != after.activity)):
        print(f"ตรวจพบการเปลี่ยนสถานะของบอท {after.name}: {before.status} -> {after.status}")
        await update_bot_status_message(after.guild)

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
    
    # ถ้าเป็นบอทที่เข้าใหม่ ให้อัพเดตสถานะ
    if member.bot:
        print(f"ตรวจพบบอทใหม่เข้าร่วม: {member.name}")
        await update_bot_status_message(member.guild)
    
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

@bot.event
async def on_member_remove(member):
    """เรียกเมื่อมีสมาชิกออกจากเซิร์ฟเวอร์"""
    # ถ้าเป็นบอทที่ออกไป ให้อัพเดตสถานะ
    if member.bot:
        print(f"ตรวจพบบอทออกจากเซิร์ฟเวอร์: {member.name}")
        await update_bot_status_message(member.guild)

# ปรับความถี่การอัปเดตสถานะบอท (ลดลงเป็น backup เฉพาะ)
@tasks.loop(minutes=30)  # ลดลงเป็นทุก 30 นาที เป็นการ sync backup
async def bot_status_sync_task():
    """งานในเบื้องหลังสำหรับ sync สถานะบอทเป็นระยะ (backup)"""
    print("กำลัง sync สถานะบอท (backup check)...")
    for guild in bot.guilds:
        # บังคับอัพเดตเพื่อ sync ข้อมูล
        await update_bot_status_message(guild, force_update=True)

# รอให้บอทพร้อมก่อนเริ่มงานในเบื้องหลัง
@bot_status_sync_task.before_loop
async def before_bot_status_sync_task():
    """รอให้บอทพร้อมก่อนเริ่มงานในเบื้องหลัง"""
    await bot.wait_until_ready()

# เพิ่มคำสั่งสำหรับตั้งค่าช่องแสดงสถานะบอท
@bot.command()
@commands.has_permissions(administrator=True)
async def setbotstatuschannel(ctx, channel: discord.TextChannel = None):
    """ตั้งค่าช่องสำหรับแสดงสถานะบอทอัตโนมัติ"""
    global BOT_STATUS_CHANNEL_ID
    if channel is None:
        # ถ้าไม่ระบุช่อง จะแสดงช่องปัจจุบัน
        current_channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
        if current_channel:
            await ctx.send(f"ช่องแสดงสถานะบอทปัจจุบันคือ: {current_channel.mention}")
        else:
            await ctx.send("ไม่ได้ตั้งค่าช่องแสดงสถานะบอท")
        return
    
    # สร้างหรือโหลดไฟล์การตั้งค่า
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    # อัปเดตค่า BOT_STATUS_CHANNEL_ID
    config['BOT_STATUS_CHANNEL_ID'] = channel.id
    
    # บันทึกการตั้งค่า
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    # อัปเดตค่า BOT_STATUS_CHANNEL_ID
    BOT_STATUS_CHANNEL_ID = channel.id
    
    # สร้างข้อความสถานะบอทในช่องใหม่ทันที
    await update_bot_status_message(ctx.guild, force_update=True)
    
    await ctx.send(f"ตั้งค่าช่องแสดงสถานะบอทเป็น {channel.mention} สำเร็จ")

# เพิ่มคำสั่งสำหรับบังคับอัปเดตสถานะบอททันที
@bot.command()
@commands.has_permissions(administrator=True)
async def updatebotstatus(ctx):
    """บังคับอัปเดตสถานะบอททันที"""
    await ctx.send("กำลังอัปเดตสถานะบอท...")
    await update_bot_status_message(ctx.guild, force_update=True)
    await ctx.send("อัปเดตสถานะบอทเรียบร้อยแล้ว")

# Create registrations form Modal
class RegistrationForm(ui.Modal, title="ลงทะเบียนผู้เล่น SALUSA"):
    in_game_name = ui.TextInput(label="ชื่อในเกม", placeholder="กรุณากรอกชื่อตัวละครในเกม", required=True)
    steam_id = ui.TextInput(label="Steam ID", placeholder="กรุณากรอก Steam ID ของคุณ", required=True)
    profession = ui.TextInput(label="คุณสนใจอาชีพไหนใน SALUSA", placeholder="กรุณากรอกอาชีพที่สนใจ", required=True)
    gold_methods = ui.TextInput(label="คุณสามารถหาทอง [Gold] ได้จากวิธีใดบ้าง", placeholder="[ตัวอย่าง: นำขายเข้าตลาดหุ้น]", required=True)
    server_rules = ui.TextInput(label="จะเกิดอะไรขึ้นหากทิ้งรถไว้ในโซนต้องห้าม", placeholder="[ตัวอย่าง: ได้รับเงิน SD 3000]", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # รวบรวมข้อมูล
            user_data = {
                "user_id": interaction.user.id,
                "username": interaction.user.name,
                "in_game_name": self.in_game_name.value,
                "steam_id": self.steam_id.value,
                "profession": self.profession.value,
                "gold_methods": self.gold_methods.value,
                "server_rules": self.server_rules.value,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # บันทึกข้อมูลลงในไฟล์
            registrations = load_registrations()
            
            # ตรวจสอบว่าข้อมูลเดิมมีอยู่แล้วหรือไม่ (อนุญาตให้ส่งซ้ำได้)
            if str(interaction.user.id) in registrations:
                update_message = "ข้อมูลลงทะเบียนของคุณได้รับการอัปเดตแล้ว! ทีมงานจะตรวจสอบข้อมูลของคุณเร็วๆ นี้"
            else:
                update_message = "ขอบคุณสำหรับการลงทะเบียน! ทีมงานจะตรวจสอบข้อมูลของคุณเร็วๆ นี้"
                
            # บันทึกหรืออัปเดตข้อมูล
            registrations[str(interaction.user.id)] = user_data
            save_registrations(registrations)
            
            # ตอบกลับผู้ใช้
            await interaction.response.send_message(
                update_message, 
                ephemeral=True
            )
            
            # ส่งแจ้งเตือนไปยังช่องทีมงาน (แยกออกจาก interaction response)
            admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                # สร้าง embed สำหรับข้อมูลการลงทะเบียน
                embed = discord.Embed(
                    title="การลงทะเบียนใหม่",
                    description=f"ผู้ใช้ {interaction.user.mention} ได้ส่งคำขอลงทะเบียน",
                    color=discord.Color.blue()
                )
                embed.add_field(name="ชื่อในเกม", value=self.in_game_name.value, inline=False)
                embed.add_field(name="Steam ID", value=self.steam_id.value, inline=False)
                embed.add_field(name="อาชีพที่สนใจ", value=self.profession.value, inline=False)
                embed.add_field(name="วิธีหาทอง", value=self.gold_methods.value, inline=False)
                embed.add_field(name="โซนต้องห้าม", value=self.server_rules.value, inline=False)
                
                # สร้างปุ่มอนุมัติและปฏิเสธ
                view = AdminActionView(interaction.user.id)
                
                # เพิ่ม mention admin role ในข้อความ
                admin_role_mention = f"<@&{ADMIN_ROLE_ID}>"
                await admin_channel.send(
                    f"{admin_role_mention} มีการลงทะเบียนใหม่ที่รอการอนุมัติ!", 
                    embed=embed, 
                    view=view
                )
        
        except Exception as e:
            print(f"Error processing registration: {str(e)}")
            try:
                await interaction.response.send_message(
                    "เกิดข้อผิดพลาดในการลงทะเบียน โปรดลองใหม่อีกครั้ง", 
                    ephemeral=True
                )
            except:
                # Interaction might have already been responded to
                pass

# ปุ่มลงทะเบียน
class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # ปุ่มไม่หมดอายุ
    
    @discord.ui.button(label="ลงทะเบียนที่นี่", style=discord.ButtonStyle.primary, emoji="📝")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # เปิดแบบฟอร์มลงทะเบียน
        await interaction.response.send_modal(RegistrationForm())

# Modal สำหรับกรอกเหตุผลการปฏิเสธ
class RejectReasonModal(ui.Modal, title="เหตุผลการปฏิเสธ"):
    reason = ui.TextInput(
        label="กรุณาระบุเหตุผลการปฏิเสธ",
        placeholder="ตัวอย่าง: ข้อมูล Steam ID ไม่ถูกต้อง, ข้อมูลอาชีพไม่ครบถ้วน...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view
    
    async def on_submit(self, interaction: discord.Interaction):
        # ตรวจสอบว่ามีเหตุผลหรือไม่
        if not self.reason.value.strip():
            await interaction.response.send_message("กรุณากรอกเหตุผลการปฏิเสธ", ephemeral=True)
            return
        
        # ดำเนินการปฏิเสธพร้อมเหตุผล
        await interaction.response.defer(ephemeral=True)
        await self.original_view.perform_reject_with_reason(interaction, self.reason.value)

# ปุ่มสำหรับทีมงานยืนยันการอนุมัติหรือปฏิเสธ
class ConfirmActionView(discord.ui.View):
    def __init__(self, original_view, action_type="approve"):
        super().__init__(timeout=60)  # timeout หลังจาก 60 วินาที
        self.original_view = original_view
        self.action_type = action_type  # "approve" หรือ "reject"
    
    @discord.ui.button(label="ยืนยัน", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("คุณไม่มีสิทธิ์ในการดำเนินการนี้", ephemeral=True)
            return
        
        # ดำเนินการตามประเภทการกระทำ
        if self.action_type == "approve":
            await self.original_view.perform_approve(interaction)
        else:
            # สำหรับการปฏิเสธ ให้เปิด Modal เพื่อกรอกเหตุผล
            await interaction.response.send_modal(RejectReasonModal(self.original_view))
    
    @discord.ui.button(label="ยกเลิก", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("คุณไม่มีสิทธิ์ในการดำเนินการนี้", ephemeral=True)
            return
        
        # ยกเลิกและกลับไปยังปุ่มเดิม
        await interaction.response.edit_message(view=self.original_view)
        await interaction.followup.send("ยกเลิกการดำเนินการแล้ว", ephemeral=True)

# ปุ่มสำหรับทีมงานอนุมัติหรือปฏิเสธ
class AdminActionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)  # ปุ่มไม่หมดอายุ
        self.user_id = user_id
    
    @discord.ui.button(label="อนุมัติ", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("คุณไม่มีสิทธิ์ในการดำเนินการนี้", ephemeral=True)
            return
        
        # แสดงข้อความยืนยันการอนุมัติ
        confirm_view = ConfirmActionView(self, "approve")
        await interaction.response.edit_message(
            content=f"คุณแน่ใจหรือไม่ที่จะอนุมัติการลงทะเบียนของ <@{self.user_id}>?",
            view=confirm_view
        )
    
    @discord.ui.button(label="ปฏิเสธ", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("คุณไม่มีสิทธิ์ในการดำเนินการนี้", ephemeral=True)
            return
        
        # แสดง Modal สำหรับกรอกเหตุผลโดยตรง โดยไม่ต้องผ่าน ConfirmActionView ก่อน
        await interaction.response.send_modal(RejectReasonModal(self))
    
    # ฟังก์ชันสำหรับดำเนินการอนุมัติหลังจากยืนยันแล้ว
    async def perform_approve(self, interaction):
        """อนุมัติผู้ใช้และแสดงข้อมูลอีกครั้งก่อนลบ"""
        registrations = load_registrations()
        user_id_str = str(self.user_id)
        
        if user_id_str in registrations:
            user_data = registrations[user_id_str]
            
            # ให้บทบาทกับผู้ใช้
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            
            if member:
                auto_role = guild.get_role(AUTOROLE_ID)
                player_role = guild.get_role(PLAYER_ROLE_ID)
                if player_role:
                    try:
                        # ลบ Auto Role ออกก่อน
                        if auto_role:
                            await member.remove_roles(auto_role)
                        
                        # จากนั้นเพิ่ม Player Role
                        await member.add_roles(player_role)
                        
                        # สร้าง embed สำหรับแสดงข้อมูลที่อนุมัติ
                        approved_embed = discord.Embed(
                            title="✅ การลงทะเบียนได้รับการอนุมัติ",
                            description=f"ข้อมูลการลงทะเบียนของ {member.mention}",
                            color=discord.Color.green(),
                            timestamp=datetime.now()
                        )
                        approved_embed.add_field(name="ชื่อในเกม", value=user_data['in_game_name'], inline=False)
                        approved_embed.add_field(name="Steam ID", value=user_data['steam_id'], inline=False)
                        approved_embed.add_field(name="อาชีพที่สนใจ", value=user_data['profession'], inline=False)
                        approved_embed.add_field(name="วิธีหาทอง", value=user_data['gold_methods'], inline=False)
                        approved_embed.add_field(name="โซนต้องห้าม", value=user_data['server_rules'], inline=False)
                        approved_embed.set_footer(text=f"อนุมัติโดย {interaction.user.display_name}")
                        
                        # แจ้งเตือนผู้ใช้ว่าได้รับการอนุมัติ
                        try:
                            await member.send(
                                "ยินดีด้วย! คำขอลงทะเบียนของคุณได้รับการอนุมัติแล้ว\n"
                                "คุณสามารถเข้าร่วมเซิร์ฟเวอร์ได้ทันที https://discord.com/channels/1360583634481975327/1374821568839942258 ",
                                embed=approved_embed
                            )
                        except:
                            pass  # อาจไม่สามารถส่งข้อความส่วนตัวได้
                        
                        # ส่งข้อมูลที่อนุมัติไปยังช่องแอดมินก่อนลบ
                        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
                        if admin_channel:
                            await admin_channel.send(
                                f"✅ การลงทะเบียนของ {member.mention} ได้รับการอนุมัติโดย {interaction.user.mention}",
                                embed=approved_embed
                            )
                        
                        # ลบข้อมูลออกจากไฟล์
                        del registrations[user_id_str]
                        save_registrations(registrations)
                        
                        # ลบข้อความรอยืนยันเดิม
                        await interaction.message.delete()
                        
                        await interaction.response.send_message("อนุมัติผู้ใช้เรียบร้อยแล้ว", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)
                else:
                    await interaction.response.send_message("ไม่พบบทบาทผู้เล่น โปรดตรวจสอบการตั้งค่า", ephemeral=True)
            else:
                await interaction.response.send_message("ไม่พบผู้ใช้ในเซิร์ฟเวอร์", ephemeral=True)
        else:
            await interaction.response.send_message("ไม่พบข้อมูลการลงทะเบียนของผู้ใช้นี้", ephemeral=True)
    
    # ฟังก์ชันสำหรับดำเนินการปฏิเสธหลังจากยืนยันแล้ว (พร้อมเหตุผล)
    async def perform_reject_with_reason(self, interaction, reason):
        """ปฏิเสธผู้ใช้พร้อมเหตุผลและลบข้อมูลเก่า"""
        registrations = load_registrations()
        user_id_str = str(self.user_id)
        
        if user_id_str in registrations:
            # แจ้งเตือนผู้ใช้ว่าถูกปฏิเสธพร้อมเหตุผล
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            
            if member:
                try:
                    reject_embed = discord.Embed(
                        title="❌ การลงทะเบียนไม่ได้รับการอนุมัติ",
                        description="ขออภัย คำขอลงทะเบียนของคุณไม่ได้รับการอนุมัติ",
                        color=discord.Color.red()
                    )
                    reject_embed.add_field(
                        name="เหตุผล",
                        value=reason,
                        inline=False
                    )
                    reject_embed.add_field(
                        name="ข้อแนะนำ",
                        value="กรุณาแก้ไขตามเหตุผลข้างต้นและส่งแบบฟอร์มลงทะเบียนใหม่ที่ช่อง <#1361242784509726791>",
                        inline=False
                    )
                    
                    await member.send(embed=reject_embed)
                except discord.Forbidden:
                    # ไม่สามารถส่ง DM ให้ผู้ใช้ได้
                    pass
            
            # ลบข้อมูลออกจากไฟล์
            del registrations[user_id_str]
            save_registrations(registrations)
            
            # สร้าง embed สำหรับแสดงเหตุผลการปฏิเสธ
            reject_info_embed = discord.Embed(
                title="❌ การลงทะเบียนถูกปฏิเสธ",
                description=f"การลงทะเบียนของ <@{self.user_id}> ถูกปฏิเสธโดย {interaction.user.mention}",
                color=discord.Color.red()
            )
            reject_info_embed.add_field(
                name="เหตุผลการปฏิเสธ",
                value=reason,
                inline=False
            )
            
            # ปรับปรุงข้อความทีมงาน
            try:
                await interaction.message.edit(
                    content="",
                    embed=reject_info_embed,
                    view=None
                )
                await interaction.followup.send("ปฏิเสธผู้ใช้เรียบร้อยแล้ว และส่งเหตุผลให้ผู้ใช้แล้ว", ephemeral=True)
            except Exception as e:
                print(f"Error updating rejection message: {e}")
        else:
            await interaction.followup.send("ไม่พบข้อมูลการลงทะเบียนของผู้ใช้นี้", ephemeral=True)    

@bot.event
async def on_ready():
    """เรียกเมื่อบอทเริ่มทำงานและพร้อมใช้งาน"""
    print(f'{bot.user.name} พร้อมใช้งานแล้ว!')
    
    # เริ่มงานในเบื้องหลังสำหรับ sync สถานะบอท (backup)
    bot_status_sync_task.start()
    
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
                "โปรดอ่าน https://discord.com/channels/1360583634481975327/1364640491647537272 \n"
                "โปรดอ่าน https://discord.com/channels/1360583634481975327/1361289410804580372 \n"
                "กรุณาลงทะเบียนเพื่อเข้าร่วมเซิร์ฟเวอร์ของเรา โดยคลิกที่ปุ่ม 'ลงทะเบียนที่นี่' ด้านล่าง\n"
                "หลังจากลงทะเบียนแล้ว ทีมงานจะตรวจสอบข้อมูลของคุณและอนุมัติคำขอโดยเร็วที่สุด"
            ),
            color=discord.Color.blue()
        )
        
        await register_channel.send(embed=embed, view=RegisterButton())
    
    # สร้างข้อความสถานะบอทเมื่อบอทเริ่มทำงาน
    for guild in bot.guilds:
        # สร้าง cache เริ่มต้นและแสดงสถานะ
        update_bot_status_cache(guild)
        await update_bot_status_message(guild, force_update=True)

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
    if role is None:
        # ถ้าไม่ระบุ Role จะแสดง Role ปัจจุบัน
        current_role = ctx.guild.get_role(AUTOROLE_ID)
        if current_role:
            await ctx.send(f"Auto Role ปัจจุบันคือ: {current_role.mention}")
        else:
            await ctx.send("ไม่ได้ตั้งค่า Auto Role")
        return
    
    # สร้างหรือโหลดไฟล์การตั้งค่า
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    # อัปเดตค่า AUTOROLE_ID
    config['AUTOROLE_ID'] = role.id
    
    # บันทึกการตั้งค่า
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    # อัปเดตค่า AUTOROLE_ID โดยใช้ตัวแปรที่ประกาศเป็น global ไว้แล้วตั้งแต่ต้น
    AUTOROLE_ID = role.id
    
    await ctx.send(f"ตั้งค่า Auto Role เป็น {role.mention} สำเร็จ")

# เพิ่มคำสั่งสำหรับตั้งค่า Admin Role
@bot.command()
@commands.has_permissions(administrator=True)
async def setadminrole(ctx, role: discord.Role = None):
    """ตั้งค่า Admin Role ที่จะถูก mention เมื่อมีการลงทะเบียนใหม่"""
    if role is None:
        # ถ้าไม่ระบุ Role จะแสดง Role ปัจจุบัน
        current_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        if current_role:
            await ctx.send(f"Admin Role ปัจจุบันคือ: {current_role.mention}")
        else:
            await ctx.send("ไม่ได้ตั้งค่า Admin Role")
        return
    
    # สร้างหรือโหลดไฟล์การตั้งค่า
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    # อัปเดตค่า ADMIN_ROLE_ID
    config['ADMIN_ROLE_ID'] = role.id
    
    # บันทึกการตั้งค่า
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    # อัปเดตค่า ADMIN_ROLE_ID โดยใช้ตัวแปรที่ประกาศเป็น global ไว้แล้วตั้งแต่ต้น
    ADMIN_ROLE_ID = role.id
    
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

@bot.command(name="botstatus", aliases=["botsstatus", "botsonline"])
async def bot_status(ctx, bot_name: str = None):
    """แสดงสถานะออนไลน์ของบอทอื่นๆ ในเซิร์ฟเวอร์"""
    # รวบรวมบอททั้งหมดในเซิร์ฟเวอร์
    bots = [member for member in ctx.guild.members if member.bot]
    
    if bot_name:
        # ค้นหาบอทตามชื่อที่ระบุ (ค้นหาแบบไม่คำนึงถึงตัวพิมพ์ใหญ่-เล็ก)
        filtered_bots = [bot for bot in bots if bot_name.lower() in bot.name.lower() or bot_name.lower() in bot.display_name.lower()]
        if not filtered_bots:
            await ctx.send(f"ไม่พบบอทที่มีชื่อว่า '{bot_name}'")
            return
        bots = filtered_bots
    
    # ถ้าไม่มีบอทในเซิร์ฟเวอร์
    if not bots:
        await ctx.send("ไม่พบบอทในเซิร์ฟเวอร์นี้")
        return
    
    # สร้าง embed สำหรับแสดงสถานะบอท
    embed = discord.Embed(
        title="📊 ข้อมูลเซิร์ฟเวอร์",
        description=f"พบบอททั้งหมด {len(bots)} ตัว",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # แยกบอทตามสถานะ
    online_bots = []
    offline_bots = []
    
    for bot in bots:
        if bot.status == discord.Status.offline or bot.status is None:
            offline_bots.append(bot)
        else:
            online_bots.append(bot)
    
    # เรียงลำดับบอทแต่ละกลุ่มตามชื่อ
    online_bots.sort(key=lambda b: b.name.lower())
    offline_bots.sort(key=lambda b: b.name.lower())
    
    # เพิ่มหัวข้อสำหรับบอทออนไลน์
    if online_bots:
        embed.add_field(
            name="🟢 บอทที่ออนไลน์",
            value="บอทต่อไปนี้กำลังทำงานอยู่",
            inline=False
        )
        
        # เพิ่มข้อมูลบอทออนไลน์
        for bot in online_bots:
            # ไอคอนสำหรับแต่ละสถานะ
            status_icons = {
                discord.Status.online: "🟢 ออนไลน์",
                discord.Status.idle: "🟡 ไม่อยู่",
                discord.Status.dnd: "🔴 ห้ามรบกวน",
                None: "🟢 ออนไลน์"  # กรณีไม่สามารถตรวจจับสถานะได้ แต่รู้ว่าไม่ได้ออฟไลน์
            }
            
            status_text = status_icons.get(bot.status, "🟢 ออนไลน์")
            
            # ตรวจสอบกิจกรรมของบอท
            activity_text = ""
            if bot.activity:
                activity_type = {
                    discord.ActivityType.playing: "กำลังเล่น",
                    discord.ActivityType.streaming: "กำลังสตรีม",
                    discord.ActivityType.listening: "กำลังฟัง",
                    discord.ActivityType.watching: "กำลังดู",
                    discord.ActivityType.custom: "",
                    discord.ActivityType.competing: "กำลังแข่งขัน"
                }.get(bot.activity.type, "")
                
                if activity_type:
                    activity_text = f"{activity_type} {bot.activity.name}"
                elif isinstance(bot.activity, discord.CustomActivity) and bot.activity.name:
                    activity_text = bot.activity.name
            
            # สร้างข้อความสถานะ
            status_display = status_text
            if activity_text:
                status_display += f" | {activity_text}"
            
            embed.add_field(
                name=f"{bot.display_name}",
                value=status_display,
                inline=False
            )
    
    # เพิ่มหัวข้อสำหรับบอทออฟไลน์
    if offline_bots:
        embed.add_field(
            name="⚫ บอทที่ออฟไลน์",
            value="บอทต่อไปนี้ไม่ได้ทำงานอยู่",
            inline=False
        )
        
        # เพิ่มข้อมูลบอทออฟไลน์
        for bot in offline_bots:
            embed.add_field(
                name=f"{bot.display_name}",
                value="⚫ ออฟไลน์",
                inline=False
            )
    
    # เพิ่ม Server Info หลังจากแสดงสถานะบอท
    embed.add_field(
        name="IP และ Password",
        value="# **IP:** ```79.127.213.68:7082```\n# **Password:** ```PlayerIsPrisoner```",
        inline=False
    )
    
    # ลบ footer timestamp ออก
    
    await ctx.send(embed=embed)

@bot.command(name="botinfo")
async def bot_info(ctx, *, bot_name: str):
    """แสดงข้อมูลละเอียดของบอทที่ระบุ"""
    # ค้นหาบอทตามชื่อ
    found_bots = []
    for member in ctx.guild.members:
        if member.bot and (bot_name.lower() in member.name.lower() or bot_name.lower() in member.display_name.lower()):
            found_bots.append(member)
    
    if not found_bots:
        await ctx.send(f"ไม่พบบอทที่มีชื่อว่า '{bot_name}'")
        return
    
    # ถ้าพบหลายบอท ให้แสดงบอทแรกที่พบ
    target_bot = found_bots[0]
    
    # สร้าง embed สำหรับแสดงข้อมูลบอท
    embed = discord.Embed(
        title=f"ข้อมูลบอท: {target_bot.display_name}",
        color=target_bot.color,
        timestamp=datetime.now()
    )
    
    # เพิ่มรูปโปรไฟล์ของบอท
    if target_bot.avatar:
        embed.set_thumbnail(url=target_bot.avatar.url)
    
    # สถานะออนไลน์
    status_icons = {
        discord.Status.online: "🟢 ออนไลน์",
        discord.Status.idle: "🟡 ไม่อยู่",
        discord.Status.dnd: "🔴 ห้ามรบกวน",
        discord.Status.offline: "⚫ ออฟไลน์",
        discord.Status.invisible: "⚪ ซ่อนตัว",
        None: "⚫ ไม่ทราบสถานะ"
    }
    embed.add_field(name="สถานะ", value=status_icons.get(target_bot.status, status_icons[None]), inline=True)
    
    # ไอดีของบอท
    embed.add_field(name="ID", value=target_bot.id, inline=True)
    
    # วันที่เข้าร่วมเซิร์ฟเวอร์
    joined_at = target_bot.joined_at.strftime("%Y-%m-%d %H:%M:%S") if target_bot.joined_at else "ไม่ทราบ"
    embed.add_field(name="เข้าร่วมเมื่อ", value=joined_at, inline=True)
    
    # วันที่สร้างบัญชี
    created_at = target_bot.created_at.strftime("%Y-%m-%d %H:%M:%S") if target_bot.created_at else "ไม่ทราบ"
    embed.add_field(name="สร้างเมื่อ", value=created_at, inline=True)
    
    # กิจกรรมปัจจุบัน
    activity_text = "ไม่มีกิจกรรม"
    if target_bot.activity:
        activity_type = {
            discord.ActivityType.playing: "กำลังเล่น",
            discord.ActivityType.streaming: "กำลังสตรีม",
            discord.ActivityType.listening: "กำลังฟัง",
            discord.ActivityType.watching: "กำลังดู",
            discord.ActivityType.custom: "",
            discord.ActivityType.competing: "กำลังแข่งขัน"
        }.get(target_bot.activity.type, "")
        
        if activity_type:
            activity_text = f"{activity_type} {target_bot.activity.name}"
        elif isinstance(target_bot.activity, discord.CustomActivity) and target_bot.activity.name:
            activity_text = target_bot.activity.name
    
    embed.add_field(name="กิจกรรม", value=activity_text, inline=True)
    
    # บทบาททั้งหมด
    roles = [role.mention for role in target_bot.roles if role.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "ไม่มีบทบาท"
    embed.add_field(name="บทบาท", value=roles_text, inline=False)
    
    await ctx.send(embed=embed)

# งานหลักตอนเริ่มบอท
load_config()
keep_alive()

bot.run(os.getenv('discordkey'))