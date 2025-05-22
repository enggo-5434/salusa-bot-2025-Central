import discord
import os
from discord.ext import commands, tasks
from myserver import keep_alive
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import json
from discord import ui
from datetime import datetime

# Configure intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Channel and role IDs
WELCOME_CHANNEL_ID = 1372511440786817075  
REGISTER_CHANNEL_ID = 1361242784509726791 
ADMIN_CHANNEL_ID = 1361241867798446171
BOT_STATUS_CHANNEL_ID = 1374821568839942258 
AUTOROLE_ID = 1361182119069749310  
PLAYER_ROLE_ID = 1361186568416657593
ADMIN_ROLE_ID = 1361241867798446171
BANNER_TEMPLATE = "welcome_SalusaBG2.png"  
REGISTRATIONS_FILE = "registrations.json"  
CONFIG_FILE = "config.json"

# Load registration data
def load_registrations():
    try:
        with open(REGISTRATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save registration data
def save_registrations(data):
    with open(REGISTRATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Load config 
def load_config():
    global AUTOROLE_ID, ADMIN_ROLE_ID, BOT_STATUS_CHANNEL_ID
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            AUTOROLE_ID = config.get('AUTOROLE_ID', AUTOROLE_ID)
            ADMIN_ROLE_ID = config.get('ADMIN_ROLE_ID', ADMIN_ROLE_ID)
            BOT_STATUS_CHANNEL_ID = config.get('BOT_STATUS_CHANNEL_ID', BOT_STATUS_CHANNEL_ID)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

# Generate bot status embed
async def generate_bot_status_embed(guild):
    """Generate an embed showing the status of all bots in the server"""
    bots = [member for member in guild.members if member.bot]
    
    if not bots:
        embed = discord.Embed(
            title="📊 Bot Status in Server",
            description="No bots found in this server",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        return embed
    
    embed = discord.Embed(
        title="📊 Bot Status in Server",
        description=f"Found {len(bots)} bots",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    status_icons = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline",
        discord.Status.invisible: "⚪ Invisible",
        None: "⚫ Unknown"
    }
    
    # Separate bots by status
    online_bots = []
    offline_bots = []
    
    for bot in bots:
        if bot.status == discord.Status.offline or bot.status is None:
            offline_bots.append(bot)
        else:
            online_bots.append(bot)
    
    # Sort bots by name
    online_bots.sort(key=lambda b: b.name.lower())
    offline_bots.sort(key=lambda b: b.name.lower())
    
    # Add online bots section
    if online_bots:
        embed.add_field(
            name="🟢 Online Bots",
            value="These bots are currently active:",
            inline=False
        )
        
        for bot in online_bots:
            status_text = status_icons.get(bot.status, "🟢 Online")
            
            activity_text = ""
            if bot.activity:
                activity_type = {
                    discord.ActivityType.playing: "Playing",
                    discord.ActivityType.streaming: "Streaming",
                    discord.ActivityType.listening: "Listening to",
                    discord.ActivityType.watching: "Watching",
                    discord.ActivityType.custom: "",
                    discord.ActivityType.competing: "Competing in"
                }.get(bot.activity.type, "")
                
                if activity_type:
                    activity_text = f"{activity_type} {bot.activity.name}"
                elif isinstance(bot.activity, discord.CustomActivity) and bot.activity.name:
                    activity_text = bot.activity.name
            
            status_display = status_text
            if activity_text:
                status_display += f" | {activity_text}"
            
            embed.add_field(
                name=f"{bot.display_name}",
                value=status_display,
                inline=False
            )
    
    # Add offline bots section
    if offline_bots:
        embed.add_field(
            name="⚫ Offline Bots",
            value="These bots are currently inactive:",
            inline=False
        )
        
        for bot in offline_bots:
            embed.add_field(
                name=f"{bot.display_name}",
                value="⚫ Offline",
                inline=False
            )
    
    embed.set_footer(text=f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    return embed

# Update bot status message
async def update_bot_status_message(guild):
    """Update the bot status message in the designated channel"""
    channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
    if not channel:
        print(f"Bot status channel not found (ID: {BOT_STATUS_CHANNEL_ID})")
        return
    
    # Check for existing status message
    status_message = None
    async for message in channel.history(limit=50):
        if message.author == bot.user and message.embeds and "Bot Status" in message.embeds[0].title:
            status_message = message
            break
    
    # Create new embed
    embed = await generate_bot_status_embed(guild)
    
    # Update or send new message
    if status_message:
        await status_message.edit(embed=embed)
    else:
        await channel.send(embed=embed)

# Background task to update bot status
@tasks.loop(minutes=2)
async def bot_status_task():
    """Background task to periodically update bot status"""
    for guild in bot.guilds:
        await update_bot_status_message(guild)

@bot_status_task.before_loop
async def before_bot_status_task():
    await bot.wait_until_ready()

# Registration Form Modal
class RegistrationForm(ui.Modal, title="ลงทะเบียนผู้เล่น"):
    in_game_name = ui.TextInput(label="In-Game Name", placeholder="กรุณากรอกชื่อในเกม", required=True)
    steam_id = ui.TextInput(label="Steam ID", placeholder="กรุณากรอก Steam ID", required=True)
    profession = ui.TextInput(label="อาชีพใดที่คุณสนใจใน SALUSA", placeholder="กรุณากรอกอาชีพที่คุณสนใจ", required=True)
    gold_methods = ui.TextInput(label="คุณสามารถหาทองได้จากวิธีใดบ้าง", placeholder="ซื้อจากตลาดหุ้น", required=True)
    server_rules = ui.TextInput(label="จะเกิดอะไรขึ้นหากคุณจอดรถไว้ในพื้นที่ต้องห้าม", placeholder="ได้รับเงิน 3000 SD", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
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
            
            registrations = load_registrations()
            
            if str(interaction.user.id) in registrations:
                update_message = "Your registration information has been updated! Staff will review it shortly."
            else:
                update_message = "Thank you for registering! Staff will review your information shortly."
                
            registrations[str(interaction.user.id)] = user_data
            save_registrations(registrations)
            
            await interaction.response.send_message(update_message, ephemeral=True)
            
            # Notify admin channel
            admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                embed = discord.Embed(
                    title="New Registration",
                    description=f"User {interaction.user.mention} has submitted a registration",
                    color=discord.Color.blue()
                )
                embed.add_field(name="In-Game Name", value=self.in_game_name.value, inline=False)
                embed.add_field(name="Steam ID", value=self.steam_id.value, inline=False)
                embed.add_field(name="Preferred Profession", value=self.profession.value, inline=False)
                embed.add_field(name="Gold Methods", value=self.gold_methods.value, inline=False)
                embed.add_field(name="Restricted Zone", value=self.server_rules.value, inline=False)
                
                view = AdminActionView(interaction.user.id)
                admin_role_mention = f"<@&{ADMIN_ROLE_ID}>"
                await admin_channel.send(
                    f"{admin_role_mention} New registration awaiting approval!", 
                    embed=embed, 
                    view=view
                )
        
        except Exception as e:
            print(f"Registration error: {str(e)}")
            try:
                await interaction.response.send_message(
                    "An error occurred during registration. Please try again.", 
                    ephemeral=True
                )
            except:
                pass

# Register Button
class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Register Here", style=discord.ButtonStyle.primary, emoji="📝")
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegistrationForm())

# Admin Action Buttons
class AdminActionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("You don't have permission for this action", ephemeral=True)
            return
        
        confirm_view = ConfirmActionView(self, "approve")
        await interaction.response.edit_message(
            content=f"Are you sure you want to approve the registration for <@{self.user_id}>?",
            view=confirm_view
        )
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("You don't have permission for this action", ephemeral=True)
            return
        
        confirm_view = ConfirmActionView(self, "reject")
        await interaction.response.edit_message(
            content=f"Are you sure you want to reject the registration for <@{self.user_id}>?",
            view=confirm_view
        )
    
    async def perform_approve(self, interaction):
        registrations = load_registrations()
        user_id_str = str(self.user_id)
        
        if user_id_str in registrations:
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            
            if member:
                auto_role = guild.get_role(AUTOROLE_ID)
                player_role = guild.get_role(PLAYER_ROLE_ID)
                if player_role:
                    try:
                        if auto_role:
                            await member.remove_roles(auto_role)
                        
                        await member.add_roles(player_role)
                        
                        try:
                            await member.send("Congratulations! Your registration has been approved. You can now access the server.")
                        except:
                            pass
                        
                        del registrations[user_id_str]
                        save_registrations(registrations)
                        
                        await interaction.message.edit(
                            content=f"✅ Registration for <@{self.user_id}> approved by {interaction.user.mention}",
                            embed=interaction.message.embeds[0],
                            view=None
                        )
                        await interaction.response.send_message("User approved successfully", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
                else:
                    await interaction.response.send_message("Player role not found. Please check settings", ephemeral=True)
            else:
                await interaction.response.send_message("User not found in server", ephemeral=True)
        else:
            await interaction.response.send_message("Registration data not found for this user", ephemeral=True)
    
    async def perform_reject(self, interaction):
        registrations = load_registrations()
        user_id_str = str(self.user_id)
        
        if user_id_str in registrations:
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            
            if member:
                try:
                    await member.send("Sorry, your registration was not approved. Please contact staff for more information.")
                except:
                    pass
            
            del registrations[user_id_str]
            save_registrations(registrations)
            
            await interaction.message.edit(
                content=f"❌ Registration for <@{self.user_id}> rejected by {interaction.user.mention}",
                embed=interaction.message.embeds[0],
                view=None
            )
            await interaction.response.send_message("User rejected successfully", ephemeral=True)
        else:
            await interaction.response.send_message("Registration data not found for this user", ephemeral=True)

# Confirmation View
class ConfirmActionView(discord.ui.View):
    def __init__(self, original_view, action_type="approve"):
        super().__init__(timeout=60)
        self.original_view = original_view
        self.action_type = action_type
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("You don't have permission for this action", ephemeral=True)
            return
        
        if self.action_type == "approve":
            await self.original_view.perform_approve(interaction)
        else:
            await self.original_view.perform_reject(interaction)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.permissions.administrator:
            await interaction.response.send_message("You don't have permission for this action", ephemeral=True)
            return
        
        await interaction.response.edit_message(view=self.original_view)
        await interaction.followup.send("Action cancelled", ephemeral=True)

# Bot Events
@bot.event
async def on_ready():
    print(f'{bot.user.name} is ready!')
    
    # Start background tasks
    bot_status_task.start()
    
    # Setup registration channel
    register_channel = bot.get_channel(REGISTER_CHANNEL_ID)
    if register_channel:
        async for message in register_channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()
        
        embed = discord.Embed(
            title="Register for SALUSA",
            description=(
                "Welcome to SALUSA server!\n"
                "Please read our rules first:\n"
                "https://discord.com/channels/1360583634481975327/1364640491647537272 \n"
                "https://discord.com/channels/1360583634481975327/1361289410804580372 \n"
                "Click the 'Register Here' button below to join our server\n"
                "After registration, our staff will review your information"
            ),
            color=discord.Color.blue()
        )
        
        await register_channel.send(embed=embed, view=RegisterButton())

@bot.event
async def on_member_join(member):
    try:
        autorole = member.guild.get_role(AUTOROLE_ID)
        if autorole:
            await member.add_roles(autorole)
            print(f"Added Auto Role to {member.name}")
        else:
            print(f"Auto Role not found (ID: {AUTOROLE_ID})")
    except Exception as e:
        print(f"Error adding Auto Role: {str(e)}")
    
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    
    if welcome_channel:
        welcome_banner = await create_welcome_banner(member)
        
        await welcome_channel.send(
            f"**Welcome {member.mention} to SALUSA!** 🎉\n"
            f"Please visit <#{REGISTER_CHANNEL_ID}> to register",
            file=welcome_banner
        )

async def create_welcome_banner(member):
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_response = requests.get(avatar_url)
    avatar_image = Image.open(BytesIO(avatar_response.content)).convert('RGBA')
    avatar_size = 255
    
    avatar_image = avatar_image.resize((avatar_size, avatar_size))
    
    mask = Image.new('L', (255, 255), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 255, 255), fill=255)
    
    try:
        template = Image.open(BANNER_TEMPLATE).convert('RGBA')
    except FileNotFoundError:
        template = Image.new('RGBA', (1024, 500), (47, 49, 54, 255))
        
    avatar_with_mask = Image.new('RGBA', (255, 255))
    avatar_with_mask.paste(avatar_image, (0, 0), mask)
    pos_x = 512 - (255 // 2)
    template.paste(avatar_with_mask, (pos_x, 70), avatar_with_mask)
    
    draw = ImageDraw.Draw(template)
    
    try:
        title_font = ImageFont.truetype("NotoSans-Regular.ttf", 48)
        user_font = ImageFont.truetype("NotoSans-Regular.ttf", 36)
        watermark_font = ImageFont.truetype("NotoSans-Regular.ttf", 10)
    except IOError:
        title_font = ImageFont.load_default()
        user_font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()
    
    draw.text((512, 365), "Welcome to SALUSA", fill=(255, 255, 255, 255), font=title_font, anchor="mm")
    draw.text((512, 420), f"{member.display_name}", fill=(230, 126, 32, 255), font=user_font, anchor="mm")
    
    watermark_text = "©2025 All Rights Reserved, Salusa"
    watermark_color = (255, 255, 255, 255) 
    watermark_y = template.height - 20  
    
    draw.text((512, watermark_y), watermark_text, fill=watermark_color, font=watermark_font, anchor="ms")
    
    buffer = BytesIO()
    template.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(buffer, filename='welcome.png')

# Bot Commands
@bot.command()
@commands.has_permissions(administrator=True)
async def setbotstatuschannel(ctx, channel: discord.TextChannel = None):
    """Set the channel for automatic bot status updates"""
    global BOT_STATUS_CHANNEL_ID
    if channel is None:
        current_channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
        if current_channel:
            await ctx.send(f"Current bot status channel: {current_channel.mention}")
        else:
            await ctx.send("No bot status channel set")
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    config['BOT_STATUS_CHANNEL_ID'] = channel.id
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    BOT_STATUS_CHANNEL_ID = channel.id
    await update_bot_status_message(ctx.guild)
    await ctx.send(f"Set bot status channel to {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def updatebotstatus(ctx):
    """Force update the bot status"""
    await ctx.send("Updating bot status...")
    await update_bot_status_message(ctx.guild)
    await ctx.send("Bot status updated")

@bot.command()
@commands.has_permissions(administrator=True)
async def setautorole(ctx, role: discord.Role = None):
    """Set the role to be automatically given to new members"""
    if role is None:
        current_role = ctx.guild.get_role(AUTOROLE_ID)
        if current_role:
            await ctx.send(f"Current auto role: {current_role.mention}")
        else:
            await ctx.send("No auto role set")
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    config['AUTOROLE_ID'] = role.id
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    AUTOROLE_ID = role.id
    await ctx.send(f"Auto role set to {role.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setadminrole(ctx, role: discord.Role = None):
    """Set the admin role to be mentioned for new registrations"""
    if role is None:
        current_role = ctx.guild.get_role(ADMIN_ROLE_ID)
        if current_role:
            await ctx.send(f"Current admin role: {current_role.mention}")
        else:
            await ctx.send("No admin role set")
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    config['ADMIN_ROLE_ID'] = role.id
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    ADMIN_ROLE_ID = role.id
    await ctx.send(f"Admin role set to {role.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def registrations(ctx):
    """Show pending registration requests"""
    registrations_data = load_registrations()
    
    if not registrations_data:
        await ctx.send("No pending registration requests")
        return
    
    embed = discord.Embed(
        title="Pending Registration Requests",
        color=discord.Color.blue()
    )
    
    for user_id, data in registrations_data.items():
        embed.add_field(
            name=f"User: {data['username']}",
            value=f"In-Game Name: {data['in_game_name']}\nSteam ID: {data['steam_id']}\nRegistration Date: {data['timestamp']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="botstatus", aliases=["botsstatus", "botsonline"])
async def bot_status(ctx, bot_name: str = None):
    """Show online status of bots in the server"""
    bots = [member for member in ctx.guild.members if member.bot]
    
    if bot_name:
        filtered_bots = [bot for bot in bots if bot_name.lower() in bot.name.lower() or bot_name.lower() in bot.display_name.lower()]
        if not filtered_bots:
            await ctx.send(f"No bot found with name '{bot_name}'")
            return
        bots = filtered_bots
    
    if not bots:
        await ctx.send("No bots found in this server")
        return
    
    embed = await generate_bot_status_embed(ctx.guild)
    await ctx.send(embed=embed)

@bot.command(name="botinfo")
async def bot_info(ctx, *, bot_name: str):
    """Show detailed information about a specific bot"""
    found_bots = []
    for member in ctx.guild.members:
        if member.bot and (bot_name.lower() in member.name.lower() or bot_name.lower() in member.display_name.lower()):
            found_bots.append(member)
    
    if not found_bots:
        await ctx.send(f"No bot found with name '{bot_name}'")
        return
    
    target_bot = found_bots[0]
    
    embed = discord.Embed(
        title=f"Bot Info: {target_bot.display_name}",
        color=target_bot.color,
        timestamp=datetime.now()
    )
    
    if target_bot.avatar:
        embed.set_thumbnail(url=target_bot.avatar.url)
    
    status_icons = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline",
        discord.Status.invisible: "⚪ Invisible",
        None: "⚫ Unknown"
    }
    embed.add_field(name="Status", value=status_icons.get(target_bot.status, status_icons[None]), inline=True)
    embed.add_field(name="ID", value=target_bot.id, inline=True)
    
    joined_at = target_bot.joined_at.strftime("%Y-%m-%d %H:%M:%S") if target_bot.joined_at else "Unknown"
    embed.add_field(name="Joined", value=joined_at, inline=True)
    
    created_at = target_bot.created_at.strftime("%Y-%m-%d %H:%M:%S") if target_bot.created_at else "Unknown"
    embed.add_field(name="Created", value=created_at, inline=True)
    
    activity_text = "No activity"
    if target_bot.activity:
        activity_type = {
            discord.ActivityType.playing: "Playing",
            discord.ActivityType.streaming: "Streaming",
            discord.ActivityType.listening: "Listening to",
            discord.ActivityType.watching: "Watching",
            discord.ActivityType.custom: "",
            discord.ActivityType.competing: "Competing in"
        }.get(target_bot.activity.type, "")
        
        if activity_type:
            activity_text = f"{activity_type} {target_bot.activity.name}"
        elif isinstance(target_bot.activity, discord.CustomActivity) and target_bot.activity.name:
            activity_text = target_bot.activity.name
    
    embed.add_field(name="Activity", value=activity_text, inline=True)
    
    roles = [role.mention for role in target_bot.roles if role.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "No roles"
    embed.add_field(name="Roles", value=roles_text, inline=False)
    
    await ctx.send(embed=embed)

# Start the bot
load_config()
keep_alive()
bot.run(os.getenv('discordkey'))