import socket
import threading
import random
import time


DOWNLOAD_QUEUE_LEN = 3

OPCODE_RECORD_FILE_DATA = '3' # Received by peers when they connect and tell the server what files they want to share
OPCODE_FILE_REQUEST_FROM_PEER = '4' # Received when a peer is requesting to download a file
OPCODE_CHUNK_DOWNLOAD_SUCCESS = '5'
OPCODE_FAILURE = '6'
OPCODE_CLOSING_CONNECTION_TO_SERVER = '7'
OPCODE_SEND_CHUNK_HASH_TO_SERVER = '8'
OPCODE_REQ_CHUNK_HASH = '9'
OPCODE_DOWNLOAD_COMPLETE = 'a'
OPCODE_REQUEST_FILE_LIST = 'b'

requested_data = '<server_data_here>'
peers = {} # {peer_id:(server_addr, listening_addr)} --> addr stored as (ip_addr, port_number)
data_holders = {} # {data_hash:(peer_id1, peer_id2, peer_id3, ...)} --> peer IDs stored in set

file_holders = {} # {file1_name: {chunk_1: (peer_id1, peer_id2, ...), chunk_2: (peer_id1, peer_id2, ...)}, file2_name: {...}, ...}
                  # ^--> dictionary of file names. Within each file there is another dictionary containing the chunk and a set of
                  #      which peers have that chunk. The number of chunks in a file can be found by dining the length of the
                  #      set stored under the file_name
                  #      file_name is a string, the chunk number is an int, and the peer IDs are ints

chunk_hashes = {} # {file1_name: {chunk_1: 'hex_dig', chunk_2: 'hex_dig', ...}, file2_name: {...}, ...}
                  # ^--> dictionary of the file names (strings) as the first key layer. Under the filename is a dictionary of key
                  #      value pairs. Each key is a chunk in that file and the value is the hex digest of that chunk

def get_message_length(peer_socket):
    """
        Description - before peers send messages, they send the length of the message followed by a '#' sign. This loops through the
                      data in the peer_socket one character at a time until the '#' sign is reached. The '#' is ignored, but everything
                      before it will be form an integer that represents the length of the peer's message in bytes.
    """

    cur_substring = ''
    while True:
        byte = peer_socket.recv(1).decode('utf-8')
        if byte == '#':
            break
        cur_substring += byte
    if cur_substring:
        return int(cur_substring)
    else:
        return None


def get_peer_contact_info(message):
    """
        Description - when peers send messages to the server they include their contact information This is the peer's ID and the port
                      number of the socket it uses to listen for request from other peers. These values are seperated by a '#' sign,
                      so it iterates through the characters in the message to pull out the id and port number.
        
    """

    cur_substring = ''
    peer_id = None
    peer_port = None

    # get peer_id
    i = 0
    while i < len(message):
        if message[i] != '#':
            cur_substring += message[i]
        else:
            i += 1
            break
        i += 1
    peer_id = int(cur_substring)
    
    # get peer's listening port number
    cur_substring = ''
    while i < len(message):
        if message[i] != '#':
            cur_substring += message[i]
        else:
            i += 1
            break
        i += 1

    peer_port = int(cur_substring)
    return peer_id, peer_port, message[i:]


def record_file_data(message, peer_id):
    """
        Description - peers tell the server information about the files they want to share on the network. The information is stored
                      in message and includes the file name and number of chunks in the file. The peer id is used so the server can
                      pull up this peer's contact information in case another peer wants to request the chunk number from them.

        Inputs
            message - contains the file information formatted as file_name_length + '#' + file_name + '#' + num_chunks
            peer_id - the ID the peer that has the file. This is used to access their listener port number in the peers dictionary

    """

    i = 0

    # loop through the different files in the message
    while i < len(message):
        # get length of the file name 
        cur_substring = ''
        while i < len(message):
            if message[i] == '#':
                i += 1
                break
            cur_substring += message[i]
            i += 1

        file_name_length = int(cur_substring)
        cur_file_name = message[i:i+file_name_length] # store the substring of message that contains the file name

        # get number of chunks in the file
        i += file_name_length
        cur_substring = ''
        while i < len(message):
            if message[i] == '#':
                i += 1
                break
            cur_substring += message[i]
            i += 1
        num_chunks = int(cur_substring)


        # initialize/ update the file's entry in the files dictionary
        if cur_file_name in file_holders:
            chunk_set = file_holders[cur_file_name]
            for chunk_num in chunk_set:
                chunk_set[chunk_num].add(peer_id)
        else:
            file_holders[cur_file_name] = {}
            chunk_set = file_holders[cur_file_name]
            for j in range(num_chunks):
                chunk_set[j] = set()
                chunk_set[j].add(peer_id)
        if cur_file_name not in chunk_hashes:
            chunk_hashes[cur_file_name] = {}
            for j in range(num_chunks):
                chunk_hashes[cur_file_name][j] = ''
    
    #print(f'server.py: File data recorded from Peer{peer_id}\n           file_holders: {file_holders}')
    

def handle_peer(conn, addr):
    """
        Description - wait for messages from the peer. Determine the message's opcode, then call the corresponding function. This
                      continues to run until the peer disconnects or the server shuts down.

        Inputs
            conn - the socket that the server uses to communicate with the peer
            addr - the ip and port number of the peer this thread is communicating with. This port number is an ephemoral port number,
                   not the peer's listening port number. The listening port number is gotten from the peer when it connects.
    """

    # Function to handle communication with a single peer
    #print(f"server.py: New connection from {addr}")
    peer_id = None
    while True:
        message_length = get_message_length(conn)
        message = conn.recv(message_length).decode('utf-8')
        operation = message[0]

        #print(f"server.py: hand_peer received message: {message}")

        # Close the server if the message is NULL (empty)
        if operation == OPCODE_CLOSING_CONNECTION_TO_SERVER:
            #print('\nBLUEBERRY\n')
            if peer_id in peers:
                print(f"server.py: Peer{peer_id} disconnected.")
                del peers[peer_id]
                for file_name in file_holders:
                    for chunk_num in file_holders[file_name]:
                        if peer_id in file_holders[file_name][chunk_num]:
                            file_holders[file_name][chunk_num].remove(peer_id)
                print(f'server.py: Peer{peer_id} removed from file_holders: {file_holders}')
            else:
                print(f"Null message recieved from unknown peer")
            break


        peer_id, peer_listening_port, message = get_peer_contact_info(message[1:])
        #print(f'\nserver.py: TESTING MESSAGE\n           peerID: {peer_id}\n           portNum: {peer_listening_port}\n           message: {message}\n')
        if peer_id not in peers:
            peers[peer_id] = (addr, (addr[0], peer_listening_port))
            #print(f'server.py: start handle_peer, peers: {peers}')
    
        if operation == OPCODE_REQ_CHUNK_HASH:
            #print(f"server.py: sending chunk hash: {message}")
            send_chunk_hash(message, conn)

        # Peer is telling the server what files it is willing to share
        elif operation == OPCODE_RECORD_FILE_DATA:
            record_file_data(message, peer_id)

        elif operation == OPCODE_SEND_CHUNK_HASH_TO_SERVER:
            record_chunk_hash(message)

        # Peer is telling the server what file it wants to download
        elif operation == OPCODE_FILE_REQUEST_FROM_PEER:
            send_file(conn, peer_id, message)
        
        elif operation == OPCODE_REQUEST_FILE_LIST:
            send_file_list(conn)


    conn.close()
    #print(f'server.py: end of handle_peer, peers: {peers}')


def send_file_list(conn):
    """
        Description - when DemoPeer requests a list of files that it can download, this is used to iterate through the files on the
                      network, determine if all the file's chunks are available, and then add that file's name to a message that is
                      sent to the peer formatted as:
                                    
                                    file1_name + '#' + file2_name + '#' + file3_name + '#' ...
    """

    # iterate through files
    message = ''
    for file_name in file_holders:
        chunk_set = file_holders[file_name]
        file_complete = True

        # make sure ach of the chunks has at least one peer on the netowrk
        for chunk in chunk_set:
            if chunk_set[chunk] == None:
                file_complete = False
        if file_complete:
            message += file_name+'#'
    
    # send the file names to the peer
    message = message.encode('utf-8')
    message_length = str(len(message)) + '#'
    conn.send(message_length.encode('utf-8'))
    conn.send(message)


def send_chunk_hash(message, conn):
    """ 
        Description - When the peer needs to verify the integrity of the data it receives, it asks for the original chunk hash. 
                      These are stored in the chunk_hashes dictionary and are initialized when a peer first uploads a file.

        Inputs:
            message - formated as file_name + '#' + chunk_num, where file_name and chunk_num are the name of the file and the 
                      chunk number in that file that the peer wants the hash for.
               conn - the server's connection to the peer. This is used to send the hash back to the peer

    """

    #print(f"\nserver.py: send_chunk_hash message: {message}\n")
    message_parts = message.split('#')
    file_name = message_parts[0]
    chunk_num = int(message_parts[1])
    chunk_hash = chunk_hashes[file_name][chunk_num]
    chunk_hash = chunk_hash.encode('utf-8')
    message_length = str(len(chunk_hash)) + '#'
    conn.send(message_length.encode('utf-8'))
    #print(f'server.py: sent message_length: {message_length}')
    conn.send(chunk_hash)
    #print(f'server.py: sent chunk_hash: {chunk_hash}')


def record_chunk_hash(message):
    """
        Description - peers tell the server the hash digests of the chunks for files they are sharing. They do so by sending messages
                      formatted as file_name + '#' + chunk_num + '#' + chunk_hash. This splits the message on the '#' sign to extract
                      the hash as well as its corresponding chunk then stores that information in the chunk_hashes dictionary.

        Inputs
            message - this is the message sent by the peer (string)
    """
    message_parts = message.split('#')
    file_name = message_parts[0]
    chunk_num = int(message_parts[1])
    chunk_hash = message_parts[2]

    if not chunk_hashes[file_name][chunk_num]:
        chunk_hashes[file_name][chunk_num] = chunk_hash


def send_chunk2(conn, chunk_set, chunk_num):
    """
        Description:
            Randomely picks a peer who has the desired chunk (chunk_num) and sends that peer's contact info as well as the
            chunk number to the requester.

        inputs:
                 conn - the socket between the server and the peer requesting a file
            requester - the id of the peer requesting the file
            chunk_set - the set of chunks with the ids of peers who have each chunk
            chunk_num - the chunk within chunk_set that needs to be sent to the requester

    """

    # Randomly choose a peer who has the chunk
    peer_id = random.choice(list(chunk_set[chunk_num]))
    #print(f'TESTING: send_chunk choices: {chunk_set[chunk_num]}')

    # Get that peer's contact info
    peer_ip_addr = peers[peer_id][1][0]
    peer_port_num = peers[peer_id][1][1]
    message = str(chunk_num) + '#' + str(peer_ip_addr) + '#' + str(peer_port_num)
    message = message.encode('utf-8')
    message_len = str(len(message)) + '#'
    conn.send(message_len.encode('utf-8')) # tell the peer how many bytes it needs to read to capture the next message
    conn.send(message)
    #print(f'server.py: Server sending chunk-info to peer\n           message: {message}, length: {message_len}\n')


def find_rarest_chunk(file_name, needed_chunks, queued_chunks):
    """
        Description - search through the chunks that the peer still needs to download and select the one that has the fewest copies
                      on the network (the chunk whose set of peers that have the chunk is the smallest).

        Inputs
                file_name - the name of the file that is being downloaded (string)
            needed_chunks - the chunks that still have to be downloaded by the peer (set)
            queued_chunks - 
    """

    #print(f'FIND_RAREST_CHUNK:\nneeded_chunks: {needed_chunks}\nqueued_chunks: {queued_chunks}\n')
    chunk_set = file_holders[file_name]
    rarest = None
    for chunk_num in needed_chunks:
        if not rarest and chunk_num not in queued_chunks:
            rarest = [chunk_num, len(chunk_set[chunk_num])]
        elif rarest and len(chunk_set[chunk_num]) < rarest[1] and chunk_num not in queued_chunks:
            rarest = [chunk_num, len(chunk_set[chunk_num])]
    
    if rarest:
        return rarest[0]
    return None



def send_file(conn, requester_id, file_name):
    """
        Initialize a set of the chunks that the requester needs to download.
        Loop through that set to send chunks to the requester until there are no more chunks left for the requester to download
        Continuously track which chunks the requester has and update file_holders so other peers can download from them

    """

    if file_name not in file_holders:
        Exception(f'server.py: EXCEPTION - file {file_name} not in file_holders')
        return 

    chunk_set = file_holders[file_name]
    needed_chunks = set(chunk_set.keys())
    queued_chunks = set()

    # tell the peer how many chunks are in the file
    num_chunks_message = str(len(needed_chunks)).encode('utf-8')
    num_chunks_message_length = str(len(num_chunks_message)) + '#'
    conn.send(num_chunks_message_length.encode('utf-8'))
    conn.send(num_chunks_message)
    #print(f'server.py: Server sending num_chunks to Peer{requester_id}: {num_chunks_message}, len: {num_chunks_message_length}')

    while len(needed_chunks) > 0:
        chunk_num = find_rarest_chunk(file_name, needed_chunks, queued_chunks)
        # only queue up a certain number of chunks at a time (the number is stored in DOWNLOAD_QUEUE_LEN)
        if chunk_num != None and len(queued_chunks) < DOWNLOAD_QUEUE_LEN and chunk_num not in queued_chunks:
            queued_chunks.add(chunk_num)
            send_chunk2(conn, chunk_set, chunk_num)
            time.sleep(0.05) # give time for peer response to finish sending here
        else:
            # download_result format: OPCODE + '#' + PEER_ADDR + '#' + CHUNK_NUM --> PEER_ADDR is the ADDR of the peer that sent the chunk
            peer_message_length = get_message_length(conn)
            download_result = conn.recv(peer_message_length).decode('utf-8')
            #print(f'server.py: Server received message while waiting for chunks to download\n          message: {download_result}')

            if download_result[0] == OPCODE_CHUNK_DOWNLOAD_SUCCESS:
                # get downloaded chunk number
                downloaded_chunk = int(download_result.split('#')[2])

                # add this peer to the set of peers who have the chunk
                file_holders[file_name][downloaded_chunk].add(requester_id)

                # remove the chunk from the download queue
                queued_chunks.remove(downloaded_chunk)
                needed_chunks.remove(downloaded_chunk)


            elif download_result[0] == OPCODE_FAILURE:
                #print(f'server.py: peer FAILED to donwload chunk')
                downloaded_chunk = int(download_result.split('#')[2])
                queued_chunks.remove(downloaded_chunk)

            # triggers if the OPCODE was neither 0 or 1
            else:
                Exception('server.py: EXCEPTION invalid opcode from peer in send_file')
        #print('TESTING: for loop finished')
        outdated_queues = set()
        for chunk_num in queued_chunks:
            if requester_id in file_holders[file_name][chunk_num]:
                outdated_queues.add(chunk_num)
        
        for chunk_num in outdated_queues:
            queued_chunks.remove(chunk_num)

    #print("\n\nEXITING SEND FILE\n\n")
    print(f'TESTING: files {file_holders}')

    #send message to tell peer download is complete
    message = '1#' + OPCODE_DOWNLOAD_COMPLETE
    conn.send(message.encode('utf-8'))


# Close the peer connection
def close_server(conn):
    conn.close()


# Server setup to handle multiple peers
def start_server():
    """
        Description - create the socket that peers connect to. When peers do connect, a thread is created to run handle_peer for that
                      peer until it disconnects. This will continue to accept new connections from peers until the server terminates.
    """
    host = '127.0.0.1'  # Localhost
    port = 12345        # Non-privileged port

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to address and port
    server_socket.bind((host, port))

    # Listen for incoming connections
    server_socket.listen()
    print(f"server.py: Server listening on {host}:{port}")

    while True:
        # Accept a new connection from a peer
        conn, addr = server_socket.accept()

        # Start a new thread to handle the peer
        peer_thread = threading.Thread(target=handle_peer, args=(conn, addr))
        peer_thread.start()

if __name__ == '__main__':
    start_server()
