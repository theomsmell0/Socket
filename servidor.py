import socket
import os
import hashlib
import json
import logging

HOST = '127.0.0.1'
PORTA_CONTROLE = 8021
PORTA_DADOS = 8020
PASTA_SERVIDOR = 'pasta_servidor'
ARQUIVO_MESTRE = os.path.join(PASTA_SERVIDOR, 'config_master.json')

os.makedirs(PASTA_SERVIDOR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PASTA_SERVIDOR, "servidor.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

if not os.path.exists(ARQUIVO_MESTRE):
    with open(ARQUIVO_MESTRE, 'w') as f:
        json.dump({"versao": "1.0", "tema": "dark", "mensagem_boas_vindas": "SISTEMA INICIADO"}, f, indent=4)

def calcular_hash(caminho_arquivo):
    if not os.path.exists(caminho_arquivo): return None
    sha = hashlib.sha256()
    with open(caminho_arquivo, 'rb') as f:
        sha.update(f.read())
    return sha.hexdigest()

socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_controle.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# BIND: Associa o processo a uma interface de rede e porta
socket_controle.bind((HOST, PORTA_CONTROLE))
socket_controle.listen(1)

# TIMEOUT: O segredo para o servidor não ficar travado no accept()
# Ele vai esperar 1 segundo por conexões. Se não vier, ele dá uma volta no loop.
socket_controle.settimeout(1.0) 

logging.info(f"Servidor Iniciado. BIND realizado com sucesso em IP: {HOST} | Porta: {PORTA_CONTROLE}")
logging.info(f"Monitorando alterações no arquivo: {ARQUIVO_MESTRE}")

# Memória do servidor para saber quando VOCÊ alterou o arquivo no disco
ultimo_hash_servidor = calcular_hash(ARQUIVO_MESTRE)

while True:
    # 1. VERIFICAÇÃO ATIVA DO ARQUIVO LOCAL
    hash_atual_servidor = calcular_hash(ARQUIVO_MESTRE)
    if hash_atual_servidor != ultimo_hash_servidor:
        logging.info("=====================================================")
        logging.warning("[ALERTA] Arquivo config_master.json foi MODIFICADO no disco!")
        logging.info("Nova versão pronta para distribuição aos terminais.")
        logging.info("=====================================================")
        ultimo_hash_servidor = hash_atual_servidor

    # 2. AGUARDA CONEXÕES
    try:
        conn_ctrl, addr = socket_controle.accept()
    except socket.timeout:
        continue # Passou 1 segundo e ninguém conectou. Volta pro começo do loop silenciosamente.

    # 3. CLIENTE CONECTOU! Pega as informações de rede dele.
    ip_cliente, porta_cliente = addr
    logging.info(f"Nova conexão de controle -> IP Origem: {ip_cliente} | Porta Origem: {porta_cliente}")
    
    try:
        mensagem = conn_ctrl.recv(1024).decode()
        
        if mensagem.startswith("CHECK_CONF"):
            partes = mensagem.split()
            hash_cliente = partes[1] if len(partes) > 1 else None
            
            if ultimo_hash_servidor == hash_cliente:
                logging.info(f"[Cliente {porta_cliente}] Terminal já possui o hash {hash_cliente[:6]}... (Atualizado)")
                conn_ctrl.sendall(b"304 Not Modified")
            else:
                logging.info(f"[Cliente {porta_cliente}] Terminal desatualizado. Negociando porta de dados...")
                
                socket_dados = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                socket_dados.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                socket_dados.bind((HOST, PORTA_DADOS))
                socket_dados.listen(1)
                
                logging.info(f"[Cliente {porta_cliente}] BIND Temporário realizado na porta de DADOS {PORTA_DADOS}")
                conn_ctrl.sendall(f"150 ACCEPTED PORT {PORTA_DADOS}".encode())
                
                conn_dados, addr_dados = socket_dados.accept()
                logging.info(f"Conexão de DADOS estabelecida com -> Porta Origem: {addr_dados[1]}. Enviando arquivo...")
                
                with open(ARQUIVO_MESTRE, 'rb') as f:
                    conn_dados.sendall(f.read())
                        
                conn_dados.close()
                socket_dados.close() 
                
                conn_ctrl.sendall(b"226 Transfer Complete")
                logging.info(f"[Cliente {porta_cliente}] Arquivo transferido. Conexões encerradas.")

    except Exception as e:
        logging.error(f"Erro na comunicação com {ip_cliente}:{porta_cliente} - {e}")
    finally:
        conn_ctrl.close()