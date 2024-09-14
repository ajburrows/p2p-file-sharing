import socket
import threading
import time

file_data = ""
class Peer:
    def __init__(self, peer_id, host, port):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.client_socket = None
        self.listener_socket = None
        self.is_running = True  # Flag to control the background thread
        print(f'peer.py: Created new peer id: {peer_id}, host: {host}, port: {port}')

    def start_listening(self):
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.bind((self.host, self.port + 1000))
        self.listener_socket.listen(5)
        print(f'peer.py: Peer{self.peer_id} listening on port {self.port + 1000}')
        while self.is_running:
            conn, addr = self.listener_socket.accetp()
            thread = threading.Thread(target=self.handle_peer_request, args=(conn, addr))
            thread.start()
    
    def handle_peer_request(self, conn, addr):
        print(f'client.py: Received connection from {addr}')
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            print(f'Received data from {addr}: {data}')
        conn.close()

    def get_peer_id(self):
        return self.peer_id

    def create_peer_socket(self):
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(2)
        print(f'peer.py: Created socket for Peer{self.peer_id}')

    def connect(self):
        self.peer_socket.connect((self.host, self.port))
        print(f"peer.py: Peer {self.peer_id} connected to server at {self.host}:{self.port}")

    def send_message(self, message):
        if self.peer_socket:
            message = '1' + message
            self.peer_socket.send(message.encode('utf-8'))
            print(f'peer.py: Client{self.client_id} sent message: {message[1:]}')
        else:
            raise Exception('peer.py: Client is not connected to a server.')
    
    def req_chunk(self):
        if self.peer_socket:
            print(f'peer.py: Peer{self.peer_id} requesting data')
            self.peer_socket.send('0'.encode('utf-8'))
            server_data = self.peer_socket.recv(1024).decode('utf-8')
            print(f'peer.py: Peer{self.peer_id} received data\n           data: {server_data}')
            
            if server_data[0] == '0':
                file_data += server_data[1:]
            #TODO: if server_data[0] == 1, then server_data[1:] is the address of the peer who has
            # the desired data, so ask that peer for the data
            self.peer_socket.send('1'.encode('utf-8')) # tell the server the data was recieved

        else:
            raise Exception('peer.py: Peer is not connected to a server.')

    def close(self):
        if self.peer_socket:
            self.peer_socket.close()
            self.is_running = False
            print(f"peer.py: Peer {self.peer_id} socket closed.")
        else:
            raise Exception("peer.py: Peer socket was never created or is already closed.")

    def run_in_background(self):
        self.start_listening()

def peer_thread_function(peer): 
    peer.run_in_background()
