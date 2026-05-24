import socket
import json
import struct
import hashlib
import os

# Configurações de rede e diretório
HOST = '127.0.0.1' # Localhost
PORT = 5000
TAMANHO_BLOCO = 4096 # 4 KB de leitura por vez
DIRETORIO_DESTINO = 'recebidos'

# Cria o diretório 'recebidos' se ele não existir
if not os.path.exists(DIRETORIO_DESTINO):
    os.makedirs(DIRETORIO_DESTINO)

def receber_exatamente(sock, num_bytes):
    """
    Lê uma quantidade exata de bytes do socket.
    Necessário porque a rede pode fragmentar os pacotes TCP.
    """
    dados = bytearray()
    while len(dados) < num_bytes:
        pacote = sock.recv(num_bytes - len(dados))
        if not pacote:
            return None # Conexão interrompida
        dados.extend(pacote)
    return dados

def iniciar_servidor():
    # 1. Configuração do Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #instrui uso de endereço ipv4//instrui do so a usar o protocolo tcp
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    
    print(f"Servidor aguardando conexões em {HOST}:{PORT}...")

    while True:
        client_socket, endereco_cliente = server_socket.accept()
        print(f"Conexão estabelecida com {endereco_cliente}")

        try:
            # 2. Leitura do prefixo de tamanho (4 bytes)
            bytes_prefixo = receber_exatamente(client_socket, 4)
            if not bytes_prefixo:
                print("Erro: Não foi possível ler o prefixo.")
                client_socket.close()
                continue
            
            # Converte os 4 bytes em um número inteiro
            tamanho_cabecalho = struct.unpack('>I', bytes_prefixo)[0]

            # 3. Leitura do cabeçalho JSON
            bytes_cabecalho = receber_exatamente(client_socket, tamanho_cabecalho)
            if not bytes_cabecalho:
                print("Erro: Não foi possível ler o cabeçalho.")
                client_socket.close()
                continue
                
            cabecalho = json.loads(bytes_cabecalho.decode('utf-8'))
            nome_arquivo = cabecalho['nome_arquivo']
            tamanho_total = cabecalho['tamanho_bytes']
            hash_esperado = cabecalho['hash_sha256']
            
            print(f"Metadados recebidos: Arquivo '{nome_arquivo}', Tamanho: {tamanho_total} bytes")

            # 4. Preparação para receber o arquivo
            caminho_salvamento = os.path.join(DIRETORIO_DESTINO, nome_arquivo)
            bytes_recebidos = 0
            
            # Inicializa o objeto de hash para calcular os dados em tempo real
            sha256_calculado = hashlib.sha256()

            # 5. Recepção em blocos e escrita no disco
            with open(caminho_salvamento, 'wb') as arquivo:
                while bytes_recebidos < tamanho_total:
                    # Determina o tamanho da próxima leitura (não exceder o tamanho total)
                    bytes_restantes = tamanho_total - bytes_recebidos
                    tamanho_leitura = min(TAMANHO_BLOCO, bytes_restantes)
                    
                    dados_bloco = client_socket.recv(tamanho_leitura)
                    if not dados_bloco:
                        print("Erro: A conexão foi perdida durante o download.")
                        break
                        
                    # Escreve no arquivo e atualiza o hash
                    arquivo.write(dados_bloco)
                    sha256_calculado.update(dados_bloco)
                    bytes_recebidos += len(dados_bloco)
            
            # 6. Validação de integridade
            hash_final = sha256_calculado.hexdigest()
            print(f"Recebimento concluído. Validando integridade...")
            
            if hash_final == hash_esperado:
                print(f"SUCESSO: Os hashes coincidem ({hash_final}). O arquivo está íntegro.")
                client_socket.sendall(b"STATUS 200 OK")
            else:
                print(f"FALHA: Os hashes são diferentes.\nEsperado: {hash_esperado}\nCalculado: {hash_final}")
                client_socket.sendall(b"STATUS 500 CORROMPIDO")

        except Exception as e:
            print(f"Ocorreu um erro no processamento: {e}")
        
        finally:
            client_socket.close()
            print("Conexão encerrada.\n---")

if __name__ == "__main__":
    iniciar_servidor()