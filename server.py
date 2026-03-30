import socket
import threading

def binary_to_hex(binary_str):
    try:
        decimal_val = int(binary_str.strip(), 2)
        return hex(decimal_val).upper().replace('0X', '')
    except ValueError:
        return "Ошибка: неверный формат двоичного числа"

class Server:
    def __init__(self, port):
        self.host = '127.0.0.1'
        self.port = port
        self.clients = {}  # {socket: name}
        
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen()
            print(f"Сервер запущен на порту {self.port}")
        except socket.error:
            print(f"Ошибка: порт {self.port} занят.")
            exit()

    def broadcast_client_list(self):
        names = list(self.clients.values())
        msg = f"LIST|{','.join(names)}"
        for client in self.clients:
            try:
                client.send(msg.encode('utf-8'))
            except:
                pass

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data: break
                
                # Разделяем служебную информацию и текст сообщения
                parts = data.split('|', 1)
                targets_part = parts[0].replace('TARGETS:', '')
                targets = [t.strip() for t in targets_part.split(',')]
                message_content = parts[1].replace('MESSAGE:', '')
                sender_name = self.clients[client_socket]

                # Формируем текст ответа
                response_text = message_content
                
                # Логика варианта 20: поиск маркера <@>
                if "<@>" in message_content:
                    # Извлекаем всё, что идет ПОСЛЕ <@>
                    binary_part = message_content.split("<@>")[1].strip()
                    # Убираем возможные лишние слова после числа, если они есть
                    binary_number = binary_part.split()[0] 
                    
                    hex_result = binary_to_hex(binary_number)
                    # Добавляем преобразованное сообщение согласно заданию [cite: 10]
                    response_text += f"\n[Конвертация варианта 20]: HEX = {hex_result}"

                final_msg = f"MSG|{sender_name}: {response_text}"
                
                # Рассылка выбранным клиентам [cite: 24]
                for sock, name in self.clients.items():
                    if 'all' in targets or name in targets or name == sender_name:
                        sock.send(final_msg.encode('utf-8'))
            except Exception as e:
                print(f"Ошибка при обработке: {e}")
                break

    def run(self):
        while True:
            try:
                client, addr = self.server.accept()
                name = client.recv(1024).decode('utf-8')
                self.clients[client] = name
                print(f"Подключен: {name}")
                self.broadcast_client_list()
                threading.Thread(target=self.handle_client, args=(client,)).start()
            except:
                break

if __name__ == "__main__":
    p = input("Введите порт сервера (по умолчанию 5000): ")
    port = int(p) if p else 5000
    Server(port).run()