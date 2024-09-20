import socket
import threading
import os
import sys

requested_data = '<server_data_here>'
peers = {} # {peer_id:(server_addr, listening_addr)} --> addr stored as (ip_addr, port_number)
data_holders = {} # {data_hash:(peer_id1, peer_id2, peer_id3, ...)}

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

# Function to handle communication with a single peer
def handle_peer(conn, addr):
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
                break
            else:
                print(f"Null message recieved from unknown peer")

        operation = message[0]
        peer_id = message[1]
        if peer_id not in peers:
            peers[peer_id] = (addr, (addr[0], int(message[2:])))
            print(f'server.py: start handle_peer, peers: {peers}')
    

        # Send data to the peer
        if operation == '0':
            print(f'server.py: Data request received from Peer{peer_id}\n           Peer addrs: {peers[peer_id]}')
            send_chunk(conn, peer_id, message)
            data_holders[requested_data].add(peer_id)

        elif operation == '1':
            print(f'server.py: Message received from Peer{peers[addr]}\n           Peer addr: {addr}\n           Message: {message[1:]}\n')
    conn.close()
    print(f'server.py: end of handle_peer, peers: {peers}')


# Close the peer connection
def close_server(conn):
    conn.close()


def file_to_chunks(file_path, chunk_size):
    """
        inputs:
            file_path - root path of the directory containing files for the server to upload.
            chunk_size - the files will be split up into chunks of this size in bytes

        outputs:

    """
    chunk_dict = {}
    i = 0
    with open(file_path, 'rb') as file:
        while i >= 0:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            chunk_dict[i] = chunk
            i += 1

    return chunk_dict

# Server setup to handle multiple peers
def start_server(files_directory):
    host = '127.0.0.1'  # Localhost
    port = 12345        # Non-privileged port

    # break all files in the directory into chunks and store them in files
    files = {}
    for file in os.listdir(files_directory):
        # Create full path to the entry
        full_path = os.path.join(files_directory, file)
        # Check if the entry is a file
        if os.path.isfile(full_path):
            files[file] = file_to_chunks(full_path, 1024)
    print(f'server.py: files - {files}')

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
    if len(sys.argv) < 2:
        print("server.py: python server.py <files_directory>")
        sys.exit(1)
    files_directory = os.path.abspath(sys.argv[1])
    start_server(files_directory)
