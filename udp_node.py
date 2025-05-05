import socket
import threading
import time
import base64
import os
import hashlib
import argparse
from pending_message import PendingMessage
from device_info import DeviceInfo
from message_handler import MessageHandler

HEARTBEAT_INTERVAL = 5
DEVICE_TIMEOUT = 10
CLEANUP_INTERVAL = 2
RESEND_INTERVAL = 2
PORT = 11000
MAX_RETRY = 5 #maximo numero de tentativas de reenvio
message_counter = 0

class UdpNode:
    def __init__(self, device_name, listen_port=11000, dest_ip="255.255.255.255", dest_port=11000): #dest_port é só para caso queira falar entre processos diretamente (tem que mudar a porta padrão tmb)
        self.device_name = device_name
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.active_devices = {}
        self.pending_messages = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', listen_port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.lock = threading.Lock()

    def start(self, dest_ip, listen_port):
        threading.Thread(target=self.listen_loop, daemon=True).start()
        self._schedule(lambda: self.send_heartbeat(dest_ip, listen_port), HEARTBEAT_INTERVAL)
        self._schedule(self.cleanup_inactive_devices, CLEANUP_INTERVAL)
        self._schedule(self.resend_pending_messages, RESEND_INTERVAL)
        self.send_heartbeat(dest_ip, listen_port)
        self.console_loop()
        
    def listen_loop(self):
        while True:
            data, addr = self.socket.recvfrom(8192)
            message = data.decode('utf-8')
            sender_ip, sender_port = addr
            MessageHandler.handle_message(message, sender_ip, sender_port, self)

    def send_udp(self, message, dest_ip, dest_port):
        self.socket.sendto(message.encode('utf-8'), (dest_ip, dest_port))

    def send_heartbeat(self, dest_ip, listen_port):
        msg = f"HEARTBEAT {self.device_name}"
        self.send_udp(msg, dest_ip, listen_port)

    def cleanup_inactive_devices(self):
        now = time.time()
        with self.lock:
            to_remove = [name for name, info in self.active_devices.items()
                         if now - info.last_heartbeat > DEVICE_TIMEOUT]
            for name in to_remove:
                print(f">>> [INFO] Dispositivo inativo removido: {name}")
                del self.active_devices[name]

    def resend_pending_messages(self):
        now = time.time()
        for pm_id, pm in list(self.pending_messages.items()):
            if pm.acknowledged:
                continue
            if now - pm.last_sent > 3:
                if pm.retries >= MAX_RETRY:  #depois de 5 tentativas, joga o erro e desiste
                    print(f"[ERRO] Falha ao enviar mensagem ID={pm.id} após múltiplas tentativas")
                    del self.pending_messages[pm_id]
                    continue
                print(f"[RETX] Reenviando ID={pm.id} (tentativa {pm.retries + 1})")
                self.send_udp(pm.message, pm.dest_ip, pm.dest_port)
                pm.update_last_sent()
                pm.retries += 1

    def console_loop(self):
        while True:
            line = input("> ").strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            cmd = parts[0].lower()
            if cmd == "devices":
                self.list_devices()
            elif cmd == "talk":
                if len(parts) > 1:
                    try:
                        target, msg = parts[1].split(" ", 1)
                        self.send_talk(target, msg)
                    except ValueError:
                        print("Uso: talk <nome> <mensagem>")
                else:
                    print("Uso: talk <nome> <mensagem>")
            elif cmd == "sendfile":
                if len(parts) > 1:
                    try:
                        target, path = parts[1].split(" ", 1)
                        self.send_file(target, path)
                    except ValueError:
                        print("Uso: sendfile <nome> <caminho-arquivo>")
                else:
                    print("Uso: sendfile <nome> <caminho-arquivo>")
            else:
                print("Comando não reconhecido:", cmd)
                print("Comandos disponíveis: devices, talk, sendfile")

    def list_devices(self):
        print("=== Dispositivos Ativos ===")
        now = time.time()
        for info in self.active_devices.values():
            diff = now - info.last_heartbeat
            print(f"* {info.name} - {info.ip}:{info.port} (último heartbeat há {int(diff * 1000)} ms)")
        print("===========================")

    def send_talk(self, target_name, content):
        info = self.active_devices.get(target_name)
        if not info:
            print("[ERRO] Dispositivo não encontrado:", target_name)
            return
        msg_id = self._generate_message_id()
        msg = f"TALK {msg_id} {content}"
        self.pending_messages[msg_id] = PendingMessage(msg_id, msg, info.ip, info.port)
        self.send_udp(msg, info.ip, info.port)

    def send_file(self, target_name, file_path):
        info = self.active_devices.get(target_name)
        if not info:
            print("[ERRO] Dispositivo não encontrado:", target_name)
            return
        if not os.path.isfile(file_path):
            print("[ERRO] Arquivo não encontrado:", file_path)
            return

        msg_id = self._generate_message_id()
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        header = f"FILE {msg_id} {file_name} {file_size}"
        self.pending_messages[msg_id] = PendingMessage(msg_id, header, info.ip, info.port)
        self.send_udp(header, info.ip, info.port)

        with open(file_path, 'rb') as f:
            seq = 0
            while chunk := f.read(1024):
                seq += 1
                base64_data = base64.b64encode(chunk).decode('utf-8')
                chunk_msg = f"CHUNK {msg_id} {seq} {base64_data}"
                chunk_id = f"{msg_id}-seq{seq}"
                self.pending_messages[chunk_id] = PendingMessage(chunk_id, chunk_msg, info.ip, info.port)
                self.send_udp(chunk_msg, info.ip, info.port)
                print(f"... enviado CHUNK seq={seq} ({len(chunk)} bytes)")

        with open(file_path, 'rb') as f:
            file_data = f.read()
        file_hash = hashlib.md5(file_data).hexdigest()

        end_msg = f"END {msg_id} {file_hash}"
        end_id = f"{msg_id}-end"
        self.pending_messages[end_id] = PendingMessage(end_id, end_msg, info.ip, info.port)
        self.send_udp(end_msg, info.ip, info.port)
        print(f">>> [END enviado] ID={msg_id}")

    def _schedule(self, func, interval):
        def wrapper():
            while True:
                func()
                time.sleep(interval)
        threading.Thread(target=wrapper, daemon=True).start()

    def _generate_message_id(self):
        global message_counter
        message_counter += 1
        return f"msg{message_counter}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="UDP Node")
    parser.add_argument("--name", required=True, help="Nome do dispositivo")
    parser.add_argument("--listen-port", type=int, default=11000, help="Porta de escuta")
    parser.add_argument("--dest-port", type=int, default=11000, help="Porta de destino")
    parser.add_argument("--dest-ip", default="255.255.255.255", help="Endereço IP de destino")
    args = parser.parse_args()

node = UdpNode(args.name, args.listen_port, args.dest_ip, args.dest_port)
node.start(args.dest_ip , args.listen_port)

