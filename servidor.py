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
    format='%(asctime)s | %(levelname)-8s | %(message)s',
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

socket_controle.bind((HOST, PORTA_CONTROLE))
socket_controle.listen(1)
socket_controle.settimeout(1.0) 

# --- LOGS PROFISSIONAIS DE INICIALIZAÇÃO ---
logging.info("[SYSTEM]  Daemon de Provisionamento Inicializado.")
logging.info(f"[NETWORK] Control Socket BIND estabelecido -> tcp://{HOST}:{PORTA_CONTROLE}")
logging.info(f"[FILE_IO] Monitorando artefato principal: {ARQUIVO_MESTRE}")

ultimo_hash_servidor = calcular_hash(ARQUIVO_MESTRE)
logging.info(f"[SYNC]    Hash de referência carregado: {ultimo_hash_servidor[:8]}...")

while True:
    hash_atual_servidor = calcular_hash(ARQUIVO_MESTRE)
    if hash_atual_servidor != ultimo_hash_servidor:
        logging.warning("[FILE_IO] Mutação detectada no arquivo de configuração em disco.")
        logging.info(f"[SYNC]    Novo Hash de referência: {hash_atual_servidor[:8]}... Versão pronta para deploy.")
        ultimo_hash_servidor = hash_atual_servidor

    try:
        conn_ctrl, addr = socket_controle.accept()
    except socket.timeout:
        continue 

    ip_cliente, porta_cliente = addr
    id_sessao = f"{ip_cliente}:{porta_cliente}"
    logging.info(f"[SESSION] Nova conexão entrante estabelecida. Origem: {id_sessao}")
    
    try:
        mensagem = conn_ctrl.recv(1024).decode()
        logging.info(f"[PROTOCOL] RX ({id_sessao}) <- {mensagem[:30]}")
        
        if mensagem.startswith("CHECK_CONF"):
            partes = mensagem.split()
            hash_cliente = partes[1] if len(partes) > 1 else None
            
            if ultimo_hash_servidor == hash_cliente:
                logging.info(f"[SYNC]    Coerência de cache validada para {id_sessao}. Operação abortada.")
                conn_ctrl.sendall(b"304 Not Modified")
                logging.info(f"[PROTOCOL] TX ({id_sessao}) -> 304 Not Modified")
            else:
                logging.info(f"[SYNC]    Obsolescência detectada para {id_sessao}. Iniciando provisionamento.")
                
                socket_dados = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                socket_dados.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                socket_dados.bind((HOST, PORTA_DADOS))
                socket_dados.listen(1)
                
                logging.info(f"[NETWORK] Data Socket BIND temporário -> tcp://{HOST}:{PORTA_DADOS}")
                conn_ctrl.sendall(f"150 ACCEPTED PORT {PORTA_DADOS}".encode())
                logging.info(f"[PROTOCOL] TX ({id_sessao}) -> 150 ACCEPTED PORT {PORTA_DADOS}")
                
                conn_dados, addr_dados = socket_dados.accept()
                logging.info(f"[SESSION] Canal de DADOS aberto com sucesso. Origem: {addr_dados[0]}:{addr_dados[1]}")
                
                bytes_enviados = 0
                with open(ARQUIVO_MESTRE, 'rb') as f:
                    dados = f.read()
                    conn_dados.sendall(dados)
                    bytes_enviados = len(dados)
                        
                conn_dados.close()
                socket_dados.close() 
                
                logging.info(f"[FILE_IO] Transferência concluída. {bytes_enviados} bytes transmitidos.")
                conn_ctrl.sendall(b"226 Transfer Complete")
                logging.info(f"[PROTOCOL] TX ({id_sessao}) -> 226 Transfer Complete")

        elif mensagem.startswith("KEEP_LOCAL"):
            logging.info(f"[SYNC]    Diretiva de Autonomia de Nó recebida de {id_sessao}.")
            conn_ctrl.sendall(b"200 OK - Modo Local Mantido")
            logging.info(f"[PROTOCOL] TX ({id_sessao}) -> 200 OK")
            
        else:
            msg_segura = mensagem[:50] 
            logging.warning(f"[SECURITY] Vetor de dados malformado/anômalo recebido de {id_sessao}: '{msg_segura}'")
            conn_ctrl.sendall(b"400 Bad Request")
            logging.info(f"[PROTOCOL] TX ({id_sessao}) -> 400 Bad Request")
            
    except Exception as e:
        logging.error(f"[SYSTEM]  Exceção não tratada na sessão {id_sessao}: {e}")
    finally:
        conn_ctrl.close()
        logging.info(f"[SESSION] Conexão de controle encerrada para {id_sessao}.\n")