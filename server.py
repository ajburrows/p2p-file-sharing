import socket
import threading


OPCODE_RECORD_FILE_DATA = '3' # Received by peers when they connect and tell the server what files they want to share
OPCODE_FILE_REQUEST_FROM_PEER = '4' # Received when a peer is requesting to download a file
OPCODE_SUCCESS = '5'
OPCODE_FAILURE = '6'

requested_data = '<server_data_here>'
peers = {} # {peer_id:(server_addr, listening_addr)} --> addr stored as (ip_addr, port_number)
data_holders = {} # {data_hash:(peer_id1, peer_id2, peer_id3, ...)} --> peer IDs stored in set

file_holders = {} # {file1_name: {chunk_1: (peer_id1, peer_id2, ...), chunk_2: (peer_id1, peer_id2, ...)}, file2_name: {...}, ...}
                  # ^--> dictionary of file names. Within each file there is another dictionary containing the chunk and a set of
                  #      which peers have that chunk. The number of chunks in a file can be found by dining the length of the
                  #      set stored under the file_name
                  #      file_name is a string, the chunk number is an int, and the peer IDs are ints

def send_chunk(peer_conn, peer_id, message):
    # Check if any peers on the network have the data already
    peer_addrs = peers[peer_id]
    if requested_data not in data_holders:
        data_holders[requested_data] = set()
        message = "0" + requested_data # prepend 0 so the peer knows it received the data
        peer_conn.send(message.encode('utf-8'))

        # wait for confirmation from peer that it sucessfuly recieved the data
        success = peer_conn.recv(1024).decode('utf-8')
        if success == "1":
            data_holders[requested_data].add(peer_id)
            print(f'server.py: send_chunk to peer{peer_id} succeeded\n           message: {message}')
        else:
            Exception(f'server.py: send_chunk failed\n           peer_addr: {peer_addrs[0]}\n           message: {message}')

    else:
        # loop through the peers who have the desired data until one successfuly sends the data to the peer_addr
        print(f"server.py: data_holders = {data_holders}")
        for cur_peer_id in data_holders[requested_data]:
            print(f'server.py: cur_peer_id: {cur_peer_id}')
            print(f'server.py: peers = {str(peers)}')
            message = "1" + str(peers[cur_peer_id][1][0]) + ":" + str(peers[cur_peer_id][1][1]) # prepend 1 so the peer knows it received the address of a peer with the data
            peer_conn.send(message.encode('utf-8'))
            success = peer_conn.recv(1024).decode('utf-8')
            if success == '2':
                data_holders[requested_data].add(peer_id)
                break


def get_peer_contact_info(message):
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
    
    print(f'server.py: File data recorded from Peer{peer_id}\n           file_holders: {file_holders}')


def handle_peer(conn, addr):
    # Function to handle communication with a single peer
    print(f"server.py: New connection from {addr}")
    peer_id = None
    while True:
        message = conn.recv(1024).decode('utf-8')

        # Close the server if the message is NULL (empty)
        if not message:
            if peer_id in peers:
                print(f"server.py: Peer{peer_id} disconnected.")
                del peers[peer_id]
                data_holders[requested_data].discard(peer_id)
            else:
                print(f"Null message recieved from unknown peer")
            break

        operation = message[0]
        peer_id, peer_listening_port, message = get_peer_contact_info(message[1:])
        #print(f'\nserver.py: TESTING MESSAGE\n           peerID: {peer_id}\n           portNum: {peer_listening_port}\n           message: {message}\n')
        if peer_id not in peers:
            peers[peer_id] = (addr, (addr[0], peer_listening_port))
            print(f'server.py: start handle_peer, peers: {peers}')
    

        # Send data to the peer
        if operation == '0':
            print(f'server.py: Data request received from Peer{peer_id}\n           Peer addrs: {peers[peer_id]}')
            send_chunk(conn, peer_id, message)
            data_holders[requested_data].add(peer_id)

        elif operation == '1':
            print(f'server.py: Message received from Peer{peers[addr]}\n           Peer addr: {addr}\n           Message: {message[1:]}\n')

        # Peer is telling the server what files it is willing to share
        elif operation == OPCODE_RECORD_FILE_DATA:
            record_file_data(message, peer_id)
        
        # Peer is telling the server what file it wants to download
        elif operation == OPCODE_FILE_REQUEST_FROM_PEER:
            send_file(conn, peer_id, message)


    conn.close()
    print(f'server.py: end of handle_peer, peers: {peers}')


def send_chunk2(conn, peer_id, chunk_set, chunk_num):
    """
        Takes the file_name, chunk_number, requester, and peer with the chunk.

        Tells the requester the chunk_number and peer contact so the requester and reach out to the peer to get that chunk

    """
    return

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

    for chunk_num in needed_chunks:
        # only queue up 4 concurrent chunk downloads at a time
        if len(queued_chunks) < 4:
            queued_chunks.add(chunk_num)
            send_chunk2(conn, requester_id, chunk_set, chunk_num)
        else:
            # download_result format: 'OPCODE' + 'CHUNK_NUM' + '#' + 'PEER_ID'. PEER_ID is the id of the peer that sent the chunk
            download_result = conn.recv(1024).decode('utf-8')

            # get downloaded chunk number
            downloaded_chunk = int(download_result.split('#')[0][1:])

            if download_result[0] == OPCODE_SUCCESS:
                # add this peer to the set of peers who have the chunk
                file_holders[file_name][downloaded_chunk].add(requester_id)

                # update the remaining chunks of the file that need to be downloaded
                needed_chunks.remove(downloaded_chunk)

                # remove the chunk from the download queue
                queued_chunks.remove(downloaded_chunk)


            elif download_result[0] == OPCODE_FAILURE:
                # the data was corrupted so remove the peer from the server's lists
                failed_peer_id = int(download_result.split('#')[1])
                del peers[failed_peer_id]
                file_holders[file_name][downloaded_chunk].discard(failed_peer_id)

                # try to download the chunk again
                send_chunk2(conn, requester_id, chunk_set, downloaded_chunk)

            # triggers if the OPCODE was neither 0 or 1
            else:
                Exception('server.py: EXCEPTION invalid opcode from peer in send_file')





# Close the peer connection
def close_server(conn):
    conn.close()


# Server setup to handle multiple peers
def start_server():
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
