import aiosmtpd.controller
import email
import email.policy
from discord_webhook import DiscordWebhook, DiscordEmbed
import threading
import queue
import yaml
import os
import signal
import time
import logging

#todo support encryption

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class mail2discordServer:
    class CustomSMTPHandler:
        def __init__(self, queue):
            self.queue = queue

        async def handle_DATA(self, server, session, envelope):
            self.queue.put(envelope)
            return '250 OK'

    def __init__(self):
        if os.path.isfile("/config/config.yaml"):
            with open("/config/config.yaml", 'r') as stream:
                self.config = yaml.safe_load(stream)
        elif os.path.isfile("config.yaml"):
            with open("config.yaml", 'r') as stream:
                self.config = yaml.safe_load(stream)

        logger.info(f"Config: {self.config}")

        self.__stop = False
        self.queue = queue.Queue()
        self.discord_thread = threading.Thread(target=self.discord_webhook_worker, daemon=False)
        self.handler = mail2discordServer.CustomSMTPHandler(self.queue)
        self.smtp_thread = aiosmtpd.controller.Controller(self.handler, hostname="", port=25)

    def discord_webhook_worker(self):
        while not self.__stop:
            try:
                envelope = self.queue.get(timeout = 1)
            except queue.Empty:
                envelope = None

            if envelope is not None:
                message = email.message_from_bytes(envelope.content, policy=email.policy.default)
                body = message.get_body(preferencelist=('plain', 'related', 'html'))
                content = body.get_content()

                mentions = []

                for to in envelope.rcpt_tos:
                    if "mappings" in self.config and to in self.config["mappings"]:
                        mentions.append("<@" + str(self.config["mappings"][to]) + ">")

                webhook = DiscordWebhook(url=self.config["url"], username=envelope.mail_from)
                embed = DiscordEmbed(title=message.get("Subject"), description=" ".join(mentions)+ " " + content)
                webhook.add_embed(embed)
                response = webhook.execute()

                self.queue.task_done()

    def start(self):
        self.smtp_thread.start()
        self.discord_thread.start()

    def stop(self):
        self.__stop = True
        self.smtp_thread.stop()

    def join(self):
        self.discord_thread.join()


stop = False
def handler(signum, frame):
    logger.info(f"Received signal STOPPING")
    global stop
    stop = True
signal.signal(signal.SIGINT, handler)

server = mail2discordServer()
server.start()

while not stop:
    try:
        time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info(f"KeyboardInterrupt STOPPING")
        break

server.stop()
server.join()