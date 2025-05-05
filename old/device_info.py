# Arquivo: device_info.py

class DeviceInfo:
    def __init__(self, name: str, ip: str, port: int, last_heartbeat: int):
        # Nome do dispositivo
        self._name = name

        # Endereço IP do dispositivo
        self._ip = ip

        # Porta utilizada para comunicação
        self._port = port

        # Último sinal de vida recebido (timestamp)
        self._last_heartbeat = last_heartbeat

    # Métodos de acesso (getters)
    def get_name(self) -> str:
        return self._name

    def get_ip(self) -> str:
        return self._ip

    def get_port(self) -> int:
        return self._port

    def get_last_heartbeat(self) -> int:
        return self._last_heartbeat

    # Método para atualizar o timestamp do último heartbeat
    def set_last_heartbeat(self, t: int):
        self._last_heartbeat = t
