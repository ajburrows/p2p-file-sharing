import socket
import threading
import time

class Peer:
    def __init__(self, peer_id, host, port):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.server_socket = None
        self.listener_socket = None
        self.is_running = True  # Flag to control the background thread
        self.file_data = ''
        print(f'  peer.py: Created new peer id: {peer_id}, host: {host}, port: {port}')

    def start_listening(self):
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f'  peer.py: Peer{self.peer_id} listening port: {self.port+self.peer_id}')
        self.listener_socket.bind((self.host, self.port + self.peer_id))
        self.listener_socket.listen(5)
        print(f'  peer.py: Peer{self.peer_id} listening on port {self.port + self.peer_id}')
        while self.is_running:
            conn, addr = self.listener_socket.accept()
            thread = threading.Thread(target=self.handle_peer_request, args=(conn, addr))
            thread.start()
    
    def handle_peer_request(self, conn, addr):
        print(f'  peer.py: Peer{self.peer_id} received connection from {addr}')
        conn.settimeout(5.0)
        while self.is_running:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            print(f'  peer.py: Peer{self.peer_id} Received data from {addr}\n           data: {data}')

            # if data starts with "2", the peer is requesting file_data
            if data[0] == '2':
                conn.send(self.file_data.encode('utf-8'))
                break
        conn.close()
        print(f'  peer.py: Peer{self.peer_id} conn closed')

    def get_peer_id(self):
        return self.peer_id

    def create_server_socket(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(2)
        print(f'  peer.py: Created socket for Peer{self.peer_id}')

    def connect(self):
        self.server_socket.connect((self.host, self.port))
        print(f"  peer.py: Peer {self.peer_id} connected to server at {self.host}:{self.port}")

    def send_message(self, message):
        if self.server_socket:
            message = '1' + message
            self.server_socket.send(message.encode('utf-8'))
            print(f'  peer.py: Peer{self.peer_id} sent message to server: {message[1:]}')
        else:
            raise Exception(f'  peer.py: Peer{self.peer_id} is not connected to a server.')
    
    def verify_data(self, data):
        if data == '<server_data_here>':
            return True
        return False

    def req_chunk(self):
        if self.server_socket:
            print(f'  peer.py: Peer{self.peer_id} requesting data')
            message = '0' + str(self.peer_id) + str(self.port + self.peer_id)# send the server the port of the listener_socket
            self.server_socket.send(message.encode('utf-8'))
            server_data = self.server_socket.recv(1024).decode('utf-8')
            print(f'  peer.py: Peer{self.peer_id} received data from server\n           data: {server_data}')
            
            if server_data[0] == '0':
                self.file_data += server_data[1:]
            
            # if server_data starts with "1", then the peer must get the data from another peer
            elif server_data[0] == '1':
                peer_ip, peer_port = server_data[1:].split(':')[0], server_data[1:].split(':')[1]
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                try:
                    print(f'  peer.py: Peer{self.peer_id} connected to peer [{peer_ip}:{peer_port}]')
                    peer_socket.connect((peer_ip, int(peer_port))) #TODO: the port given represents the server_port of the peer. Get their listening port instead (ask the server)
                    peer_socket.send('2'.encode('utf-8')) # ask the peer for the data (op 2)
                    self.file_data += peer_socket.recv(1024).decode('utf-8') # record the data from the peer
                    print(f'  peer.py: Peer{self.peer_id} now has file_data: {self.file_data}')
                except ConnectionRefusedError:
                    print(f'  peer.py: Peer{self.peer_id} failed to connect to peer [{peer_ip}:{peer_port}]')
                finally:
                    peer_socket.close()
                    print(f'  peer.py: Peer{self.peer_id} closed socket with peer [{peer_ip}:{peer_port}]')

            if self.verify_data(self.file_data):
                self.server_socket.send('1'.encode('utf-8')) # tell the server the data was recieved
            else:
                #TODO: if invalid data is received, wait for another response from server (either another ip address or the file_data)
                print(f'  peer.py: Peer{self.peer_id} received invalid data from peer [{peer_ip}:{peer_port}]')
                self.server_socket.send('0'.encode('utf-8'))

        else:
            raise Exception('  peer.py: Peer is not connected to a server.')

    def close(self):
        if self.server_socket:
            self.server_socket.close()
        if self.listener_socket:
            self.listener_socket.close()
        self.is_running = False
        print(f"  peer.py: Peer{self.peer_id} sockets closed.")

    def run_in_background(self):
        self.start_listening()

def peer_thread_function(peer): 
    peer.run_in_background()
