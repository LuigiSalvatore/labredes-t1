# Arquivo: device.py
import sys
from udp_node import UdpNode  # Assumindo que criaremos essa classe também em outro arquivo

def main():
    # Verifica se um argumento foi passado na linha de comando
    if len(sys.argv) < 2:
        print("Uso: python device.py <nome-do-dispositivo>")
        return

    # Lê o nome do dispositivo a partir dos argumentos
    my_name = sys.argv[1]

    # Cria uma instância do nó UDP
    node = UdpNode(my_name)

    try:
        # Inicia o nó
        node.start()
    except Exception as e:
        # Imprime qualquer erro que ocorra durante a execução
        print("Erro ao iniciar o nó:", e)

if __name__ == "__main__":
    main()
