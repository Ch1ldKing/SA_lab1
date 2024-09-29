import socket
import threading
import json
import redis
import uuid

# Redis 客户端配置
redis_client = redis.Redis(host="localhost", port=6379, db=0)


def handle_message(message):
    try:
        data = json.loads(message)
        conversation_id = data.get("conversation_id", str(uuid.uuid4()))
        user_query = data["user_query"]
        ai_response = data["ai_response"]

        redis_key = f"conversation:{conversation_id}"
        redis_client.hmset(
            redis_key, {"user_query": user_query, "ai_response": ai_response}
        )
        print(f"Stored conversation {conversation_id} to Redis.")
    except Exception as e:
        print(f"Error handling message in Redis subscriber: {e}")


def subscribe_to_broker(host="localhost", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    client.sendall("SUBSCRIBER".encode())
    print("Connected to Message Broker as Subscriber.")

    try:
        while True:
            data = client.recv(4096).decode()
            if not data:
                break
            handle_message(data)
    except KeyboardInterrupt:
        print("Redis subscriber shutting down.")
    except Exception as e:
        print(f"Error in Redis subscriber: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    subscribe_to_broker()
