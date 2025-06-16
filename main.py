import discord
import os
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
    1361305826798604440: "ผู้พิทักษ์",
    1361303692766216313: "อันธพาล", 
    1361303934563778751: "เพลงดาบทมิฬ",
    1361304137979002991: "เสียงกรีดร้อง",
    1361304383345918022: "แสงยานุภาพ",
    1361304546068005064: "สายธาร",
    1361304712061648908: "มุมมืด",
    1361304887253667921: "เปลวเพลิง",
    1361305463718936616: "สายฟ้า",
    1361305165336150096: "สายลม",
    1361305687103111238: "ปากท้อง",
    1361306017438109808: "ฟันเฟือง",
    1361306190868516897: "เมล็ดพันธุ์",
    1361306485409190061: "นักตกปลา",
    1361306651054968994: "แสงสีทอง"
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
        title=f"🎓 อาชีพ: {profession_name}\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B\u200B",
        color=role.color if role.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.now()
    )
    # เพิ่มบรรทัดนี้เพื่อแสดง role icon
    if role.display_icon:
        embed.set_thumbnail(url=role.display_icon.url)
    if role.members:
        member_list = []
        for member in role.members:
            # ใช้วันที่เข้าร่วมเซิร์ฟเวอร์เป็นข้อมูลอ้างอิง
            join_date = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "ไม่ทราบ"
            
            # รูปแบบการแสดงผล: Avatar + ชื่อ + วันที่
            member_info = f"{member.mention} • **{member.display_name}** • `{join_date}`"
            member_list.append(member_info)
        
        # แบ่งรายชื่อเป็นหลายฟิลด์ถ้ามีมากเกินไป
        if len(member_list) <= 15:
            embed.add_field(
                name=f" 📗 รายชื่อสมาชิก ({len(member_list)} คน)",
                value="\n".join(member_list),
                inline=False
            )
        else:
            # แบ่งเป็นหลายฟิลด์
            for i in range(0, len(member_list), 15):
                chunk = member_list[i:i+15]
                field_name = f"👥 สมาชิก ({i+1}-{min(i+15, len(member_list))})"
                embed.add_field(
                    name=field_name,
                    value="\n".join(chunk),
                    inline=False
                )
    else:
        embed.add_field(
            name="👥 สมาชิก",
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