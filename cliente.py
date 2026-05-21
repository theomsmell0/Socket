import socket
import json
import struct
import hashlib
import os

# Configurações de rede e arquivo
HOST = '127.0.0.1'
PORT = 5000
ARQUIVO_ALVO = 'teste.txt'  # Certifique-se de que um arquivo com este nome exista na pasta
TAMANHO_BLOCO = 4096

def iniciar_cliente():
    # 1. Validação do arquivo no disco
    if not os.path.exists(ARQUIVO_ALVO):
        print(f"Erro: O arquivo '{ARQUIVO_ALVO}' não foi encontrado.")
        return

    tamanho_arquivo = os.path.getsize(ARQUIVO_ALVO)
    print(f"Processando '{ARQUIVO_ALVO}' ({tamanho_arquivo} bytes)...")

    # 2. Leitura inicial para cálculo do hash SHA-256
    sha256 = hashlib.sha256()
    with open(ARQUIVO_ALVO, 'rb') as arquivo:
        for bloco in iter(lambda: arquivo.read(TAMANHO_BLOCO), b""):
            sha256.update(bloco)
    hash_arquivo = sha256.hexdigest()

    # 3. Geração do JSON e do prefixo estruturado (4 bytes)
    cabecalho = {
        "operacao": "UPLOAD",
        "nome_arquivo": ARQUIVO_ALVO,
        "tamanho_bytes": tamanho_arquivo,
        "hash_sha256": hash_arquivo
    }
    bytes_cabecalho = json.dumps(cabecalho).encode('utf-8')
    tamanho_cabecalho = len(bytes_cabecalho)
    prefixo_tamanho = struct.pack('>I', tamanho_cabecalho)

    # 4. Instanciação do socket TCP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # APLICAÇÃO DO CONNECT: O script bloqueia aqui até que o SO
        # complete a sequência de inicialização TCP com o servidor.
        print(f"Requisitando conexão ao servidor em {HOST}:{PORT}...")
        client_socket.connect((HOST, PORT))
        
        # APLICAÇÃO DO SENDALL (Metadados): Transferência dos dados de controle.
        # Envia primeiro os 4 bytes com o tamanho do JSON.
        client_socket.sendall(prefixo_tamanho)
        # Envia a sequência de bytes correspondente ao JSON.
        client_socket.sendall(bytes_cabecalho)
        
        # APLICAÇÃO DO SENDALL (Dados do Arquivo): Transferência do conteúdo.
        print("Iniciando transmissão dos dados...")
        bytes_enviados = 0
        with open(ARQUIVO_ALVO, 'rb') as arquivo:
            while True:
                dados = arquivo.read(TAMANHO_BLOCO)
                if not dados:
                    break
                client_socket.sendall(dados)
                bytes_enviados += len(dados)
        
        print(f"Transmissão concluída ({bytes_enviados} bytes). Aguardando validação...")
        
        # 5. Bloqueio de leitura aguardando o código de status do servidor
        resposta = client_socket.recv(1024)
        print(f"Retorno do servidor: {resposta.decode('utf-8')}")

    except ConnectionRefusedError:
        print("Erro: O servidor recusou a conexão. Verifique se servidor.py está em execução.")
    except Exception as e:
        print(f"Ocorreu um erro durante a operação: {e}")
    finally:
        # 6. Liberação dos recursos do sistema operacional
        client_socket.close()
        print("Conexão encerrada.")

if __name__ == "__main__":
    iniciar_cliente()