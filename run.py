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
import urllib
import hashlib

#todo support encryption

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class Config:
    avatar_size = 20
    avatar_default = "https://www.interstatedevelopment.com/wp-content/uploads/2019/04/generic-avatar-1-300x273.jpg"

    def get_mentions(self, to_list):
        raise NotImplementedError
        
    def get_avatar_url(self, email):
        raise NotImplementedError

    def get_webhook_url(self, to_list):
        raise NotImplementedError


class ConfigFile(Config):
    def __init__(self):
        if os.path.isfile("/config/config.yaml"):
            with open("/config/config.yaml", 'r') as stream:
                self.data = yaml.safe_load(stream)
        elif os.path.isfile("config.yaml"):
            with open("config.yaml", 'r') as stream:
                self.data = yaml.safe_load(stream)
        logger.info(f"Config loaded: {self.data}")

    def get_mentions(self, to_list):
        return_value = []
        for to in to_list:
            if "mappings" in self.data and to in self.data["mappings"]:
                if "mentions" in self.data["mappings"][to]:
                    for m in self.data["mappings"][to]["mentions"]:
                        return_value.append("<@" + str(m) + ">")
            return return_value
        
    def get_avatar_url(self, email):
        avatar_url = "https://www.gravatar.com/avatar/" + hashlib.md5(email.lower().encode("utf-8")).hexdigest() + "?"
        avatar_url += urllib.parse.urlencode({'d':Config.avatar_default, 's':str(Config.avatar_size)})
        return avatar_url

    def get_webhook_url(self, to_list):
        return_value = []
        for to in to_list:
            if "url" in self.data["mappings"][to]:
                return_value.append(self.data["mappings"][to]["url"])
        return return_value
    
    def get_project_url(self):
        return "https://github.com/nslythe/mail2discord"


class mail2discordServer:
    class CustomSMTPHandler:
        def __init__(self, queue):
            self.queue = queue

        async def handle_DATA(self, server, session, envelope):
            self.queue.put(envelope)
            return '250 OK'

    def __init__(self, config):
        self.config = config
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
                email_content = body.get_content()

                mentions = self.config.get_mentions(envelope.rcpt_tos)
                urls = self.config.get_webhook_url(envelope.rcpt_tos)
                avatar_url = self.config.get_avatar_url(envelope.mail_from)

                content = " ".join(mentions)+ " " + email_content + "\n"
                content += "Sent from : [mail2discord](" + self.config.get_project_url() + ")"

                embed = DiscordEmbed(title=message.get("Subject"), description=content)
                embed.set_author(name=envelope.mail_from, url=self.config.get_project_url(), icon_url=avatar_url)
                for w in DiscordWebhook.create_batch(urls=urls, username=envelope.mail_from, avatar_url=avatar_url , rate_limit_retry=True):
                    w.add_embed(embed)
                    response = w.execute()

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

config = ConfigFile()
server = mail2discordServer(config)
server.start()

while not stop:
    try:
        time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info(f"KeyboardInterrupt STOPPING")
        break

server.stop()
server.join()