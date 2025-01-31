import argparse
import getpass
from client import Client

def main():
    parser = argparse.ArgumentParser(
        description='client login',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-u', '--username',
        help='input username e.g.: -u cat'
    )
    parser.add_argument(
        '-p', '--password',
        help='password (should avoid command line input for safety reason)'
    )
    args = parser.parse_args()

    username = args.username
    if not username:
        username = input("username:").strip()
        if not username:
            print("err: empty username")
            return

    password = args.password
    if not password:
        password = getpass.getpass("password:")
    if not password:
        print("err: empty password")
        return

    try:
        c = Client()
        c.start(username, password)
    except Exception as e:
        print(f"connection failed: {str(e)}")

if __name__ == "__main__":
    main()