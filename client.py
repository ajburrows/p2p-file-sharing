"""import socket
import argparse
# operations: 
# prepend 0 to request data from server
# prepend 1 to send data to server
# prepend 2 to tell the server the client is closing

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None

    def create_client_socket(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.create_client_socket()
        self.client_socket.connect((self.host, self.port))
        print(f"Connected to server at {self.host}:{self.port}")

    def send_message(self, message):
        if self.client_socket:
            message = "1" + message
            self.client_socket.send(message.encode('utf-8'))
        else:
            raise Exception("Client is not connected to a server.")
    
    def receive_message(self):
        if self.client_socket:
            message = "0" + "hello"
            self.client_socket.send(message.encode('utf-8'))
            server_data = self.client_socket.recv(1024).decode('utf-8')
            print(f"SERVERDATA: {server_data}")
        else:
            raise Exception("Client is not connected to a server.")

    def close(self):
        if self.client_socket:
            self.client_socket.close()
            print("Client socket closed.")
        else:
            raise Exception("Client socket was never created or is already closed.")

def start_client(host, port):
    client = Client(host, port)
    client.connect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Client to connect to a server.")
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Server IP to connect to')
    parser.add_argument('--port', type=int, default=12345, help='Server port to connect to')
    args = parser.parse_args()

    start_client(args.host, args.port)"""

import socket
import threading
import time

class Client:
    def __init__(self, client_id, host, port):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = True  # Flag to control the background thread

    def create_client_socket(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.create_client_socket()
        self.client_socket.connect((self.host, self.port))
        print(f"Client {self.client_id} connected to server at {self.host}:{self.port}")

    def send_message(self, message):
        if self.client_socket:
            self.client_socket.send(message.encode('utf-8'))
            print(f"Client {self.client_id} sent message: {message}")
        else:
            raise Exception("Client is not connected to a server.")

    def close(self):
        if self.client_socket:
            self.client_socket.close()
            self.is_running = False
            print(f"Client {self.client_id} socket closed.")
        else:
            raise Exception("Client socket was never created or is already closed.")

    def run_in_background(self):
        #Thread function to simulate background tasks.
        while self.is_running:
            time.sleep(1)
            print(f"Client {self.client_id} running in background...")

def client_thread_function(client): 
    """
    The function that will be run in the client thread.
    It will handle the background tasks of the client.
    """
    client.run_in_background()
