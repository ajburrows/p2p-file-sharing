import threading
import hashlib
import socket
import time
import os

CHUNK_SIZE = 1024
DOWNLOAD_QUEUE_LEN = 3


OPCODE_REQ_CHUNK_FROM_SERVER = '0'
OPCODE_REQ_CHUNK_FROM_PEER = '1'
OPCODE_UPLOAD_FILE_DATA = '2' # Peer tells the server what files it has - sends file's name and its number of chunks
OPCODE_DOWNLOAD_FILE_FROM_SERVER = '3'
OPCODE_SEND_CHUNK_TO_PEER = '4'
OPCODE_CHUNK_DOWNLOAD_SUCCESS = '5'
OPCODE_FAILURE = '6'
OPCODE_CLOSING_CONNECTION_TO_SERVER = '7'
OPCODE_SEND_CHUNK_HASH_TO_SERVER = '8'
OPCODE_REQ_CHUNK_HASH = '9'
OPCODE_DOWNLOAD_COMPLETE = 'a'
OPCODE_REQUEST_FILE_LIST = 'b'

class DemoPeer:
    def __init__(self, peer_id, host, port, files_dir, malicious=False, demo_peer=False):
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
                      malicious - a boolean where if True, this peer will intentionally modify data to give incorrect chunks that should be discarded by peers 

        """

        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.files_dir = files_dir
        self.server_socket = None
        self.listener_socket = None
        self.is_running = True
        self.file_data = ''
        self.files = {} # format: {file_name_1: {chunk_1: 'str1', chunk2: 'str2', ...}, file_name_2: {}, ...}
        self.req_threads = []
        self.needed_file_chunks = {}
        self.malicious = malicious
        self.download_threads = []
        self.demo_peer = demo_peer


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

        handler_threads = [] # stores threads created to handle other peers
        
        # Listen for requests from other peers and create threads to handle them
        while self.is_running:
            try:
                conn, addr = self.listener_socket.accept()
                thread = threading.Thread(target=self.handle_peer_request, args=(conn, addr))
                handler_threads.append(thread)
                thread.start()
                time.sleep(0.1)

            except socket.timeout:
                continue

            except OSError as e:
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

        #print(f'  peer.py: Peer{self.peer_id} received connection from {addr}')
        peer_socket.settimeout(4.0)

        # Continuously listen for messages from the connected peer and perfrom the requested operation
        while True:
            try: 
                message_length = self.get_message_length(peer_socket)
                #print(f' peer.py: Peer{self.peer_id} received message of length: ({message_length})')
                
                # close the connection on NULL message
                if not message_length:
                    break

                peer_message = peer_socket.recv(message_length).decode('utf-8')
                #print(f'  peer.py: Peer{self.peer_id} Received message from {addr}\n           message: {peer_message}\n           msg_length: {message_length}')

                # if data starts with "2", the peer is requesting file_data
                if peer_message[0] == OPCODE_REQ_CHUNK_FROM_PEER:
                    # message format: OPCODE_REQ_CHUNK_FROM_PEER + '#' + file_name + '#' + chunk_num
                    #peer_socket.send(self.file_data.encode('utf-8'))
                    file_name, chunk_num = peer_message.split('#')[1], int(peer_message.split('#')[2])
                    self.send_chunk_to_peer(peer_socket, file_name, chunk_num)
                    break

            # close the connection if close_peer is called or the socket times out
            except socket.timeout:
                continue
            except (OSError, ConnectionResetError) as e:
                break

        # close the connection to the peer
        peer_socket.close()


    def send_chunk_to_peer(self, peer_socket, file_name, chunk_num):
        """
            Description - when a peer connects to this peer to request a file chunk, this method sends the chunk in a utf-8 message. It also prepends the length of that
                          message so the peer knows how many bytes to read

            Input
                peer_socket - the socket connection between this peer and the peer requesting the file chunk
                  file_name - the name of the file whose chunk is being requested
                  chunk_num - the chunk id within the file
        """
        chunk = self.files[file_name][chunk_num]

        # if this peer is malicious, modify the data
        if self.malicious:
            chunk = 'INVALID_'

        # send the message and its length
        message = OPCODE_SEND_CHUNK_TO_PEER + '#' + chunk
        message = message.encode('utf-8')
        message_length = str(len(message)) + '#'

        peer_socket.send(message_length.encode('utf-8'))
        peer_socket.send(message)
        return


    def create_server_socket(self):
        """
            Description - Creates a socket specifically for communicating with the central server
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def upload_file_data(self):
        """
            Description:
                Send a message to the server telling it what files this peer has by giving it a string containing the name of each
                file in self.files as well as the number of chunks that file is broken into.

                The string uses the # character to tell the server when the file_name and num_chunks values end.
        """
        message = self.make_message_header(OPCODE_UPLOAD_FILE_DATA)
        for file_name in self.files:
            file_name_length = str(len(file_name))
            num_chunks = str(len(self.files[file_name]))
            message += file_name_length + '#' + file_name + num_chunks + '#' 
        
        message = message.encode('utf-8')
        message_length = str(len(message)) + '#'
        self.server_socket.send(message_length.encode('utf-8'))
        self.server_socket.send(message)


    def send_server_message(self, socket, opcode, msg_content):
        """
            Description - when messages are sent, they must have the length of the encoded message prepended to it. This lets the receiver know how many bytes to read.
                          This method takes the message that should be sent as well as the socket, encodes it, prepends the length, and sends it along the socket.

            Inputs
                     socket - the connection socket between this peer and whoever is receiving the message
                     opcode - the OPCODE tells the recipient what the purpose of the message is
                msg_content - the data that is being sent
        """
        message = self.make_message_header(opcode)
        message += msg_content
        message = message.encode('utf-8')
        message_length = str(len(message)) + "#"
        socket.send(message_length.encode('utf-8'))
        socket.send(message)


    def upload_chunk_hashes(self):
        """
            Loop through every chunk for every file that this peer wants to share with the network. Calculate the hash for each chunk
            and send that to the server.
        """

        for file_name in self.files:
            chunk_set = self.files[file_name]
            for chunk_num in chunk_set:
                # Get the hash of the current chunk
                chunk = chunk_set[chunk_num]
                chunk_hex_dig = self.hash_chunk(chunk)
                message = file_name + "#" + str(chunk_num) + "#" + chunk_hex_dig

                # Send the hash to the server
                self.send_server_message(self.server_socket, OPCODE_SEND_CHUNK_HASH_TO_SERVER, message)


    def hash_chunk(self, chunk):
        """
            Description - this takes a chunk and returns its sha256 hex digest

            Inputs
                chunk - the chunk being hashed
        """
        encoded_chunk = chunk.encode('utf-8')
        chunk_hash_obj = hashlib.sha256()
        chunk_hash_obj.update(encoded_chunk)
        chunk_hex_dig = chunk_hash_obj.hexdigest()

        return chunk_hex_dig


    def initialize_files(self):
        """
            Description:
                The files that peers share with the network are stored in a single directory that is held in self.files_dir.
                This method loops through each of the files in that directory and breaks the files into chunks. The chunks
                are stored in the self.files dictionary.

        """

        for file in os.listdir(self.files_dir):
            # Create full path to the entry
            full_path = os.path.join(self.files_dir, file)
            # Check if the entry is a file
            if os.path.isfile(full_path):
                self.files[file] = self.file_to_chunks(full_path, CHUNK_SIZE)
        

    def file_to_chunks(self, file_path, chunk_size):
        """
            Description - breaks a file's contents up into chunks and returns a dictionary containing them.

            Inputs:
                file_path - root path of the directory containing files for this peer to upload.
                chunk_size - the files will be split up into chunks of this size in bytes

            Outputs:
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


    def make_message_header(self, opcode):
        """
            Every message sent to the server should have a header containing:
                1) OPCODE
                2) Peer's ID
                3) Peer's listening port number

            This method makes that header using the OPCODE passed in
        """
        return opcode + str(self.peer_id) + '#' + str(self.port + self.peer_id) + '#'


    def connect_to_peer(self, peer_ip, peer_port):
        """
            Description - create a socket to communicate with the peer whose information is passed in. If the connection is successful, the socket is returned.
        """
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            peer_socket.connect((peer_ip, peer_port))
        except ConnectionRefusedError:
            print(f'  peer.py: Peer{self.peer_id} failed to connect to peer [{peer_ip}:{peer_port}]')
        return peer_socket


    def req_chunk(self, file_name, chunk_num, peer_ip, peer_port):
        """
            Description - the peer will connect to the specified peer and request a single chunk from that peer. When the chunk is downloaded
                          it verifies its integrity by comparing its hash with the verified hash on the server. If it passes this test,
                          then the chunk is stored.
            
            Inputs
                file_name - the name of the file whose chunk is being requested
                chunk_num - the identifier of the specific chunk being requested
                  peer_ip - the ip address of the peer who the chunk is being downloade from
                peer_port - the port number being used to download the chunk from the peer
        """

        if self.server_socket:

            # Connect to the peer and download the data from them
            peer_socket = self.connect_to_peer(peer_ip, peer_port)
            time.sleep(0.5)
            

            # try to download the chunk from the peer
            try:
                # message format: opcode # file_name # chunk_num
                message = OPCODE_REQ_CHUNK_FROM_PEER + '#' + file_name + '#' + str(chunk_num)
                message = message.encode('utf-8')
                message_length = str(len(message)) + '#'
                peer_socket.send(message_length.encode('utf-8'))
                peer_socket.send(message)
                print(f'  peer.py: Peer{self.peer_id} requested chunk ({chunk_num}) from peer [{peer_ip}:{peer_port}]')#\n           message: {message}')

                response_length = self.get_message_length(peer_socket) # peer is sending back "12" and it's breaking under get_message_length
                peer_response = peer_socket.recv(response_length).decode('utf-8')

                # ensure the opcode is correct
                if peer_response[0] != OPCODE_SEND_CHUNK_TO_PEER:
                    print(f'  peer.py: ERROR Peer{self.peer_id} requested chunk from peer[{peer_ip}:{peer_port}], but received wrong opcode: {peer_response[0]}')
                else:
                    # Make sure the chunk was not tampered with by a malicious peer
                    chunk = peer_response.split('#')[1]
                    if self.verify_chunk_integrity(chunk, file_name, chunk_num) == True:

                        # store the chunk that was received
                        self.files[file_name][chunk_num] = chunk # store the chunk data
                        self.needed_file_chunks[file_name].remove(chunk_num) # update needed chunks

                        # notify the server that this peer has the chunk and can thus share it with other peers
                        server_message = OPCODE_CHUNK_DOWNLOAD_SUCCESS + '#' + peer_ip + ':' + str(peer_port) + '#' + str(chunk_num)
                        server_message = server_message.encode('utf-8')
                        server_message_length = str(len(server_message)) + '#'
                        self.server_socket.send(server_message_length.encode('utf-8'))
                        self.server_socket.send(server_message)
                        print(f'  peer.py: Peer{self.peer_id} received chunk ({chunk_num})\n')
                    
                    else:
                        print(f'  peer.py: discarding chunk ({chunk_num}) - hashes mismatched')
                        server_message = OPCODE_FAILURE + '#' + peer_ip + ':' + str(peer_port) + '#' + str(chunk_num)
                        server_message = server_message.encode('utf-8')
                        server_message_length = str(len(server_message)) + '#'
                        self.server_socket.send(server_message_length.encode('utf-8'))
                        self.server_socket.send(server_message)

            except:
                print(f'  peer.py: Peer{self.peer_id} failed to receive chunk ({chunk_num}) from peer [{peer_ip}:{peer_port}]')
            finally:
                peer_socket.close()
        else:
            raise Exception('  peer.py: Peer is not connected to a server.')


    def verify_chunk_integrity(self, chunk_received, file_name, chunk_num):
        """
            Description - this calculates the hex digest of the given chunk then downloads the correct hex digest for that chunk from the server. If both digests are equal
                          then it returns True. Otherwise, it return False.
            
            Input
                chunk_received - the data that is being verified
                     file_name - the name of the file that the chunk belongs to
                     chunk_num - the identifier of the chunk within the file
        """
        # create new socket to communicate with server
        new_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_server_socket.connect((self.host, self.port))

        # get the correct chunk hash from the server
        request_message = file_name + '#' + str(chunk_num)
        self.send_server_message(new_server_socket, OPCODE_REQ_CHUNK_HASH, request_message)
        time.sleep(0.05)
        message_length = self.get_message_length(new_server_socket)
        original_hash = new_server_socket.recv(message_length).decode('utf-8')

        # hash the chunk that was received from the peer
        received_hash = self.hash_chunk(chunk_received)

        # compare the two
        new_server_socket.close()
        if original_hash == received_hash:
            return True
        return False


    def get_message_length(self, conn):
        """
            Description - when reading a message from on a connection, the peer needs to know how long that message is. The length in bytes is prepended to the beginning of
                          every message and ends with a '#'. This reads one byte at a time until the '#' is reached, then returns the lenght of the message in bytes as an int.
            
            Input
                conn - the socket that is being read from.
        """
        cur_substring = ''
        while True:
            byte = conn.recv(1).decode('utf-8')
            if byte == '#':
                break
            cur_substring += byte
        if cur_substring:
            return int(cur_substring)
        else:
            return None


    def download_file_thread(self, file_name):
        # This method starts up a new thread to download an entire file
        download_thread = threading.Thread(target=self.download_file, args=([file_name]))
        download_thread.start()


    def download_file(self):
        """
            Description:
                The peer tells the server it wants a file. The server will then repeatedly send  the chunk number that should be 
                downloaded and the contact information of a peer with that chunk. This will continue until every chunk has been
                downloaded or there are no peers left on the network with the needed chunks.

                req_chunk_message = chunk_num + # + peer_ip_addr + # + peer_port_num

            Inputs:
                file_name - this is the name of the file that the peer wants to download
        """

        def get_req_chunk_info(message):
            # Extracts the chunk_num and the peer's ip address and port number from message
            message_list = message.split("#")
            chunk_num = int(message_list[0])
            peer_ip_addr = message_list[1]
            peer_port_num = int(message_list[2])
            return chunk_num, peer_ip_addr, peer_port_num

        file_name = input("Enter the file you want to download: ") 
        print(f'  peer.py: Peer{self.peer_id} downloading file: {file_name}')

        # tell the server which file this peer wants
        message = self.make_message_header(OPCODE_DOWNLOAD_FILE_FROM_SERVER) + file_name
        message = message.encode('utf-8')
        message_length = str(len(message)) + '#'
        self.server_socket.send(message_length.encode('utf-8'))
        self.server_socket.send(message)

        # Read how many chunks are in the file 
        message_length = self.get_message_length(self.server_socket)
        num_chunks = int(self.server_socket.recv(message_length).decode('utf-8'))

        #Create space to store the file data
        chunks_dict = {} # a dictionary to track the file data {chunk_1: "1st 8 bytes", chunk_2: "2nd 8 bytes", ...}
        needed_chunks = set() # a set to track which chunks still need to be downloaded. When it's empty, the download is complete
        for chunk_num in range(num_chunks):
            chunks_dict[chunk_num] = ""
            needed_chunks.add(chunk_num)
        self.files[file_name] = chunks_dict
        self.needed_file_chunks[file_name] = needed_chunks


        while len(self.needed_file_chunks[file_name]) > 0:
            # read the chunk location info
            message_length = self.get_message_length(self.server_socket)
            req_chunk_message = self.server_socket.recv(message_length).decode('utf-8')

            if req_chunk_message == OPCODE_DOWNLOAD_COMPLETE:
                break

            chunk_num, peer_ip, peer_port = get_req_chunk_info(req_chunk_message)

            # start a new thread to download that chunk
            req_thread = threading.Thread(target=self.req_chunk, args=(file_name, chunk_num, peer_ip, peer_port))
            req_thread.start()
            self.req_threads.append(req_thread)
        
        # join all the threads that were used to download a chunk from a peer
        for thread in self.req_threads:
            thread.join()

        self.write_file_from_chunks(file_name)


    def write_file_from_chunks(self, file_name):
        """
            Description - Once all the chunks of a file have been downloaded, this method iterates through them sequentially and writes the data into a local file.

            Input
                file_name - the name of the file that has just been downloaded
        """
        chunk_dict = self.files[file_name]
        output_file_path = self.files_dir + '/' + file_name
        with open(output_file_path, 'w') as output_file:
            for chunk_number in sorted(chunk_dict.keys()):
                output_file.write(chunk_dict[chunk_number]) # Write each chunk's data to the file
        print(f'  peer.py: Peer{self.peer_id} has downloaded {file_name} to {output_file_path}')


    def close_peer(self):
        """
            Description:
                Call this when the peer has finished all of its tasks and is ready to disconnect from the server.
                This closes down all of its sockets and sets is_running to false.
                Consequently, all threads running being run by this peer will be terminated.

        """
        if self.server_socket:
            message = OPCODE_CLOSING_CONNECTION_TO_SERVER
            message_length = '1#'
            self.server_socket.send(message_length.encode('utf-8'))
            self.server_socket.send(message.encode('utf-8'))
            self.server_socket.close()
        if self.listener_socket:
            self.listener_socket.close()

        self.is_running = False


    def run_in_background(self):
        listening_thread = threading.Thread(target=self.start_listening)
        listening_thread.start()
        print("listening thread created") 


    def request_file_list(self):

        # send request to server
        message = self.make_message_header(OPCODE_REQUEST_FILE_LIST)
        message = message.encode('utf-8')
        message_length = str(len(message)) + '#'
        self.server_socket.send(message_length.encode('utf-8'))
        self.server_socket.send(message)

        # collect data from server
        response_length = self.get_message_length(self.server_socket)
        file_data = self.server_socket.recv(response_length).decode('utf-8')

        # print it to the console
        print(f'request_file_list data:\n{file_data}')

        file_names = file_data.split('#')
        for i in range(len(file_names)):
            if file_names[i] != '':
                print(f'{i}:  {file_names[i]}')


def demo_peer_thread_function(peer): 
    """
        Commands:
            c - connect to server
            q - close
            u - upload files
            f - get a list of files from the server
            d - download a file

    """

    peer.run_in_background()
    userInput = ''
    while userInput != 'q':
        userInput = input("Enter a command: ")
        if userInput == 'c':
            peer.connect_to_server()
            print("Connected to server")
        if userInput == 'q':
            peer.close_peer()
            break
        if userInput[0] == 'u':
            peer.initialize_files()
            peer.upload_file_data()
            peer.upload_chunk_hashse()
        if userInput[0] == 'f':
            peer.request_file_list()
        if userInput[0] == 'd':
            peer.download_file()



if __name__ == '__main__':
    #start_demo()
    demo_peer = DemoPeer(5, '127.0.0.1', 12345, '/home/ajburrows/projects/p2p-file-sharing-lab1/files5', False, True)
    demo_peer.create_server_socket()
    demo_peer_thread_function(demo_peer)

