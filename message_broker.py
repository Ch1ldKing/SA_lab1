import socket
import threading

# 实现消息队列类
class MessageBroker:
    def __init__(self, host="localhost", port=9999):
        self.host = host
        self.port = port
        self.subscribers = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"Message Broker running on {self.host}:{self.port}")

    def start(self):
        try:
            while True:
                client_socket, addr = self.server.accept()
                print(f"Connection from {addr}")
                threading.Thread(
                    target=self.handle_client, args=(client_socket,), daemon=True
                ).start()
        except KeyboardInterrupt:
            print("Shutting down broker.")
            self.server.close()

    def handle_client(self, client_socket):
        try:
            # First message determines if client is a publisher or subscriber
            role = client_socket.recv(1024).decode().strip()
            if role == "PUBLISHER":
                self.handle_publisher(client_socket)
            elif role == "SUBSCRIBER":
                self.subscribers.append(client_socket)
                print(f"Subscriber added. Total subscribers: {len(self.subscribers)}")
                while True:
                    # Keep the subscriber connection alive
                    data = client_socket.recv(1024)
                    if not data:
                        break
            else:
                print("Unknown role. Closing connection.")
                client_socket.close()
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            if client_socket in self.subscribers:
                self.subscribers.remove(client_socket)
                print(f"Subscriber removed. Total subscribers: {len(self.subscribers)}")
            client_socket.close()

    def handle_publisher(self, client_socket):
        try:
            while True:
                message = client_socket.recv(4096).decode()
                if not message:
                    break
                print(f"Received message from publisher: {message}")
                self.broadcast(message)
        except Exception as e:
            print(f"Error handling publisher: {e}")
        finally:
            client_socket.close()

    def broadcast(self, message):
        to_remove = []
        for subscriber in self.subscribers:
            try:
                subscriber.sendall(message.encode())
            except:
                to_remove.append(subscriber)
        for subscriber in to_remove:
            self.subscribers.remove(subscriber)
            subscriber.close()
            print(f"Removed a subscriber. Total subscribers: {len(self.subscribers)}")


if __name__ == "__main__":
    broker = MessageBroker(host="localhost", port=9999)
    broker.start()
