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
        print(f'client.py: Created new client id: {client_id}, host: {host}, port: {port}')

    def get_client_id(self):
        return self.client_id

    def create_client_socket(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(2)
        print(f'client.py: Created socket for Client{self.client_id}')

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        print(f"client.py: Client {self.client_id} connected to server at {self.host}:{self.port}")

    def send_message(self, message):
        if self.client_socket:
            message = '1' + message
            self.client_socket.send(message.encode('utf-8'))
            print(f'client.py: Client{self.client_id} sent message: {message[1:]}')
        else:
            raise Exception('client.py: Client is not connected to a server.')
    
    def req_data(self):
        if self.client_socket:
            print(f'client.py: Client{self.client_id} requesting data')
            self.client_socket.send('0'.encode('utf-8'))
            server_data = self.client_socket.recv(1024).decode('utf-8')
            print(f'client.py: Client{self.client_id} received data\n           data: {server_data}')
        else:
            raise Exception('client.py: Client is not connected to a server.')

    def close(self):
        if self.client_socket:
            self.client_socket.close()
            self.is_running = False
            print(f"client.py: Client {self.client_id} socket closed.")
        else:
            raise Exception("client.py: Client socket was never created or is already closed.")

    def run_in_background(self):
        #Thread function to simulate background tasks.
        while self.is_running:
            time.sleep(1)
            #print(f"\n[client.py: Client {self.client_id} running in background...]\n")

def client_thread_function(client): 
    """
    The function that will be run in the client thread.
    It will handle the background tasks of the client.
    """
    client.run_in_background()
