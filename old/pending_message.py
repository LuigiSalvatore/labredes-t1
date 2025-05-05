# Classe que representa uma mensagem pendente a ser reenviada
import time

class PendingMessage:
    def __init__(self, msg_id, message, dest_ip, dest_port):
        self.id = msg_id                 # ID da mensagem, ex: "msg1" ou "file1-seq2"
        self.message = message          # Texto completo da mensagem
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.last_sent = time.time()    # Timestamp do último envio

    def update_last_sent(self):
        self.last_sent = time.time()
