import socket
import time
import random

HOST = '127.0.0.1'
PORTA = 8021

# Arsenal de mensagens lixo para testar o servidor
mensagens_troll = [
    "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n", # Simulando um navegador web perdido
    "CHECK_CONFIG abcdef12345",                  # Simulando um erro de digitação (CONFIG em vez de CONF)
    "DROP TABLE usuarios;",                      # Simulando uma tentativa (ingênua) de SQL Injection
    "SYNC_ME_NOW",                               # Comando que não existe
    "A" * 1000                                   # Simulando um buffer overflow (texto gigante)
]

print("=== INICIANDO ATAQUE DE FUZZING (TROLL) ===")

while True:
    try:
        # Cria o socket e conecta na porta de controle do servidor
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORTA))
        
        # Escolhe um lixo aleatório
        msg = random.choice(mensagens_troll)
        print(f"[->] Mandando lixo: {msg[:30]}...")
        
        # Envia para o servidor
        s.sendall(msg.encode())
        
        # Opcional: Espera para ver a bronca que o servidor vai dar
        resposta = s.recv(1024).decode()
        print(f"[<-] Servidor respondeu: {resposta}\n")
        
        s.close()
        
    except ConnectionRefusedError:
        print("Servidor está offline. Aguardando...")
    except Exception as e:
        print(f"Erro no Troll: {e}")
        
    # Espera 2 segundos para você conseguir ler os logs com calma
    time.sleep(2)