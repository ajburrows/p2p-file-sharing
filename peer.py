import threading
import socket
import time

class Peer:
    def __init__(self, peer_id, host, port, files_dir):
        """
            Inputs:
                        peer_id - an integer used to identify the peer and help with debugging (int)
                           host - the ip address of the central server (string)
                           port - the port number of the central server (int)
                      files_dir - the root files path of the directory containing the files that this peer will share
            
            Variables:
                        peer_id - an integer used to identify the peer and help with debugging (int)
                           host - the ip address of the central server (string)
                           port - the port number of the central server (int)
                      files_dir - the root files path of the directory containing the files that this peer will share
                 server_ socket - a socket used specifically for communicating with the central server
                listener_socket - a socket used for recieving requests from other peers
                     is_running - a flag that is set to False when close_peer() is called to shut down the instance of the peer
                      file_data - this is where the data being downloaded from other peers is stored

        """

        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.files_dir = files_dir
        self.server_socket = None
        self.listener_socket = None
        self.is_running = True
        self.file_data = ''
        print(f'  peer.py: Created new peer id: {peer_id}, host: {host}, port: {port}, file_dir: {files_dir}')

    def start_listening(self):
        """
            Create and setup the listening socket.
            This is for handling requests from other peers, not the server.
            Throws OSError when the listener_socket is closed by close_peer()

        """

        # Create and setup the listener_socket
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener_socket.bind((self.host, self.port + self.peer_id))
        self.listener_socket.listen(5)
        self.listener_socket.settimeout(3.0)
        print(f'  peer.py: Peer{self.peer_id} listening on port {self.port + self.peer_id}')

        handler_threads = [] # stores threads created to handle other peers
        
        # Listen for requests from other peers and create threads to handle them
        while self.is_running:
            try:
                conn, addr = self.listener_socket.accept()
                thread = threading.Thread(target=self.handle_peer_request, args=(conn, addr))
                handler_threads.append(thread)
                thread.start()

            except socket.timeout:
                continue

            except OSError as e:
                print(f'  peer.py: accept() failed with OSError: {e}')
                break
        
        # Join all active threads with other peers
        for thread in handler_threads:
            thread.join()


    def handle_peer_request(self, peer_socket, addr):
        """
            Description:
                Waits for messages from the peer. Each message has an operation number corresponding to a specific action.
                It continuously performs the operations requested until the connection is closed or the socket times out after
                4 seconds.


            Inputs: 
                peer_socket - socket for communicating with the peer that initiated an interaction with this peer
                       addr - tuple (ip_addr, port) with the ip address (string) and the port number (int) of the peer
                              who initiated the interaction with this peer 

            Operations:
                       NULL - closes connection to the peer
                          2 - sends data to the peer

        """

        print(f'  peer.py: Peer{self.peer_id} received connection from {addr}')
        peer_socket.settimeout(4.0)

        while True:
            # recieve message from the peer and perfrom the requested operation
            try: 
                data = peer_socket.recv(1024).decode('utf-8')
                
                # close the connection on NULL message
                if not data:
                    break
                print(f'  peer.py: Peer{self.peer_id} Received data from {addr}\n           data: {data}')

                # if data starts with "2", the peer is requesting file_data
                if data[0] == '2':
                    peer_socket.send(self.file_data.encode('utf-8'))
                    break

            # close the connection if close_peer is called or the socket times out
            except socket.timeout:
                continue
            except (OSError, ConnectionResetError) as e:
                print(f'  peer.py: Exception in handle_peer_request: {e}')
                break

        # close the connection to the peer
        peer_socket.close()
        print(f'  peer.py: Peer{self.peer_id} peer_socket closed')


    def get_peer_id(self):
        return self.peer_id


    def create_server_socket(self):
        """
            Creates a socket specifically for communicating with the central server

        """

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(2)
        print(f'  peer.py: Created socket for Peer{self.peer_id}')


    def connect_to_server(self):
        """
            Connects the peer to the central server using the designated server_socket
        """

        self.server_socket.connect((self.host, self.port))
        print(f"  peer.py: Peer {self.peer_id} connected to server at {self.host}:{self.port}")


    def send_message(self, message):
        """
            Description: 
                Send a message to the server without waiting for or expecting a response
                Prepend 1 to the message so the server knows not to send a response to the message
            
            Input:
                message - Stores the value of the message that will be sent to the server

        """

        if self.server_socket:
            message = '1' + message
            self.server_socket.send(message.encode('utf-8'))
            print(f'  peer.py: Peer{self.peer_id} sent message to server: {message[1:]}')

        else:
            raise Exception(f'  peer.py: Peer{self.peer_id} is not connected to a server.')


    def verify_data(self, data):
        """
            TODO: Rewrite method using hashing functions

            Description:
                Returns True if the data passed in is valid and not corrupt
                Returns False otherwise
            
            Input:
                data - the data that needs to be validated
            
        """

        if data == '<server_data_here>':
            return True
        return False


    def req_chunk(self):
        """
            TODO: 
                - If the data received is invalid, wait for another address from the server to attempt to download the data from
                  a different peer or simply download the data from the server itself
                - Add an argument that specifies which chunk of data to request

            Description:
                The peer will reach out to the server to download its desired data.

                If the server cannot find another peer that has the data it will give the data directly to the peer.

                If the server knows of another peer with the desired data, the server will send back the ip address and
                port number of that peer's listener_socket. This peer will then reachout to that peer to request the data.

                After the data is received, it is verified with the verify_data function and the server is notified if the
                data received was valid or not before closing the connection to the peer.
            
            Outgoing OpCodes (messages sent by the peer):
                0 - there are no peers with the data, so the server has sent the data over
                1 - a peer with the data was found, so the server has sent the address of that peer
                2 - tell the server that the chunk was successfuly received

            Incoming OpCodes (messages received by the server):
                2 - request data from another peer


        
        """

        # If the server_socket is closed, throw an exception
        if self.server_socket:
            print(f'  peer.py: Peer{self.peer_id} requesting data')

            # Prepend 0 to tell the server this peer is requesting data
            # Send the server the port of the listener_socket (self.port + self.peer_id)
            message = '0' + str(self.peer_id) + str(self.port + self.peer_id) 
            self.server_socket.send(message.encode('utf-8'))

            # wait for response from the server
            server_data = self.server_socket.recv(1024).decode('utf-8')
            print(f'  peer.py: Peer{self.peer_id} received data from server\n           data: {server_data}')
            
            # If the response begins with 0, the following data in the message is the required chunk
            if server_data[0] == '0':
                self.file_data += server_data[1:]
                if self.verify_data(self.file_data):
                    self.server_socket.send('2'.encode('utf-8'))
            
            # If server_data starts with "1", then this peer must get the data from another peer
            # The ip and port number of that peer's listening_socket is given in the server's message after the 1
            elif server_data[0] == '1':
                peer_ip, peer_port = server_data[1:].split(':')[0], server_data[1:].split(':')[1]
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Connect to the peer and download the data from them
                try:
                    print(f'  peer.py: Peer{self.peer_id} connected to peer [{peer_ip}:{peer_port}]')
                    peer_socket.connect((peer_ip, int(peer_port)))
                    peer_socket.send('2'.encode('utf-8'))
                    self.file_data += peer_socket.recv(1024).decode('utf-8') # record the data from the peer
                    print(f'  peer.py: Peer{self.peer_id} now has file_data: {self.file_data}')


                except ConnectionRefusedError:
                    print(f'  peer.py: Peer{self.peer_id} failed to connect to peer [{peer_ip}:{peer_port}]')
                finally:
                    peer_socket.close()
                    print(f'  peer.py: Peer{self.peer_id} closed socket with peer [{peer_ip}:{peer_port}]')


                # verify the integrity of the data
                if self.verify_data(self.file_data):
                    self.server_socket.send('2'.encode('utf-8')) # tell the server the data was recieved
                else:
                    #TODO: if invalid data is received, wait for another response from server (either another ip address or the file_data)
                    print(f'  peer.py: Peer{self.peer_id} received invalid data from peer [{peer_ip}:{peer_port}]')
                    self.server_socket.send('0'.encode('utf-8'))

        else:
            raise Exception('  peer.py: Peer is not connected to a server.')


    def close_peer(self):
        """
            Description:
                Call this when the peer has finished all of its tasks and is ready to disconnect from the server.
                This closes down all of its sockets and sets is_running to false.
                Consequently, all threads running being run by this peer will be terminated.

        """
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
