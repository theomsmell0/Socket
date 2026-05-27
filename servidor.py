import socket
import os
import hashlib
import json

HOST = '127.0.0.1'
PORTA_CONTROLE = 8021
PORTA_DADOS = 8020

# O Servidor agora é a fonte da verdade
PASTA_SERVIDOR = 'pasta_servidor'
ARQUIVO_MESTRE = os.path.join(PASTA_SERVIDOR, 'config_master.json')

os.makedirs(PASTA_SERVIDOR, exist_ok=True)

# Se não existir um JSON mestre, cria um genérico para o teste inicial
if not os.path.exists(ARQUIVO_MESTRE):
    with open(ARQUIVO_MESTRE, 'w') as f:
        json.dump({"versao": "1.0", "tema": "dark", "status": "operacional"}, f, indent=4)

def calcular_hash(caminho_arquivo):
    if not os.path.exists(caminho_arquivo): 
        return None
    sha = hashlib.sha256()
    with open(caminho_arquivo, 'rb') as f:
        sha.update(f.read())
    return sha.hexdigest()

# Configuração do Socket de Controle
socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_controle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket_controle.bind((HOST, PORTA_CONTROLE))
socket_controle.listen(1)

print(f"Servidor MESTRE Ativo. Distribuindo configurações na porta {PORTA_CONTROLE}...")

while True:
    conn_ctrl, addr = socket_controle.accept()
    mensagem = conn_ctrl.recv(1024).decode()
    
    # Novo Comando: Cliente pede para checar a configuração
    if mensagem.startswith("CHECK_CONF"):
        partes = mensagem.split()
        hash_cliente = partes[1] if len(partes) > 1 else None
        
        # Calcula o hash da configuração atual do servidor
        hash_servidor = calcular_hash(ARQUIVO_MESTRE)

        # Se o cliente já tem a mesma versão, avisa que não mudou
        if hash_servidor == hash_cliente:
            print(f"[{addr[1]}] Terminal já está atualizado.")
            conn_ctrl.sendall(b"304 Not Modified")
        
        # Se o cliente está desatualizado (ou não tem o arquivo)
        else:
            print(f"[{addr[1]}] Terminal desatualizado. Enviando nova config...")
            
            socket_dados = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_dados.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socket_dados.bind((HOST, PORTA_DADOS))
            socket_dados.listen(1)
            
            conn_ctrl.sendall(b"150 ACCEPTED PORT 8020")
            
            conn_dados, _ = socket_dados.accept()
            
            # O SERVIDOR AGORA LÊ E ENVIA (Inversão)
            with open(ARQUIVO_MESTRE, 'rb') as f:
                conn_dados.sendall(f.read())
                    
            conn_dados.close()
            socket_dados.close() 
            
            conn_ctrl.sendall(b"226 Transfer Complete")

    conn_ctrl.close()