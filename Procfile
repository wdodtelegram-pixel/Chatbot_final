# Procfile — used by Railway (Nixpacks), Heroku, and similar buildpack platforms.
#
# "worker" (not "web") is deliberate: this bot uses long-polling and opens NO
# HTTP port. If declared as "web", the platform waits for the bot to bind a
# port, never sees one, and kills it as a failed health check. "worker" tells
# the platform "this is a background process, just keep it alive".
worker: python bot.py
