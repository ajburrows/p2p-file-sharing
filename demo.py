import threading
import time
from client import Client, client_thread_function  # Assuming the Client class is in client.py
import subprocess

HOST = '127.0.0.1'
PORT = 12345

def start_server():
    server_process = subprocess.Popen(['python3', 'server.py'])
    return server_process

def stop_server(server_process):
    print("  demo.py: Stopping server...")
    server_process.terminate()  # Gracefully terminate the server
    try:
        server_process.wait(timeout=5)  # Wait for up to 5 seconds for the server to stop
        print("  demo.py: Server terminated gracefully.")
    except subprocess.TimeoutExpired:
        print("  demo.py: Server did not stop, killing it forcefully.")
        server_process.kill()  # Forcefully kill the server if it does not terminate
        print("  demo.py: Server killed.")
    
def create_new_client(client_id, host, port):
    new_client = Client(client_id=client_id, host=host, port=port)
    new_client.create_client_socket()
    new_client.connect()
    time.sleep(1)
    new_client_thread = threading.Thread(target=client_thread_function, args=(new_client,))
    new_client_thread.daemon = True
    new_client_thread.start()
    time.sleep(2)
    return new_client, new_client_thread 



def start_demo():
    server_process = start_server()
    time.sleep(2)
    print()

    client1, client1_thread = create_new_client(1, HOST, PORT)
    print()

    # Interact with the client from outside the thread (in demo.py)
    client1.send_message("Hello, server!")
    time.sleep(2)

    client1.send_message("Another message from the main thread.")
    time.sleep(2)

    client1.req_data()
    time.sleep(2)
    print()
    
    client2, client2_thread = create_new_client(2, HOST, PORT)
    print()
    # Close the client from the main thread
    client1.close()
    client2.close()

    # Wait for the thread to finish
    client1_thread.join()
    client2_thread.join()

    print("  demo.py: Client threads have finished.")
    print()

    stop_server(server_process)

if __name__ == '__main__':
    start_demo()

