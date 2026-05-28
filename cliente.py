import socket
import hashlib
import os
import json
import time
import sys 
import logging

HOST = '127.0.0.1'
PORTA_CONTROLE = 8021
PORTA_DADOS = 8020

nome_terminal = sys.argv[1] if len(sys.argv) > 1 else "Terminal_Generico"
PASTA_LOCAL = f"pasta_{nome_terminal}"

os.makedirs(PASTA_LOCAL, exist_ok=True)
ARQUIVO_LOCAL = os.path.join(PASTA_LOCAL, 'config_master.json')
ARQUIVO_LOG = os.path.join(PASTA_LOCAL, 'cliente.log')

# --- FORMATO DE LOG ALINHADO COM O SERVIDOR ---
logging.basicConfig(
    filename=ARQUIVO_LOG,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    encoding='utf-8'
)

def calcular_hash(caminho_arquivo):
    if not os.path.exists(caminho_arquivo): return None
    sha = hashlib.sha256()
    with open(caminho_arquivo, 'rb') as f:
        sha.update(f.read())
    return sha.hexdigest()

def aplicar_tema(caminho_arquivo_json):
    try:
        with open(caminho_arquivo_json, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logging.error(f"[FILE_IO] Falha na decodificação do artefato JSON: {e}")
        return

    temas = {
        "dark": "\033[0;37;40m", "light": "\033[0;30;47m", "matrix": "\033[1;32;40m",  
        "hacker": "\033[1;31;40m", "ocean": "\033[1;36;44m", "alerta": "\033[1;33;41m"   
    }
    
    tema_escolhido = config.get("tema", "dark")
    cor_ansi = temas.get(tema_escolhido, temas["dark"])
    msg = config.get("mensagem_boas_vindas", "Terminal Pronto.")

    os.system('cls' if os.name == 'nt' else 'clear')
    print(cor_ansi, end="") 
    
    print("\n")
    if config.get("exibir_cabecalho", True):
        print("=" * 60)
        print(f" {msg} ".center(60, "="))
        print("=" * 60)
    
    print(f"\n[INFO] Terminal: {nome_terminal}")
    print(f"[INFO] Versão da Configuração: {config.get('versao', 'Desconhecida')}")
    print(f"[INFO] Tema Ativo: {tema_escolhido.upper()}")
    print("\n> Aguardando novas ordens da central...\n")
    
    logging.info(f"[SYSTEM]  Interface recarregada. Parâmetros aplicados -> Tema: {tema_escolhido.upper()} | Versão: {config.get('versao', 'N/A')}")

logging.info(f"=== INICIALIZAÇÃO DO NÓ: {nome_terminal} ===")

if os.path.exists(ARQUIVO_LOCAL):
    logging.info(f"[FILE_IO] Artefato local localizado em {ARQUIVO_LOCAL}")
    aplicar_tema(ARQUIVO_LOCAL)
else:
    logging.warning("[FILE_IO] Nenhum artefato local encontrado. Entrando em estado de bootstrap.")
    print(f"[{nome_terminal}] Iniciado. Buscando primeira configuração...")

while True:
    hash_atual = calcular_hash(ARQUIVO_LOCAL)
    hash_envio = hash_atual if hash_atual else "VAZIO"
    
    modo_autonomo = False
    if hash_atual: 
        try:
            with open(ARQUIVO_LOCAL, 'r', encoding='utf-8') as f:
                config_local = json.load(f)
                modo_autonomo = config_local.get("modo_autonomo", False)
        except Exception:
            pass 

    try:
        socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_controle.connect((HOST, PORTA_CONTROLE))
        
        _, minha_porta_efemera = socket_controle.getsockname()
        logging.info(f"[NETWORK] Sessão de controle estabelecida (Local Port: {minha_porta_efemera}) -> tcp://{HOST}:{PORTA_CONTROLE}")

        if modo_autonomo:
            comando = f"KEEP_LOCAL {hash_envio}"
            logging.info(f"[SYNC]    Modo Autônomo ativo. Solicitando isenção de deploy.")
        else:
            comando = f"CHECK_CONF {hash_envio}"
            logging.info(f"[SYNC]    Iniciando sondagem de integridade. Referência: {hash_envio[:8]}...")
            
        socket_controle.sendall(comando.encode())
        logging.info(f"[PROTOCOL] TX -> {comando}")

        resposta = socket_controle.recv(1024).decode()
        logging.info(f"[PROTOCOL] RX <- {resposta}")
        
        if "150" in resposta:
            logging.info(f"[NETWORK] Estabelecendo via de recepção secundária (Porta {PORTA_DADOS})...")
            socket_dados = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_dados.connect((HOST, PORTA_DADOS))
            
            bytes_recebidos = 0
            with open(ARQUIVO_LOCAL, 'wb') as f:
                while True:
                    dados = socket_dados.recv(4096)
                    if not dados: 
                        break
                    f.write(dados)
                    bytes_recebidos += len(dados)
                    
            socket_dados.close() 
            socket_controle.recv(1024).decode()
            
            logging.info(f"[FILE_IO] Download concluído. Payload recebido: {bytes_recebidos} bytes.")
            aplicar_tema(ARQUIVO_LOCAL)
            
        elif "200" in resposta:
            logging.info("[SYNC]    Isenção confirmada pelo servidor. Estado de operação local mantido.")
            
        elif "304" in resposta:
            logging.info("[SYNC]    Terminal sincronizado com o servidor mestre. Nenhuma ação requerida.")
            
        else:
            logging.warning(f"[PROTOCOL] Resposta não padronizada do servidor: {resposta}")

    except ConnectionRefusedError:
        logging.error("[NETWORK] Falha na sondagem. O servidor mestre encontra-se inalcançável no momento.")
    except Exception as e:
        logging.critical(f"[SYSTEM]  Falha crítica de execução no laço de polling: {e}")
    finally:
        socket_controle.close()
        logging.info("[SESSION] Recursos de socket liberados. Entrando em repouso dinâmico.\n")
                
    time.sleep(5)