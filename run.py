import aiosmtpd.controller
import email
import email.policy
from discord_webhook import DiscordWebhook, DiscordEmbed
import threading
import queue
import yaml

with open("config.yaml", 'r') as stream:
    config = yaml.safe_load(stream)

q = queue.Queue()

def discord_webhook_worker():
    while True:
        envelope = q.get()

        message = email.message_from_bytes(envelope.content, policy=email.policy.default)
        body = message.get_body(preferencelist=('plain', 'related', 'html'))
        content = body.get_content()

        mentions = []

        for to in envelope.rcpt_tos:
            if to in config["mappings"]:
                mentions.append("<@" + str(config["mappings"][to]) + ">")

        webhook = DiscordWebhook(url=config["url"], username=envelope.mail_from)
        embed = DiscordEmbed(title='Alert', description=" ".join(mentions)+ " " + content)
        webhook.add_embed(embed)
        response = webhook.execute()

        q.task_done()

class CustomSMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        q.put(envelope)
        return '250 OK'






threading.Thread(target=discord_webhook_worker, daemon=True).start()
handler = CustomSMTPHandler()
server = aiosmtpd.controller.Controller(handler, hostname="10.1.1.23", port=25)
server.start()
input("Server started. Press Return to quit.")
server.stop()