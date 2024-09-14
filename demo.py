import threading
import time
from client import Client, client_thread_function  # Assuming the Client class is in client.py
import subprocess

def start_server():
    server_process = subprocess.Popen(['python3', 'server.py'])
    print("Server started.")
    return server_process

def stop_server(server_process):
    print("Stopping server...")
    server_process.terminate()  # Gracefully terminate the server
    try:
        server_process.wait(timeout=5)  # Wait for up to 5 seconds for the server to stop
        print("Server terminated gracefully.")
    except subprocess.TimeoutExpired:
        print("Server did not stop, killing it forcefully.")
        server_process.kill()  # Forcefully kill the server if it does not terminate
        print("Server killed.")


def start_demo():
    print("Starting server...")
    print("############################")
    server_process = start_server()
    time.sleep(2)
    print()

    # Create a client object
    print("Creating client\n###########################")
    client = Client(client_id=1, host='127.0.0.1', port=12345)
    client.create_client_socket()
    print()

    # Connect the client
    print("Connecting client\n#########################")
    client.connect()
    time.sleep(2)
    print()

    print("Creating client thread...\n##########################")
    # Create a thread to run the client in the background
    client_thread = threading.Thread(target=client_thread_function, args=(client,))
    client_thread.daemon = True  # Run the thread as a daemon
    client_thread.start()
    print()

    # Interact with the client from outside the thread (in demo.py)
    time.sleep(2)
    print("sending messages...\n#############################")
    client.send_message("Hello, server!")

    time.sleep(2)
    client.send_message("Another message from the main thread.")

    time.sleep(2)
    print()

    # Close the client from the main thread
    print("Closing client...\n###############################")
    client.close()

    # Wait for the thread to finish
    client_thread.join()

    print("Client thread has finished.")
    print()

    print("Stopping server...")
    stop_server(server_process)

if __name__ == '__main__':
    start_demo()

