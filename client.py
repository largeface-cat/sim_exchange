import socket
import re
from utils import encrypt, decrypt
import threading

class Client:
    def __init__(self):
        self.ckey = None

    def start(self, id, passwd, host='127.0.0.1', port=12345):
        monitor = threading.Thread(target=self.monitor, args=(host, port))
        monitor.start()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(encrypt(f'login@{id}:{passwd}').encode())
            response = s.recv(1024)
            self.ckey = decrypt(response.decode())
            print(self.ckey)
            while True:
                order = input()
                response = None
                if (match:=re.match(r'([ab]) ([A-Z]+) (\d+(?:\.\d+)?) ([0-9]+) ([0-9]+)', order)):
                    s.sendall(encrypt(f'{id}&{self.ckey}order@{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}:{match.group(5)}').encode())
                    response = s.recv(1024)
                elif (match:=re.match(r'([ab]) ([A-Z]+) (\d+(?:\.\d+)?) ([0-9]+)', order)):
                    s.sendall(encrypt(f'{id}&{self.ckey}order@{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}').encode())
                    response = s.recv(1024)
                elif (match:=re.match(r'([ab]) ([LI]) ([A-Z]+) ([0-9]+)', order)):
                    s.sendall(encrypt(f'{id}&{self.ckey}order@{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}').encode())
                    response = s.recv(1024)
                if response:
                    response = decrypt(response.decode())
                    print(response)
                else:
                    print('Unrecognized')

    def monitor(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(encrypt(f'monitor').encode())
            while True:
                response = s.recv(1024)
                # print(response)