import threading
import time
from peer import Peer, peer_thread_function
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
    
def create_new_peer(peer_id, host, port):
    new_peer = Peer(peer_id=peer_id, host=host, port=port)
    new_peer.create_server_socket()
    new_peer.connect()
    time.sleep(1)
    new_peer_thread = threading.Thread(target=peer_thread_function, args=(new_peer,))
    new_peer_thread.daemon = True
    new_peer_thread.start()
    time.sleep(2)
    return new_peer, new_peer_thread 



def start_demo():
    server_process = start_server()
    time.sleep(3)
    print()

    peer1, peer1_thread = create_new_peer(1, HOST, PORT)
    print()

    # Interact with the peer from outside the thread (in demo.py)
    peer1.send_message("Hello, server!")
    time.sleep(2)

    peer1.send_message("Another message from the main thread.")
    time.sleep(2)

    peer1.req_chunk()
    time.sleep(2)
    print()
    
    peer2, peer2_thread = create_new_peer(2, HOST, PORT)
    print()
    peer2.req_chunk()
    # Close the peer from the main thread
    peer1.close()
    peer2.close()

    # Wait for the thread to finish
    peer1_thread.join()
    peer2_thread.join()

    print("  demo.py: peer threads have finished.")
    print()

    stop_server(server_process)

if __name__ == '__main__':
    start_demo()

