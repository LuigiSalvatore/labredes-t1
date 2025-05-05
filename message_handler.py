from device_info import DeviceInfo
import hashlib
import base64
import os

received_chunks = {}  #dict para armazenar a parte recebida do arquivo

class MessageHandler:
    @staticmethod
    def handle_message(message, sender_ip, sender_port, udp_node):
        parts = message.strip().split(" ", 3)
        if not parts:
            return

        cmd = parts[0]

        if cmd == "HEARTBEAT" and len(parts) > 1:
            name = parts[1]
            if name not in udp_node.active_devices:
                udp_node.active_devices[name] = DeviceInfo(name, sender_ip, sender_port)
            else:
                udp_node.active_devices[name].update_heartbeat()
            #print(f"[INFO] HEARTBEAT de {name}")

        elif cmd == "TALK" and len(parts) >= 3:
            msg_id = parts[1]
            data = " ".join(parts[2:]) # Mensagem pode conter espaços / multiplas palavras
            print(f"[TALK recebido de {sender_ip}] {data}")
            udp_node.send_udp(f"ACK {msg_id}", sender_ip, sender_port)

        elif cmd == "ACK" and len(parts) >= 2:
            ack_id = parts[1]
            if ack_id in udp_node.pending_messages:
                udp_node.pending_messages[ack_id].acknowledged = True
                del udp_node.pending_messages[ack_id]
                print(f"[ACK recebido] {ack_id}")

        elif cmd == "FILE" and len(parts) >= 4:
            msg_id, filename, filesize = parts[1], parts[2], int(parts[3])
            print(f"[FILE recebido] {filename} ({filesize} bytes)")
            received_chunks[msg_id] = {"chunks": {}, "filename": filename, "filesize": filesize, "last_seq": 0}
            udp_node.send_udp(f"ACK {msg_id}", sender_ip, sender_port)

        elif cmd == "CHUNK" and len(parts) >= 4:
            msg_id, seq, b64data = parts[1], int(parts[2]), parts[3]
            chunk_data = base64.b64decode(b64data.encode('utf-8'))
            if msg_id in received_chunks:
                file_entry = received_chunks[msg_id]
                if seq in file_entry["chunks"]:
                    print(f"[DUPLICADO] CHUNK {seq} já recebido, descartado")
                    return  #ignora duplicata

                if seq != file_entry["last_seq"] + 1:
                    udp_node.send_udp(f"NACK {msg_id} fora_de_ordem_esperado_{file_entry['last_seq'] + 1}_recebido_{seq}", sender_ip, sender_port)
                    print(f"[NACK enviado] CHUNK fora de ordem: esperado {file_entry['last_seq'] + 1}, recebido {seq}")
                    return

                file_entry["chunks"][seq] = chunk_data
                file_entry["last_seq"] = seq
                udp_node.send_udp(f"ACK {msg_id}-seq{seq}", sender_ip, sender_port)

        elif cmd == "END" and len(parts) >= 3:
            msg_id, received_hash = parts[1], parts[2]
            if msg_id in received_chunks:
                chunks = received_chunks[msg_id]["chunks"]
                ordered = [chunks[i] for i in sorted(chunks)]
                data = b"".join(ordered)
                local_hash = hashlib.md5(data).hexdigest()
                if local_hash == received_hash:
                    filename = received_chunks[msg_id]["filename"]
                    with open(f"recv_{filename}", "wb") as f:
                        f.write(data)
                    udp_node.send_udp(f"ACK {msg_id}", sender_ip, sender_port)
                    print(f"[Arquivo salvo como recv_{filename}]")
                else:
                    udp_node.send_udp(f"NACK {msg_id} hash_invalido", sender_ip, sender_port)
                    print("[NACK enviado] Hash inválido no arquivo recebido")
                del received_chunks[msg_id]

        elif cmd == "NACK" and len(parts) >= 3:
            print(f"[NACK recebido] ID={parts[1]} Motivo={parts[2]}")
