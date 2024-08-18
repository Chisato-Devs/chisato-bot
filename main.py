from utils.basic import ChisatoBot
from utils.enviroment import env

bot: ChisatoBot = ChisatoBot(shard_count=1)

bot.load_cogs()
bot.run(env.TOKEN3)
