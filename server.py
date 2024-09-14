import socket
import threading

requested_data = '<server_data_here>'
clients_dict = {} # {addr:client_id}
data_holders = {} # {data_hash:(conn1, conn2, conn3, ...)}

def send_chunk(peer_conn, peer_addr, message):
    # Check if any peers on the network have the data already
    if not data_holders[requested_data]:
        data_holders[requested_data] = set()
        message = "0" + requested_data # prepend 0 so the peer knows it received the data
        peer_conn.send(message.encode('utf-8'))

        # wait for confirmation from peer that it sucessfuly recieved the data
        success = peer_conn.recv(1024).decode('utf-8')
        if success == "1":
            data_holders[requested_data].add(peer_addr)
        else:
            Exception(f'server.py: send_chunk failed\n           peer_addr: {peer_addr}\n           message: {message}')

    else:
        # loop through the peers who have the desired data until one successfuly sends the data to the peer_addr
        for peer in data_holders[requested_data]:
            message = "1" + peer_addr # prepend 1 so the peer knows it received the address of a peer with the data
            peer_conn.send(message.encode('utf-8'))
            success = peer_conn.recv(1024).decode('utf-8')
            if success == '1':
                break

# Function to handle communication with a single client
def handle_client(conn, addr, client_id):
    print(f"server.py: New connection from {addr}")
    if addr not in clients_dict:
        clients_dict[addr] = client_id
        print(f'server.py: start hand_client, Clients_Dic: {clients_dict}')

    while True:
        message = conn.recv(1024).decode('utf-8')

        # Close the server if the message is NULL (empty)
        if not message:
            print(f"server.py: Client{addr} disconnected.")
            del clients_dict[addr]
            break
    
        operation = message[0]
        # Send data to the peer
        if operation == '0':
            print(f'server.py: Data request received from Client{clients_dict[addr]}\n           Client addr: {addr}')
            send_chunk(conn, addr, message)

        elif operation == '1':
            print(f'server.py: Message received from Client{clients_dict[addr]}\n           Client addr: {addr}\n           Message: {message[1:]}\n')
    print(f'server.py: end of handle_client, Clients_Dic: {clients_dict}')


    # Close the client connection
def close_server(conn):
    conn.close()

# Server setup to handle multiple clients
def start_server():
    host = '127.0.0.1'  # Localhost
    port = 12345        # Non-privileged port
    client_id = 1

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to address and port
    server_socket.bind((host, port))

    # Listen for incoming connections
    server_socket.listen()
    print(f"server.py: Server listening on {host}:{port}")

    while True:
        # Accept a new connection from a client
        conn, addr = server_socket.accept()

        # Start a new thread to handle the client
        client_thread = threading.Thread(target=handle_client, args=(conn, addr, client_id))
        client_id += 1
        client_thread.start()

if __name__ == '__main__':
    start_server()

