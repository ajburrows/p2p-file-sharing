import threading
import time
from peer import Peer, peer_thread_function
from demo_peer import DemoPeer, demo_peer_thread_function
import subprocess

HOST = '127.0.0.1'
PORT = 12345

def start_server():
    """
        Description - run the server as a subprocess.
    """
    server_process = subprocess.Popen(['python3', 'server.py'])
    return server_process

def stop_server(server_process):
    """
        Description - gracefully terminate the server instance that is passed in. Forcefully kill the server if it does not terminate
                      within 5 seconds.
    """

    print("  demo.py: Stopping server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5) 
        print("  demo.py: Server terminated gracefully.")

    # Forcefully kill the server if it does not terminate
    except subprocess.TimeoutExpired:
        print("  demo.py: Server did not stop, killing it forcefully.")
        server_process.kill()  
        print("  demo.py: Server killed.")
    

def create_new_peer(peer_id, host, port, files_dir, malicious = False):
    """
        Description - create a new Peer instance and run it as a daemon thread. Then create the peer's server socket and connect
                      to the server.
    """

    new_peer = Peer(peer_id=peer_id, host=host, port=port, files_dir=files_dir, malicious=malicious)
    new_peer.create_server_socket()
    new_peer.connect_to_server()
    time.sleep(1)
    new_peer_thread = threading.Thread(target=peer_thread_function, args=(new_peer,))
    new_peer_thread.daemon = True
    new_peer_thread.start()
    time.sleep(2)
    return new_peer, new_peer_thread 


def start_demo():
    peer1_files_dir = '/home/ajburrows/projects/p2p-file-sharing-lab1/files1'
    peer2_files_dir = '/home/ajburrows/projects/p2p-file-sharing-lab1/files2'
    peer3_files_dir = '/home/ajburrows/projects/p2p-file-sharing-lab1/files3'
    peer4_files_dir = '/home/ajburrows/projects/p2p-file-sharing-lab1/files4'
    

    server_process = start_server()
    time.sleep(3)

    print('  demo.py: creating peers')
    peer1, peer1_thread = create_new_peer(1, HOST, PORT, peer1_files_dir)
    peer2, peer2_thread = create_new_peer(2, HOST, PORT, peer2_files_dir, True)
    peer3, peer3_thread = create_new_peer(3, HOST, PORT, peer3_files_dir)
    peer4, peer4_thread = create_new_peer(4, HOST, PORT, peer4_files_dir)
    print('  demo.py: created peers')

    peer1.initialize_files()
    peer1.upload_file_data()
    peer1.upload_chunk_hashes()

    peer2.initialize_files()
    peer2.upload_file_data()
    peer2.upload_chunk_hashes()
    print('  demo.py: data uploaded')
    time.sleep(2)

    print('  demo.py: peers will download in 5 seconds\n')
    time.sleep(8)
    print('  demo.py: Peer3 attempting to download f1_dir1.txt')
    peer3.download_file_thread('f1_dir1.txt')
    print('  demo.py: Peer4 attemping to download f1_dir1.txt')
    peer4.download_file_thread('f1_dir1.txt')


    time.sleep(10)
    print()
    print('  demo.py: Peers closing')
    peer1.close_peer()
    peer2.close_peer()
    peer3.close_peer()
    peer4.close_peer()
    time.sleep(1)
    print("  demo.py: peers have closed.")
    stop_server(server_process)
    peer1_thread.join()
    peer2_thread.join()
    peer3_thread.join()
    peer4_thread.join()
    print("  demo.py: All peer threads have terminated.")


if __name__ == '__main__':
    start_demo()


