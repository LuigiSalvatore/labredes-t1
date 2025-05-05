import time

class DeviceInfo:
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port    
        self.last_heartbeat = time.time()

    def update_heartbeat(self):
        self.last_heartbeat = time.time()
