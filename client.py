import socket
import threading
import sys

def receive_messages(sock):
    """Поток для асинхронного приема сообщений."""
    while True:
        try:
            data = sock.recv(4096).decode('utf-8')
            if not data:
                print("\n[Система] Соединение разорвано сервером.")
                break
            
            if data.startswith("LIST|"):
                users = data.split('|')[1]
                print(f"\n[Система] В сети: {users}")
                print("Кому отправить (имя или all) > ", end="", flush=True)
                
            elif data.startswith("MSG|"):
                content = data.split('|', 1)[1]
                print(f"\n{content}")
                print("Кому отправить (имя или all) > ", end="", flush=True)
                
        except ConnectionResetError:
            print("\n[Система] Соединение разорвано.")
            break
        except Exception as e:
            break

def start_client():
    ip = input("Введите IP сервера (127.0.0.1): ") or "127.0.0.1"
    port_input = input("Введите порт (5000): ")
    port = int(port_input) if port_input else 5000
    name = input("Введите ваше имя: ").strip()
    
    if not name:
        name = "Anonymous"

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((ip, port))
        client.send(name.encode('utf-8'))
    except ConnectionRefusedError:
        print("Ошибка: Не удалось подключиться. Сервер не запущен.")
        return
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return

    recv_thread = threading.Thread(target=receive_messages, args=(client,), daemon=True)
    recv_thread.start()

    print("Подключение успешно. Для выхода нажмите Ctrl+C.")
    
    while True:
        try:
            target = input("Кому отправить (имя или all) > ")
            if not target:
                continue
            
            msg = input("Сообщение (используйте <@> для конвертации) > ")
            
            payload = f"TARGETS:{target}|MESSAGE:{msg}"
            client.send(payload.encode('utf-8'))
            
        except KeyboardInterrupt:
            print("\nВыход...")
            break
        except EOFError:
            break
            
    client.close()

if __name__ == "__main__":
    start_client()