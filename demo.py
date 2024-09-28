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
    
def create_new_peer(peer_id, host, port, files_dir):
    new_peer = Peer(peer_id=peer_id, host=host, port=port, files_dir=files_dir)
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

    server_process = start_server()
    time.sleep(3)
    print()

    peer1, peer1_thread = create_new_peer(1, HOST, PORT, peer1_files_dir)
    print()
    peer2, peer2_thread = create_new_peer(2, HOST, PORT, peer2_files_dir)
    print()
    peer3, peer3_thread = create_new_peer(3, HOST, PORT, peer3_files_dir)
    print()


    peer1.req_chunk()
    time.sleep(4)
    print()

    peer2.req_chunk()
    time.sleep(2)
    print()

    peer1.close_peer()
    time.sleep(2)
    print()

    peer3.req_chunk()
    time.sleep(2)
    print()

    peer2.close_peer()
    peer3.close_peer()
    print("  demo.py: All peers have closed.")
    stop_server(server_process)
    peer1_thread.join()
    peer2_thread.join()
    peer3_thread.join()
    print("  demo.py: All peer threads have terminated.")

def test_upload_file_data():
    peer1_files_dir = '/home/ajburrows/projects/p2p-file-sharing-lab1/files1'

    server_process = start_server()
    time.sleep(3)
    print()

    peer1, peer1_thread = create_new_peer(1, HOST, PORT, peer1_files_dir)
    print()
    peer2, peer2_thread = create_new_peer(2, HOST, PORT, peer1_files_dir)
    print()
    peer3, peer3_thread = create_new_peer(3, HOST, PORT, '')
    print()
    #peer4, peer4_thread = create_new_peer(4, HOST, PORT, '')
    print('\n  demo.py: created peers')

    peer1.initialize_files()
    time.sleep(0.5)
    #print()
    peer1.upload_file_data()
    time.sleep(0.5)
    peer1.upload_chunk_hashes()
    time.sleep(0.5)

    peer2.initialize_files()
    time.sleep(0.5)
    print()
    peer2.upload_file_data()
    time.sleep(0.5)
    print('\n  demo.py: data uploaded')

    print('\n  demo.py: PEER3 ATTEMPTING DOWNLOAD')
    peer3.download_file('f1_dir1.txt')
    #peer4.download_file('f1_dir1.txt')
    print()

    peer1.close_peer()
    peer2.close_peer()
    peer3.close_peer()
    #peer4.close_peer()
    time.sleep(2)
    print()
    print("  demo.py: peers have closed.")
    stop_server(server_process)
    peer1_thread.join()
    peer2_thread.join()
    peer3_thread.join()
    #peer4_thread.join()
    print("  demo.py: All peer threads have terminated.")


if __name__ == '__main__':
    #start_demo()
    test_upload_file_data()


