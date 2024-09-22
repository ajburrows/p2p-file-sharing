import threading
import socket
import time
import os

OPCODE_REQ_CHUNK_FROM_SERVER = '0'
OPCODE_INVALID_DATA_RECEIVED = '0'
OPCODE_FILE_DATA_RECEIVED = '0'

OPCODE_SEND_SERVER_MESSAGE = '1'
OPCODE_PEER_ADDR_RECEIVED = '1'

OPCODE_REQ_CHUNK_FROM_PEER = '2'
OPCODE_VALID_DATA_RECEIVED ='2'

OPCODE_UPLOAD_FILE_DATA = '3' # Peer tells the server what files it has - sends file's name and its number of chunks
OPCODE_DOWNLOAD_FILE_FROM_SERVER = '4'

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
                          files - a dictionary that stores the files as chunks
                    req_threads - a list of the threads that are used to request chunks from other peers

        """

        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.files_dir = files_dir
        self.server_socket = None
        self.listener_socket = None
        self.is_running = True
        self.file_data = ''
        self.files = {}
        self.req_threads = []
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


    def create_server_socket(self):
        """
            Creates a socket specifically for communicating with the central server

        """

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(2)
        print(f'  peer.py: Created socket for Peer{self.peer_id}')


    def upload_file_data(self):
        """
            Description:
                Send a message to the server telling it what files this peer has by giving it a string containing the name of each
                file in self.files as well as the number of chunks that file is broken into.

                The string uses the # character to tell the server when the file_name and num_chunks values end.
        
        """
        # tell server what files I have (name of file + number of chunks)
        message = self.make_message_header(OPCODE_UPLOAD_FILE_DATA)
        for file_name in self.files:
            file_name_length = str(len(file_name))
            num_chunks = str(len(self.files[file_name]))

            # pound signs are a delimiter to tell the server when the file_name_length and num_chunks end
            message += file_name_length + '#' + file_name + num_chunks + '#' 
        
        print(f'  peer.py: Peer{self.peer_id} uploading file data to server\n           message: {message}')
        self.server_socket.send(message.encode('utf-8'))


    def initialize_files(self):
        """
            Description:
                The files that peers share with the network are stored in a single directory that is held in self.files_dir.
                This method loops through each of the files in that directory and breaks the files into chunks. The chunks
                are stored in the self.files dictionary.

        """

        # break all files in the directory into chunks and store them in files
        for file in os.listdir(self.files_dir):
            # Create full path to the entry
            full_path = os.path.join(self.files_dir, file)
            # Check if the entry is a file
            if os.path.isfile(full_path):
                self.files[file] = self.file_to_chunks(full_path, 8)
        #print(f'  peer.py: files - {self.files}')
        

    def file_to_chunks(self, file_path, chunk_size):
        """
            inputs:
                file_path - root path of the directory containing files for this peer to upload.
                chunk_size - the files will be split up into chunks of this size in bytes

            outputs:
                chunk_dict - a dictionary that enumerates the files chunks {1:'chunk1_data', 2:'chunk2_data', 3:'chunk3_data', ...}

        """

        chunk_dict = {}
        i = 0
        with open(file_path, 'r') as file:
            while i >= 0:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                chunk_dict[i] = chunk
                i += 1

        return chunk_dict


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
            message = self.make_message_header(OPCODE_SEND_SERVER_MESSAGE) + message
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


    def make_message_header(self, opcode):
        """
            Every message sent to the server should have a header containing:
                1) OPCODE
                2) Peer's ID
                3) Peer's listening port number

            This method makes that header using the OPCODE passed in
        """
        return opcode + str(self.peer_id) + '#' + str(self.port + self.peer_id) + '#'


    def req_chunk2(self):
        # If the server_socket is closed, throw an exception
        if self.server_socket:
            print(f'  peer.py: Peer{self.peer_id} requesting data')

            # Prepend 0 to tell the server this peer is requesting data
            # Send the server the port of the listener_socket (self.port + self.peer_id)
            message = self.make_message_header(OPCODE_REQ_CHUNK_FROM_SERVER)
            self.server_socket.send(message.encode('utf-8'))

            # wait for response from the server
            server_data = self.server_socket.recv(1024).decode('utf-8')
            print(f'  peer.py: Peer{self.peer_id} received data from server\n           data: {server_data}')
            
            # If the response begins with 0, the following data in the message is the required chunk
            if server_data[0] == OPCODE_FILE_DATA_RECEIVED:
                self.file_data += server_data[1:]
                if self.verify_data(self.file_data):
                    self.server_socket.send(self.make_message_header(OPCODE_VALID_DATA_RECEIVED).encode('utf-8'))
            
            # If server_data starts with "1", then this peer must get the data from another peer
            # The ip and port number of that peer's listening_socket is given in the server's message after the 1
            elif server_data[0] == OPCODE_PEER_ADDR_RECEIVED:
                peer_ip, peer_port = server_data[1:].split(':')[0], server_data[1:].split(':')[1]
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Connect to the peer and download the data from them
                try:
                    print(f'  peer.py: Peer{self.peer_id} connected to peer [{peer_ip}:{peer_port}]')
                    peer_socket.connect((peer_ip, int(peer_port)))
                    peer_socket.send(self.make_message_header(OPCODE_REQ_CHUNK_FROM_PEER).encode('utf-8'))
                    self.file_data += peer_socket.recv(1024).decode('utf-8') # record the data from the peer
                    print(f'  peer.py: Peer{self.peer_id} now has file_data: {self.file_data}')


                except ConnectionRefusedError:
                    print(f'  peer.py: Peer{self.peer_id} failed to connect to peer [{peer_ip}:{peer_port}]')
                finally:
                    peer_socket.close()
                    print(f'  peer.py: Peer{self.peer_id} closed socket with peer [{peer_ip}:{peer_port}]')


                # verify the integrity of the data
                if self.verify_data(self.file_data):
                    self.server_socket.send(self.make_message_header(OPCODE_VALID_DATA_RECEIVED).encode('utf-8')) # tell the server the data was recieved
                else:
                    #TODO: if invalid data is received, wait for another response from server (either another ip address or the file_data)
                    print(f'  peer.py: Peer{self.peer_id} received invalid data from peer [{peer_ip}:{peer_port}]')
                    self.server_socket.send(self.make_message_header(OPCODE_INVALID_DATA_RECEIVED).encode('utf-8'))

        else:
            raise Exception('  peer.py: Peer is not connected to a server.')


    def download_file(self, file_name):
        """
            Inputs:
                file_name - this is the name of the file that the peer wants to download

            Description:
                The peer tells the server it wants a file. The server will then repeatedly send  the chunk number that should be 
                downloaded and the contact information of a peer with that chunk. This will continue until every chunk has been
                downloaded or there are no peers left on the network with the needed chunks.

                req_chunk_message = chunk_num + # + peer_ip_addr + # + peer_port_num

        """
        def get_req_chunk_info(message):
            i = 0
            cur_substring = ''
            while i < len(message):

                # get the chunk number
                while i < len(message):
                    if message[i] == '#':
                        i += 1
                        break
                    cur_substring += message[i]
                    i += 1
                chunk_num = int(cur_substring)


                while i < len(message):
                    if message[i] == '#':
                        i += 1
                        break
                    cur_substring += message[i]
                    i += 1
                peer_ip_addr = cur_substring

                peer_port_num = message[i:]
                
            return chunk_num, peer_ip_addr, peer_port_num


        # tell the server which file this peer wants
        message = self.make_message_header(OPCODE_DOWNLOAD_FILE_FROM_SERVER) + file_name
        self.server_socket.send(message.encode('utf-8'))

        cur_substring = ''
        while True:
            byte = self.server_socket.recv(1).decode('utf-8')
            if byte == '#':
                break
            cur_substring += byte
        message_length = int(cur_substring)

        req_chunk_message = self.server_socket.recv(message_length).decode('utf-8')
        print(f'\nTESTING: req_chunk_message - {req_chunk_message}\n')
        chunk_num, peer_ip, peer_port = get_req_chunk_info(req_chunk_message)

        # start a new thread to download that chunk
        """
        thread = threading.Thread(target=self.handle_peer_request, args=(conn, addr))
        handler_threads.append(thread)
        thread.start()
        """
        req_thread = threading.Thread(target=self.req_chunk2, args=(file_name, chunk_num))
        req_thread.start()
        self.req_threads.append(req_thread)



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
            
            Incoming OpCodes (messages sent by the server and received by this peer):
                0 - there are no peers with the data, so the server has sent the data over
                1 - a peer with the data was found, so the server has sent the address of that peer

            Outgoing OpCodes (messages received by the server):
                0 - tell the server this peer wants the data, and send this peer's listening address
                0 - tell the server that invalid data was received
                2 - tell another peer that this peer wants the data
                2 - tell the server that the chunk was successfully received


        
        """

        # If the server_socket is closed, throw an exception
        if self.server_socket:
            print(f'  peer.py: Peer{self.peer_id} requesting data')

            # Prepend 0 to tell the server this peer is requesting data
            # Send the server the port of the listener_socket (self.port + self.peer_id)
            message = self.make_message_header(OPCODE_REQ_CHUNK_FROM_SERVER)
            self.server_socket.send(message.encode('utf-8'))

            # wait for response from the server
            server_data = self.server_socket.recv(1024).decode('utf-8')
            print(f'  peer.py: Peer{self.peer_id} received data from server\n           data: {server_data}')
            
            # If the response begins with 0, the following data in the message is the required chunk
            if server_data[0] == OPCODE_FILE_DATA_RECEIVED:
                self.file_data += server_data[1:]
                if self.verify_data(self.file_data):
                    self.server_socket.send(self.make_message_header(OPCODE_VALID_DATA_RECEIVED).encode('utf-8'))
            
            # If server_data starts with "1", then this peer must get the data from another peer
            # The ip and port number of that peer's listening_socket is given in the server's message after the 1
            elif server_data[0] == OPCODE_PEER_ADDR_RECEIVED:
                peer_ip, peer_port = server_data[1:].split(':')[0], server_data[1:].split(':')[1]
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # Connect to the peer and download the data from them
                try:
                    print(f'  peer.py: Peer{self.peer_id} connected to peer [{peer_ip}:{peer_port}]')
                    peer_socket.connect((peer_ip, int(peer_port)))
                    peer_socket.send(self.make_message_header(OPCODE_REQ_CHUNK_FROM_PEER).encode('utf-8'))
                    self.file_data += peer_socket.recv(1024).decode('utf-8') # record the data from the peer
                    print(f'  peer.py: Peer{self.peer_id} now has file_data: {self.file_data}')


                except ConnectionRefusedError:
                    print(f'  peer.py: Peer{self.peer_id} failed to connect to peer [{peer_ip}:{peer_port}]')
                finally:
                    peer_socket.close()
                    print(f'  peer.py: Peer{self.peer_id} closed socket with peer [{peer_ip}:{peer_port}]')


                # verify the integrity of the data
                if self.verify_data(self.file_data):
                    self.server_socket.send(self.make_message_header(OPCODE_VALID_DATA_RECEIVED).encode('utf-8')) # tell the server the data was recieved
                else:
                    #TODO: if invalid data is received, wait for another response from server (either another ip address or the file_data)
                    print(f'  peer.py: Peer{self.peer_id} received invalid data from peer [{peer_ip}:{peer_port}]')
                    self.server_socket.send(self.make_message_header(OPCODE_INVALID_DATA_RECEIVED).encode('utf-8'))

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

