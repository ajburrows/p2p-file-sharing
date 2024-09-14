import socket
import threading

response = 'server_data'
data = set()
# Function to handle communication with a single client
def handle_client(conn, addr):
    print(f"server.py: New connection from {addr}")

    while True:
        message = conn.recv(1024).decode('utf-8')

        # Close the server if the message is NULL (empty)
        if not message:
            print(f"server.py: Client {addr} disconnected.")
            break
    
        operation = message[0]
        if operation == '0':
            print(f'server.py: recv_message call from {addr}')
            conn.send(response.encode('utf-8'))
            data.add(conn)
        if operation == '1':
            print(f'server.py: Message received\nClient address: {addr}\nMessage: {message[1:]}\n')


    # Close the client connection
def close_server(conn):
    conn.close()

# Server setup to handle multiple clients
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
        # Accept a new connection from a client
        conn, addr = server_socket.accept()

        # Start a new thread to handle the client
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

if __name__ == '__main__':
    start_server()

