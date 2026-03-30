import socket
import threading

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data: break
            if data.startswith("LIST|"):
                print(f"\n[Система] В сети: {data.split('|')[1]}")
            elif data.startswith("MSG|"):
                print(f"\n{data.split('|')[1]}")
            print("Кому отправить (имя или all) > ", end="", flush=True)
        except:
            break

def start_client():
    ip = input("Введите IP сервера (127.0.0.1): ") or "127.0.0.1"
    port_input = input("Введите порт (5000): ")
    port = int(port_input) if port_input else 5000
    name = input("Введите ваше имя: ")

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((ip, port))
        client.send(name.encode('utf-8'))
    except:
        print("Ошибка: сервер не найден.")
        return

    threading.Thread(target=receive_messages, args=(client,), daemon=True).start()

    while True:
        try:
            target = input("Кому отправить (имя или all) > ")
            msg = input("Сообщение (используйте <@> для конвертации) > ")
            payload = f"TARGETS:{target}|MESSAGE:{msg}"
            client.send(payload.encode('utf-8'))
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    start_client()