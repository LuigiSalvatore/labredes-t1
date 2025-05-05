import time

class PendingMessage:
    def __init__(self, id, message, dest_ip, dest_port):
        self.id = id
        self.message = message
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.last_sent = time.time()
        self.acknowledged = False
        self.retries = 0  

    def update_last_sent(self):
        self.last_sent = time.time()
