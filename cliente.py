import socket
import hashlib
import os
import json
import time
import sys # Para pegar o nome do terminal

HOST = '127.0.0.1'
PORTA_CONTROLE = 8021
PORTA_DADOS = 8020

# ISOLAMENTO DE MÁQUINAS: Pega o nome do terminal rodando
# Exemplo: python cliente.py Terminal_A
nome_terminal = sys.argv[1] if len(sys.argv) > 1 else "Terminal_Generico"
PASTA_LOCAL = f"pasta_{nome_terminal}"

os.makedirs(PASTA_LOCAL, exist_ok=True)
ARQUIVO_LOCAL = os.path.join(PASTA_LOCAL, 'config_master.json')

def calcular_hash(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        return None
    sha = hashlib.sha256()
    with open(caminho_arquivo, 'rb') as f:
        sha.update(f.read())
    return sha.hexdigest()

def aplicar_tema(caminho_arquivo_json):
    """Lê o JSON local e muda as cores do terminal usando códigos ANSI."""
    try:
        with open(caminho_arquivo_json, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Erro ao ler JSON: {e}")
        return

    # Dicionário de Cores ANSI
    temas = {
        "dark": "\033[0;37;40m",    # Texto Branco, Fundo Preto
        "light": "\033[0;30;47m",   # Texto Preto, Fundo Branco
        "matrix": "\033[1;32;40m",  # Texto Verde Brilhante, Fundo Preto
        "hacker": "\033[1;31;40m",  # Texto Vermelho, Fundo Preto
        "ocean": "\033[1;36;44m",   # Texto Ciano, Fundo Azul
        "alerta": "\033[1;33;41m"   # Texto Amarelo, Fundo Vermelho (Cuidado!)
    }
    
    tema_escolhido = config.get("tema", "dark")
    cor_ansi = temas.get(tema_escolhido, temas["dark"])
    msg = config.get("mensagem_boas_vindas", "Terminal Pronto.")

    # Limpa a tela (cls para Windows, clear para Linux/Mac)
    os.system('cls' if os.name == 'nt' else 'clear')

    # Aplica a cor (o end="" evita pular linha)
    print(cor_ansi, end="") 
    
    # Desenha a Interface
    print("\n")
    if config.get("exibir_cabecalho", True):
        print("=" * 60)
        print(f" {msg} ".center(60, "="))
        print("=" * 60)
    
    print(f"\n[INFO] Terminal: {nome_terminal}")
    print(f"[INFO] Versão da Configuração: {config.get('versao', 'Desconhecida')}")
    print(f"[INFO] Tema Ativo: {tema_escolhido.upper()}")
    print("\n> Aguardando novas ordens da central...\n")

# Se o cliente já tiver um arquivo salvo da última vez, aplica o visual logo ao abrir
if os.path.exists(ARQUIVO_LOCAL):
    aplicar_tema(ARQUIVO_LOCAL)
else:
    print(f"[{nome_terminal}] Iniciado. Buscando primeira configuração...")

while True:
    hash_atual = calcular_hash(ARQUIVO_LOCAL)
    
    # Se o cliente for novo e não tiver o arquivo, mandamos a palavra VAZIO
    hash_envio = hash_atual if hash_atual else "VAZIO"
    
    try:
        socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_controle.connect((HOST, PORTA_CONTROLE))
        
        # Pede para o servidor checar o hash atual
        comando = f"CHECK_CONF {hash_envio}"
        socket_controle.sendall(comando.encode())
        
        resposta = socket_controle.recv(1024).decode()
        
        # O Cliente agora RECEBE os dados (Inversão)
        if "150" in resposta:
            socket_dados = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_dados.connect((HOST, PORTA_DADOS))
            
            # Abre o arquivo local em modo de escrita binária (wb)
            with open(ARQUIVO_LOCAL, 'wb') as f:
                while True:
                    dados = socket_dados.recv(4096)
                    if not dados: 
                        break
                    f.write(dados)
                    
            socket_dados.close() 
            
            status_final = socket_controle.recv(1024).decode()
            print(f"\n[+] Nova configuração baixada com sucesso!")
            aplicar_tema(ARQUIVO_LOCAL)
        #elif "304" in resposta:
            # Comentado para não poluir o terminal, ele apenas dorme
            # print("Configuração já está na versão mais recente.")

    except ConnectionRefusedError:
        print("Servidor offline. Tentando novamente...")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        socket_controle.close()
                
    # Verifica a cada 5 segundos
    time.sleep(5)