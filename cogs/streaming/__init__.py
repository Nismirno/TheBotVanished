from .streaming import Streaming


def setup(bot):
    bot.add_cog(Streaming(bot))
