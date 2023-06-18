import socket
import threading
from robot import *

SERVER_ADDRESS = "192.168.31.171"
PORT_NUMBER = 9998


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_ADDRESS, PORT_NUMBER))
    server_socket.listen(5)

    while True:

        client_socket, client_address = server_socket.accept()

        try:
            # Create a new thread to handle the client connection
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()

        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
            client_socket.close()


if __name__ == "__main__":
    main()
