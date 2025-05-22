# Replace the existing generate_bot_status_embed function with this updated version
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
    
    return embed

# Replace the existing bot_status command with this updated version
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
    
    # Add server IP and password information
    server_info = (
        "# __**IP:**__```79.127.213.68:7082```\n"
        "# __**Password:**__```PlayerIsPrisoner```"
    )
    await ctx.send(server_info)

# Add the new RejectionReasonModal class
class RejectionReasonModal(ui.Modal, title="เหตุผลการปฏิเสธการลงทะเบียน"):
    reason = ui.TextInput(
        label="กรุณาระบุเหตุผลการปฏิเสธ",
        style=discord.TextStyle.long,
        placeholder="เช่น ข้อมูลไม่ครบถ้วน, Steam ID ไม่ถูกต้อง, ฯลฯ",
        required=True
    )

    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    async def on_submit(self, interaction: discord.Interaction):
        await self.original_view.perform_reject_with_reason(interaction, self.reason.value)

# Replace the existing AdminActionView class with this updated version
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
        
        # Show rejection reason modal
        await interaction.response.send_modal(RejectionReasonModal(self))
    
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
    
    async def perform_reject_with_reason(self, interaction, reason):
        registrations = load_registrations()
        user_id_str = str(self.user_id)
        
        if user_id_str in registrations:
            guild = interaction.guild
            member = guild.get_member(self.user_id)
            
            if member:
                try:
                    rejection_message = (
                        "ขออภัย การลงทะเบียนของคุณไม่ได้รับการอนุมัติ\n\n"
                        f"**เหตุผล:** {reason}\n\n"
                        "คุณสามารถลงทะเบียนใหม่ได้ที่ช่องทางการลงทะเบียน"
                    )
                    await member.send(rejection_message)
                except:
                    pass
            
            # Delete old registration data
            if user_id_str in registrations:
                del registrations[user_id_str]
                save_registrations(registrations)
            
            await interaction.message.edit(
                content=(
                    f"❌ Registration for <@{self.user_id}> rejected by {interaction.user.mention}\n"
                    f"**เหตุผล:** {reason}"
                ),
                embed=interaction.message.embeds[0],
                view=None
            )
            await interaction.followup.send("User rejected successfully", ephemeral=True)
        else:
            await interaction.followup.send("Registration data not found for this user", ephemeral=True)