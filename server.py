import socket
import threading

def binary_to_hex(binary_str):
    """Вариант 20: Конвертер Binary -> Hex"""
    try:
        clean_str = binary_str.strip()
        if not clean_str or not all(c in '01' for c in clean_str):
            return "Ошибка: не двоичное число"
        decimal_val = int(clean_str, 2)
        return hex(decimal_val)[2:].upper()
    except ValueError:
        return "Ошибка преобразования"

class Server:
    def __init__(self, port):
        self.host = '127.0.0.1'
        self.port = port
        self.clients = {}       # {socket: name}
        self.client_rooms = {}  # {socket: room_name}
        self.rooms = {}         # {room_name: [socket1, socket2, ...]}
        self.lock = threading.Lock()
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[Сервер] Запущен на порту {self.port}")
        except socket.error as e:
            print(f"[Ошибка] Порт занят: {e}")
            exit(1)

    def send_to_client(self, client_sock, message):
        try:
            client_sock.send(message.encode('utf-8'))
        except:
            pass

    def send_to_room(self, room_name, message, exclude_sock=None):
        with self.lock:
            if room_name not in self.rooms:
                return False
            participants = list(self.rooms[room_name])
        
        for sock in participants:
            if sock != exclude_sock: 
                try:
                    sock.send(message.encode('utf-8'))
                except:
                    pass
        return True

    def get_help_message(self):
        return (
            "[Система] Доступные команды:\n"
            "/create <name>   - Создать группу и войти в нее\n"
            "/join <name>     - Войти в существующую группу\n"
            "/leave           - Покинуть текущую группу\n"
            "/delete <name>   - Удалить группу\n"
            "/list_groups     - Список всех групп\n"
            "/send_group <grp> <msg> - Отправить сообщение в группу (не входя в нее)\n"
            "/send_user <user> <msg> - Отправить личное сообщение\n"
            "Любой другой текст - Сообщение в текущую активную группу\n"
            "Используйте <@> для конвертации (пример: privet <@> 1010)"
        )

    def handle_client(self, client_sock):
        client_name = "Unknown"
        
        try:
            name_data = client_sock.recv(1024).decode('utf-8')
            if not name_data:
                self.disconnect_client(client_sock)
                return
            
            client_name = name_data.strip()
            
            with self.lock:
                self.clients[client_sock] = client_name
            
            self.send_to_client(client_sock, f"[Система] Добро пожаловать, {client_name}!\n")
            self.send_to_client(client_sock, self.get_help_message() + "\n")
            
            print(f"[+] Подключился: {client_name}")

            while True:
                data = client_sock.recv(4096).decode('utf-8')
                if not data:
                    break
                
                data = data.strip()
                if not data:
                    continue
                
                # --- КОМАНДЫ ---
                
                if data.startswith("/help") or data.startswith("/?"):
                    self.send_to_client(client_sock, self.get_help_message() + "\n")
                    continue

                if data.startswith("/create "):
                    args = data.split(" ", 1)
                    if len(args) < 2:
                        self.send_to_client(client_sock, "[Ошибка] Укажите имя группы: /create <name>\n")
                        continue
                    room_name = args[1].strip()
                    self.create_room(room_name, client_sock)
                    self.send_to_client(client_sock, f"[Система] Группа '{room_name}' создана. Вы автоматически добавлены.\n")
                    continue

                if data.startswith("/join "):
                    args = data.split(" ", 1)
                    if len(args) < 2:
                        self.send_to_client(client_sock, "[Ошибка] Укажите имя группы: /join <name>\n")
                        continue
                    room_name = args[1].strip()
                    success = self.join_room(room_name, client_sock)
                    if success:
                        self.send_to_client(client_sock, f"[Система] Вы вошли в группу '{room_name}'.\n")
                    else:
                        self.send_to_client(client_sock, f"[Ошибка] Группа '{room_name}' не найдена.\n")
                    continue

                if data == "/leave":
                    self.leave_room(client_sock)
                    self.send_to_client(client_sock, "[Система] Вы покинули группу.\n")
                    continue

                if data.startswith("/delete "):
                    args = data.split(" ", 1)
                    if len(args) < 2:
                        self.send_to_client(client_sock, "[Ошибка] Укажите имя группы: /delete <name>\n")
                        continue
                    room_name = args[1].strip()
                    self.delete_room(room_name, client_sock)
                    self.send_to_client(client_sock, f"[Система] Группа '{room_name}' удалена.\n")
                    continue

                if data == "/list_groups":
                    self.list_rooms(client_sock)
                    continue

                if data.startswith("/send_group "):
                    parts = data.split(" ", 2)
                    if len(parts) < 3:
                        self.send_to_client(client_sock, "[Ошибка] Формат: /send_group <GroupName> <Message>\n")
                        continue
                    target_room = parts[1]
                    msg_text = parts[2]
                    processed_msg = self.process_message(msg_text)
                    final_msg = f"[{target_room}] {client_name}: {processed_msg}\n"
                    
                    if self.send_to_room(target_room, final_msg):
                        self.send_to_client(client_sock, f"[Система] Сообщение отправлено в '{target_room}'.\n")
                    else:
                        self.send_to_client(client_sock, f"[Ошибка] Группа '{target_room}' не найдена.\n")
                    continue

                if data.startswith("/send_user "):
                    parts = data.split(" ", 2)
                    if len(parts) < 3:
                        self.send_to_client(client_sock, "[Ошибка] Формат: /send_user <UserName> <Message>\n")
                        continue
                    target_user = parts[1]
                    msg_text = parts[2]
                    processed_msg = self.process_message(msg_text)
                    final_msg = f"[Личное от {client_name}]: {processed_msg}\n"
                    
                    found = False
                    with self.lock:
                        for sock, name in self.clients.items():
                            if name == target_user:
                                self.send_to_client(sock, final_msg)
                                found = True
                                break
                    
                    if found:
                        self.send_to_client(client_sock, f"[Система] Сообщение отправлено пользователю {target_user}.\n")
                    else:
                        self.send_to_client(client_sock, f"[Ошибка] Пользователь {target_user} не найден.\n")
                    continue

                # --- ПРОСТОЕ СООБЩЕНИЕ ---
                with self.lock:
                    current_room = self.client_rooms.get(client_sock)

                if current_room:
                    processed_msg = self.process_message(data)
                    final_msg = f"[{current_room}] {client_name}: {processed_msg}\n"
                    self.send_to_room(current_room, final_msg)
                else:
                    self.send_to_client(client_sock, "[Система] Вы не в группе. Введите /help для команд.\n")

        except Exception as e:
            print(f"[Ошибка] {client_name}: {e}")
        finally:
            self.disconnect_client(client_sock)

    def process_message(self, text):
        if "<@>" in text:
            parts = text.split("<@>", 1)
            binary_part = parts[1].strip().split()[0] if parts[1].strip().split() else ""
            if binary_part:
                hex_res = binary_to_hex(binary_part)
                return f"{parts[0].strip()} <@> {binary_part}\n[Конвертация: {binary_part} -> HEX]: {hex_res}"
        return text

    def create_room(self, room_name, client_sock):
        with self.lock:
            if room_name not in self.rooms:
                self.rooms[room_name] = []
            if client_sock in self.client_rooms:
                old_room = self.client_rooms[client_sock]
                if old_room in self.rooms and client_sock in self.rooms[old_room]:
                    self.rooms[old_room].remove(client_sock)
            self.rooms[room_name].append(client_sock)
            self.client_rooms[client_sock] = room_name

    def join_room(self, room_name, client_sock):
        with self.lock:
            if room_name in self.rooms:
                if client_sock in self.client_rooms:
                    old_room = self.client_rooms[client_sock]
                    if old_room in self.rooms and client_sock in self.rooms[old_room]:
                        self.rooms[old_room].remove(client_sock)
                self.rooms[room_name].append(client_sock)
                self.client_rooms[client_sock] = room_name
                msg = f"[Система] {self.clients[client_sock]} присоединился к группе.\n"
                for sock in self.rooms[room_name]:
                    if sock != client_sock:
                        try: sock.send(msg.encode('utf-8'))
                        except: pass
                return True
            return False

    def leave_room(self, client_sock):
        with self.lock:
            if client_sock in self.client_rooms:
                room_name = self.client_rooms.pop(client_sock)
                if room_name in self.rooms:
                    if client_sock in self.rooms[room_name]:
                        self.rooms[room_name].remove(client_sock)
                    msg = f"[Система] {self.clients[client_sock]} покинул группу.\n"
                    for sock in list(self.rooms[room_name]):
                        try: sock.send(msg.encode('utf-8'))
                        except: pass

    def delete_room(self, room_name, client_sock):
        with self.lock:
            if room_name in self.rooms:
                msg = f"[Система] Группа '{room_name}' удалена пользователем {self.clients[client_sock]}.\n"
                for sock in list(self.rooms[room_name]):
                    try: 
                        sock.send(msg.encode('utf-8'))
                        if sock in self.client_rooms:
                            del self.client_rooms[sock]
                    except: pass
                del self.rooms[room_name]

    def list_rooms(self, client_sock):
        with self.lock:
            if not self.rooms:
                msg = "[Система] Нет активных групп.\n"
            else:
                rooms_list = ", ".join(self.rooms.keys())
                msg = f"[Система] Активные группы: {rooms_list}\n"
        self.send_to_client(client_sock, msg)

    def disconnect_client(self, client_sock):
        with self.lock:
            name = self.clients.pop(client_sock, "Unknown")
            if client_sock in self.client_rooms:
                room = self.client_rooms.pop(client_sock)
                if room in self.rooms:
                    if client_sock in self.rooms[room]:
                        self.rooms[room].remove(client_sock)
                    msg = f"[Система] {name} отключился.\n"
                    for sock in list(self.rooms[room]):
                        try: sock.send(msg.encode('utf-8'))
                        except: pass
        try: 
            client_sock.close()
        except: 
            pass
        print(f"[-] Отключился: {name}")

    def run(self):
        print("[Сервер] Ожидание подключений...")
        while True:
            try:
                client, addr = self.server_socket.accept()
                t = threading.Thread(target=self.handle_client, args=(client,), daemon=True)
                t.start()
            except Exception as e:
                print(f"[Ошибка] Accept failed: {e}")
                break

if __name__ == "__main__":
    p = input("Введите порт сервера (по умолчанию 5000): ")
    port = int(p) if p else 5000
    server = Server(port)
    server.run()