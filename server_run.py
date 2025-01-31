from server import Server
from utils import load_users_from_json

if __name__ == "__main__":
    try:
        users = load_users_from_json()
        server = Server(users)
        server.start()
    except Exception as e:
        print(f"err: {str(e)}")
        exit(1)