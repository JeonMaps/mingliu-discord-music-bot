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
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You are not connected to a voice channel")
        if not ctx.voice_client:
            await voice_channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info['title']
                self.queue.append((url, title))
                await ctx.send(f"Added {title} to the queue")
                print(f"Added {title} to the queue with URL: {url}") 
        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)
        self.reset_inactivity_timer(ctx)

    async def play_next(self, ctx):            
        if self.queue:
            url, title = self.queue.pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda _:self.client.loop.create_task(self.play_next(ctx)))
            await ctx.send(f"Now playing {title}")
        elif not ctx.voice_client.is_playing():
            await ctx.send("Queue is empty") 
        self.reset_inactivity_timer(ctx)

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped")
        self.reset_inactivity_timer(ctx)
            
    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused")
        self.reset_inactivity_timer(ctx)
    
    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed")
        self.reset_inactivity_timer(ctx)

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected due to inactivity")
        
    def reset_inactivity_timer(self, ctx):
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        self.inactivity_timer = self.client.loop.call_later(self.inactivity_timeout, lambda: self.client.loop.create_task(self.leave(ctx)))

client = commands.Bot(command_prefix="!", intents=intents)

async def main():
    await client.add_cog(MusicBot(client))
    await client.start("DISCORD_TOKEN")

asyncio.run(main())