import discord
from discord.ext import commands

class MemberNotifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1308016533426933790

    async def send_notification(self, message: str):
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            await channel.send(message)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        msg = f"{member.mention} joined the server. Let’s welcome them here!"
        await self.send_notification(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        msg = f"{member.mention} left the server. Goodbye ~"
        await self.send_notification(msg)

async def setup(bot):
    await bot.add_cog(MemberNotifyCog(bot))
