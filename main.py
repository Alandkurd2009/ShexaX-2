import discord
from discord.ext import commands
import asyncio
from datetime import timedelta

# Bot setup without prefix (commands trigger directly from text)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

# Database/Storage simulation (Resets when bot restarts)
# Note: For permanent storage, you'd eventually want a real database like SQLite.
SWEAR_WORDS = ["badword1", "badword2", "swear3"] # Add forbidden words here
ignored_channels = set()
gif_enabled_channels = set()
welcome_channels = {}
user_gifs = {}

@bot.event
async def on_ready():
    print(f'Bot is now online and running as: {bot.user.name}')

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author.bot:
        return

    msg_content = message.content.strip().lower()
    args = msg_content.split()
    
    if not args:
        return

    command = args[0]

    # --- SWEAR WORD FILTER ---
    if message.channel.id not in ignored_channels:
        if any(word in msg_content for word in SWEAR_WORDS):
            await message.delete()
            await message.channel.send(f"{message.author.mention}, please avoid using inappropriate language!", delete_after=3)
            return

    # ==========================================
    # MODERATION & ADMIN
    # ==========================================

    # ban [@user]
    if command == "ban" and message.author.guild_permissions.ban_members:
        if message.mentions:
            user = message.mentions[0]
            await user.ban(reason="Banned by bot command")
            await message.channel.send(f"✅ Successfully banned {user.name}.")

    # kick [@user]
    elif command == "kick" and message.author.guild_permissions.kick_members:
        if message.mentions:
            user = message.mentions[0]
            await user.kick(reason="Kicked by bot command")
            await message.channel.send(f"✅ Successfully kicked {user.name}.")

    # unban [username]
    elif command == "unban" and message.author.guild_permissions.ban_members:
        if len(args) > 1:
            name = args[1]
            bans = await message.guild.bans()
            for ban_entry in bans:
                if ban_entry.user.name == name:
                    await message.guild.unban(ban_entry.user)
                    await message.channel.send(f"✅ Successfully unbanned {name}.")
                    return
            await message.channel.send(f"❌ User '{name}' not found in ban list.")

    # m [@user] [time] (Timeout - e.g., 20m, 1d)
    elif command == "m" and message.author.guild_permissions.moderate_members:
        if message.mentions and len(args) > 2:
            user = message.mentions[0]
            time_str = args[2]
            
            # Simple duration parsing
            amount = int(time_str[:-1]) if time_str[:-1].isdigit() else 10
            unit = time_str[-1].lower()
            
            if unit == 'm':
                duration = timedelta(minutes=amount)
            elif unit == 'h':
                duration = timedelta(hours=amount)
            elif unit == 'd':
                duration = timedelta(days=amount)
            else:
                duration = timedelta(minutes=10) # default fallback
                
            await user.timeout(duration, reason="Timed out by bot command")
            await message.channel.send(f"✅ Timed out {user.name} for {amount}{unit}.")

    # um [@user] (Remove Timeout)
    elif command == "um" and message.author.guild_permissions.moderate_members:
        if message.mentions:
            user = message.mentions[0]
            await user.timeout(None)
            await message.channel.send(f"✅ Timeout removed for {user.name}.")

    # c [amount] (Clear messages)
    elif command == "c" and message.author.guild_permissions.manage_messages:
        amount = int(args[1]) + 1 if len(args) > 1 and args[1].isdigit() else 11
        await message.channel.purge(limit=amount)
        await message.channel.send(f"✅ Cleared {amount-1} messages.", delete_after=3)

    # dmall [text]
    elif command == "dmall" and message.author.guild_permissions.administrator:
        text = " ".join(args[1:])
        if text:
            await message.channel.send("⏳ Sending DM to everyone, please wait...")
            count = 0
            for member in message.guild.members:
                if not member.bot:
                    try:
                        await member.send(text)
                        count += 1
                    except:
                        pass
            await message.channel.send(f"✅ Broadcast finished. Sent successfully to {count} members.")

    # set_wel [#channel]
    elif command == "set_wel" and message.author.guild_permissions.manage_guild:
        if message.channel_mentions:
            welcome_channels[message.guild.id] = message.channel_mentions[0].id
            await message.channel.send(f"✅ Welcome logs channel mapped to: {message.channel_mentions[0].mention}")

    # ==========================================
    # CHANNEL SETTINGS
    # ==========================================

    # 1 (Lock Channel)
    elif command == "1" and message.author.guild_permissions.manage_channels:
        await message.channel.set_permissions(message.guild.default_role, send_messages=False)
        await message.channel.send("🔒 Channel locked. Typing permissions disabled for everyone.")

    # ul (Unlock Channel)
    elif command == "ul" and message.author.guild_permissions.manage_channels:
        await message.channel.set_permissions(message.guild.default_role, send_messages=None)
        await message.channel.send("🔓 Channel unlocked back to default.")

    # slowmode [seconds]
    elif command == "slowmode" and message.author.guild_permissions.manage_channels:
        seconds = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
        await message.channel.edit(slowmode_delay=seconds)
        await message.channel.send(f"⏱️ Slowmode updated. Delay set to {seconds} seconds.")

    # ignore-n
    elif command == "ignore-n" and message.author.guild_permissions.manage_channels:
        if message.channel.id in ignored_channels:
            ignored_channels.remove(message.channel.id)
            await message.channel.send("🚫 Swear word filter enabled for this channel.")
        else:
            ignored_channels.add(message.channel.id)
            await message.channel.send("✅ Swear word filter toggled off for this channel.")

    # ==========================================
    # ROLE MANAGEMENT
    # ==========================================

    # +role [@user] [role name]
    elif command == "+role" and message.author.guild_permissions.manage_roles:
        if message.mentions and len(args) > 2:
            user = message.mentions[0]
            role_name = " ".join(args[2:])
            role = discord.utils.get(message.guild.roles, name=role_name)
            if role:
                await user.add_roles(role)
                await message.channel.send(f"✅ Assigned the role **{role_name}** to {user.name}.")
            else:
                await message.channel.send(f"❌ Role **{role_name}** not found.")

    # -role [@user] [role name]
    elif command == "-role" and message.author.guild_permissions.manage_roles:
        if message.mentions and len(args) > 2:
            user = message.mentions[0]
            role_name = " ".join(args[2:])
            role = discord.utils.get(message.guild.roles, name=role_name)
            if role:
                await user.remove_roles(role)
                await message.channel.send(f"❌ Removed the role **{role_name}** from {user.name}.")
            else:
                await message.channel.send(f"❌ Role **{role_name}** not found.")

    # ==========================================
    # VOICE CHANNELS
    # ==========================================

    # join
    elif command == "join":
        if message.author.voice:
            channel = message.author.voice.channel
            await channel.connect()
            await message.channel.send(f"🔊 Joined voice channel: **{channel.name}**")
        else:
            await message.channel.send("❌ You need to be in a voice channel first!")

    # dec
    elif command == "dec":
        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.channel.send("🔇 Disconnected from voice channel.")
        else:
            await message.channel.send("❌ I am not connected to any voice channel.")

    # ==========================================
    # PROFILE & GIF ENGINE
    # ==========================================

    # gif
    elif command == "gif" and message.author.guild_permissions.manage_messages:
        if message.channel.id in gif_enabled_channels:
            gif_enabled_channels.remove(message.channel.id)
            await message.channel.send("🖼️ Automated GIF responses disabled in this channel.")
        else:
            gif_enabled_channels.add(message.channel.id)
            await message.channel.send("🖼️ Automated GIF responses enabled in this channel.")

    # setgif [url]
    elif command == "setgif" and len(args) > 1:
        user_gifs[message.author.id] = args[1]
        await message.channel.send("✅ Custom image/GIF URL successfully bound to your profile.")

    # ==========================================
    # GENERAL & STATS
    # ==========================================

    # t (XP Leaderboards Placeholder)
    elif command == "t":
        await message.channel.send("📊 **XP Leaderboard**\n1. User1 - 500 XP\n2. User2 - 450 XP\n*(Connect this to a real database to track stats)*")

    # ui [@user]
    elif command == "ui":
        user = message.mentions[0] if message.mentions else message.author
        embed = discord.Embed(title=f"User Info - {user.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Joined Server At", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Account Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        await message.channel.send(embed=embed)

    # si
    elif command == "si":
        embed = discord.Embed(title=f"Server Info - {message.guild.name}", color=discord.Color.green())
        embed.add_field(name="Total Members", value=str(message.guild.member_count), inline=True)
        embed.add_field(name="Channels Count", value=str(len(message.guild.channels)), inline=True)
        await message.channel.send(embed=embed)

    # av [@user]
    elif command == "av":
        user = message.mentions[0] if message.mentions else message.author
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        await message.channel.send(f"🖼️ **{user.name}'s Avatar:**\n{avatar_url}")

    # ping
    elif command == "ping":
        await message.channel.send(f"🏓 Pong! Active Latency: `{round(bot.latency * 1000)}ms`")

    # link
    elif command == "link":
        invite = await message.channel.create_invite(max_age=300)
        await message.channel.send(f"🔗 Primary server invite link (Expires in 5 mins): {invite}")

    # tb
    elif command == "tb" and message.reference:
        replied_msg = await message.channel.fetch_message(message.reference.message_id)
        owner = message.guild.owner
        if owner:
            try:
                await owner.send(f"⚠️ **Abuse Report** from {message.author.name}:\n**Message:** {replied_msg.content}\n**Sent by:** {replied_msg.author.name}")
                await message.channel.send("✅ Report forwarded directly to the server owner.")
            except:
                await message.channel.send("❌ Failed to DM the owner. Make sure their DMs are open.")

# Automatic Welcome Handler (Linked with set_wel)
@bot.event
async def on_member_join(member):
    if member.guild.id in welcome_channels:
        channel_id = welcome_channels[member.guild.id]
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(f"👋 Welcome {member.mention} to the server! We are glad to have you here.")

# Put your bot token here
bot.run(MTUwODM5MDg5Njg2ODI2NTk5NA.GHJZJ0.SoYweHGzrvgtnbddvmaVFoBAtNbdtFYbjOhwtw)
