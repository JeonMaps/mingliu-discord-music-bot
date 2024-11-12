import discord
from discord.ext import commands
import yt_dlp
import asyncio
import imageio_ffmpeg as ffmpeg

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

ffmpeg_path = ffmpeg.get_ffmpeg_exe()

FFMPEG_OPTIONS = {
    'executable': ffmpeg_path, 'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.guild_states = {}

    def get_guild_state(self, guild_id):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {
                'queue': []
            }
        return self.guild_states[guild_id]

    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You are not connected to a voice channel")
        if not ctx.voice_client:
            await voice_channel.connect()
            
        guild_state = self.get_guild_state(ctx.guild.id)

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info['title']
                guild_state['queue'].append((url, title))
                await ctx.send(f"Added {title} to the queue")
                print(f"Added {title} to the queue with URL: {url}") 
        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        guild_state = self.get_guild_state(ctx.guild.id)
        if guild_state['queue']:
            url, title = guild_state['queue'].pop(0)
            print(f"Attempting to play {title} from {url}")  # Debugging statement
            try:
                source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
                ctx.voice_client.play(source, after=lambda _: self.client.loop.create_task(self.play_next(ctx)))
                await ctx.send(f"Now playing {title}")
            except Exception as e:
                print(f"Error playing {title}: {e}")  # Debugging statement
                await ctx.send(f"Could not play {title}")
                await self.play_next(ctx)
        else:
            await ctx.send("Queue is empty")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected")

client = commands.Bot(command_prefix="-", intents=intents)

async def main():
    await client.add_cog(MusicBot(client))
    await client.start("DISCORD_TOKEN")

asyncio.run(main())