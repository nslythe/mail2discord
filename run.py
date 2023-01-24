import mail2discord
import signal
import logging
import time

stop = False
def handler(signum, frame):
    logging.info(f"Received signal STOPPING")
    global stop
    stop = True


def main():
    signal.signal(signal.SIGINT, handler)
    config = mail2discord.ConfigFile()
    server = mail2discord.mail2discordServer(config)
    server.start()

    while not stop:
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            logging.info(f"KeyboardInterrupt STOPPING")
            break

    server.stop()
    server.join()
    

if __name__ == "__main__":
    main()
