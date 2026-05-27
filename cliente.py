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

logging.basicConfig(
    filename=ARQUIVO_LOG,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
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
        logging.error(f"Erro ao ler JSON: {e}")
        return

    temas = {
        "dark": "\033[0;37;40m",    
        "light": "\033[0;30;47m",   
        "matrix": "\033[1;32;40m",  
        "hacker": "\033[1;31;40m",  
        "ocean": "\033[1;36;44m",   
        "alerta": "\033[1;33;41m"   
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
    
    logging.info(f"Interface atualizada no terminal. Tema aplicado: {tema_escolhido.upper()}")

logging.info(f"=== SESSÃO INICIADA: {nome_terminal} ===")

if os.path.exists(ARQUIVO_LOCAL):
    aplicar_tema(ARQUIVO_LOCAL)
else:
    print(f"[{nome_terminal}] Iniciado. Buscando primeira configuração...")

while True:
    hash_atual = calcular_hash(ARQUIVO_LOCAL)
    hash_envio = hash_atual if hash_atual else "VAZIO"
    
    try:
        socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_controle.connect((HOST, PORTA_CONTROLE))
        
        # INFORMAÇÃO DE REDE: Descobrindo qual porta o SO nos emprestou
        meu_ip, minha_porta_efemera = socket_controle.getsockname()
        logging.info(f"Conectado ao Servidor Controle ({HOST}:{PORTA_CONTROLE}) usando a porta local {minha_porta_efemera}")
        
        comando = f"CHECK_CONF {hash_envio}"
        socket_controle.sendall(comando.encode())
        
        resposta = socket_controle.recv(1024).decode()
        
        if "150" in resposta:
            logging.info(f"Iniciando conexão no Socket de DADOS (Porta {PORTA_DADOS})...")
            socket_dados = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_dados.connect((HOST, PORTA_DADOS))
            
            # Porta efêmera do canal de dados
            _, porta_dados_efemera = socket_dados.getsockname()
            logging.info(f"Socket de Dados estabelecido via porta local {porta_dados_efemera}. Recebendo arquivo...")
            
            with open(ARQUIVO_LOCAL, 'wb') as f:
                while True:
                    dados = socket_dados.recv(4096)
                    if not dados: 
                        break
                    f.write(dados)
                    
            socket_dados.close() 
            socket_controle.recv(1024).decode()
            
            logging.info("Download concluído com sucesso. Recarregando interface...")
            aplicar_tema(ARQUIVO_LOCAL)
            
        else:
            logging.info("Nenhuma atualização pendente (Status 304).")

    except ConnectionRefusedError:
        logging.warning("Servidor indisponível. O BIND na porta 8021 falhou do outro lado.")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
    finally:
        socket_controle.close()
                
    time.sleep(5)