import socket
import threading

def binary_to_hex(binary_str):
    """
    Конвертация строки с двоичным числом в шестнадцатеричное представление.
    Вариант 20.
    """
    try:
        clean_str = binary_str.strip()
        if not clean_str:
            return ""
        if not all(c in '01' for c in clean_str):
            return "Ошибка: не двоичное число"
        
        decimal_val = int(clean_str, 2)
        return hex(decimal_val)[2:].upper()
    except ValueError:
        return "Ошибка преобразования"

class Server:
    def __init__(self, port):
        self.host = '127.0.0.1'
        self.port = port
        self.clients = {}  # {socket_object: client_name}
        self.lock = threading.Lock() 
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[Сервер] Запущен на порту {self.port}")
        except socket.error as e:
            print(f"[Ошибка] Порт {self.port} занят. {e}")
            exit(1)

    def broadcast_list(self):
        with self.lock:
            names = list(self.clients.values())
        msg = f"LIST|{','.join(names)}"
        
        disconnected = []
        for client_sock in self.clients:
            try:
                client_sock.send(msg.encode('utf-8'))
            except:
                disconnected.append(client_sock)
        
        for sock in disconnected:
            self.remove_client(sock)

    def remove_client(self, client_sock):
        with self.lock:
            if client_sock in self.clients:
                name = self.clients.pop(client_sock)
                print(f"[Сервер] Клиент отключился: {name}")
        try:
            client_sock.close()
        except:
            pass
        self.broadcast_list()

    def handle_client(self, client_sock):
        client_name = "Unknown"
        try:
            name_data = client_sock.recv(1024).decode('utf-8')
            if not name_data:
                self.remove_client(client_sock)
                return
            
            client_name = name_data.strip()
            with self.lock:
                self.clients[client_sock] = client_name
            print(f"[Сервер] Подключился: {client_name}")
            
            self.broadcast_list()

            while True:
                data = client_sock.recv(4096).decode('utf-8')
                if not data:
                    break
                
                if '|' not in data:
                    continue
                
                parts = data.split('|', 1)
                targets_raw = parts[0].replace('TARGETS:', '')
                message_text = parts[1].replace('MESSAGE:', '', 1)
                
                targets = [t.strip() for t in targets_raw.split(',')]
                
                response_text = message_text
                if "<@>" in message_text:
                    binary_part = message_text.split("<@>", 1)[1].strip()
                    binary_number = binary_part.split()[0] if binary_part.split() else ""
                    
                    if binary_number:
                        hex_result = binary_to_hex(binary_number)
                        response_text += f"\n[Конвертация: {binary_number} -> HEX]: {hex_result}"

                final_msg = f"MSG|{client_name}: {response_text}"
                
                with self.lock:
                    current_clients = dict(self.clients)
                
                for sock, name in current_clients.items():
                    if 'all' in targets or name in targets:
                        try:
                            sock.send(final_msg.encode('utf-8'))
                        except:
                            pass

        except Exception as e:
            print(f"[Ошибка] Клиент {client_name}: {e}")
        finally:
            self.remove_client(client_sock)

    def run(self):
        print("[Сервер] Ожидание подключений...")
        while True:
            try:
                client_sock, addr = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True)
                thread.start()
            except Exception as e:
                print(f"[Ошибка] Accept failed: {e}")
                break

if __name__ == "__main__":
    p = input("Введите порт сервера (по умолчанию 5000): ")
    port = int(p) if p else 5000
    server = Server(port)
    server.run()