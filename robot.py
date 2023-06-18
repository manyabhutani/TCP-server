from Constants import *
import select

message_buffer = ""


class Robot:
    def __init__(self, client_socket):
        # Current Coordinates
        self.x = None
        self.y = None

        # Current Direction
        self.direction = UP

        # Socket Connections
        self.client_socket = client_socket

    def send(self, message):
        send_message(self.client_socket, message)

    def receive(self):
        return receive_message(self.client_socket)

    def move(self):
        x1, y1 = self.x, self.y
        self.send(SERVER_MOVE)
        self.x, self.y = extract_coordinates(self.receive())
        self.direction = self.determine_direction(x1, y1)
        print(f"Direction: {self.direction}")

        if self.x == 0 and self.y == 0:
            self.pick_up()

    def determine_direction(self, x1, y1):
        dx, dy = self.x - x1, self.y - y1
        if dx > 0:
            return RIGHT
        elif dx < 0:
            return LEFT
        elif dy > 0:
            return UP
        elif dy < 0:
            return DOWN
        else:
            print("Error: Encounterd obstacle")
            self.go_around_obstacle()

        print(f"Direction: {self.direction}")

    def go_around_obstacle(self):
        self.turn_right()
        prev_x, prev_y = self.x, self.y
        self.move()
        if not self.has_moved(prev_x, prev_y):
            self.turn_left()
            self.turn_left()
            self.move()
            if not self.has_moved(prev_x, prev_y):
                self.turn_left()
                self.move()
                if not self.has_moved(prev_x, prev_y):
                    print("Error: Unable to bypass obstacle")
                    return
                else:
                    self.turn_right()
            else:
                self.turn_right()
        else:
            self.turn_left()

    def turn_left(self):
        self.send(SERVER_TURN_LEFT)
        self.x, self.y = extract_coordinates(self.receive())

        if self.direction is not None:
            self.direction = (self.direction - 1) % 4

    def turn_right(self):
        self.send(SERVER_TURN_RIGHT)
        self.x, self.y = extract_coordinates(self.receive())

        if self.direction is not None:
            self.direction = (self.direction + 1) % 4

    def initial_move(self):

        self.direction = 0
        self.send(SERVER_MOVE)
        x1, y1 = extract_coordinates(self.receive())

        if self.x == 0 and self.y == 0:
            self.pick_up()

        self.send(SERVER_MOVE)
        self.x, self.y = extract_coordinates(self.receive())
        self.direction = self.determine_direction(x1, y1)

        if self.direction is None:
            self.turn_left()
            self.initial_move()

        if self.x == 0 and self.y == 0:
            self.pick_up()

    def move_to_origin(self):
        self.initial_move()
        print(f"Initial Direction: {self.direction}")

        while self.x != 0 or self.y != 0:
            target_direction = self.get_target_direction()

            print("Target Direction: ", target_direction)

            if self.direction is not None:
                # Align the robot's direction with the target direction
                while self.direction != target_direction:
                    print("Turning to Target Direction")
                    self.turn_right()

            prev_x, prev_y = self.x, self.y
            self.move()

            # If the robot has not moved, it has encountered an obstacle
            if not self.has_moved(prev_x, prev_y):
                print("Encountered obstacle, trying to bypass")
                self.go_around_obstacle()

                # After going around the obstacle, realign with the target direction
                while self.direction != target_direction:
                    print("Turning to Target Direction")
                    self.turn_right()

        self.pick_up()

    def get_target_direction(self):
        if self.y > 0:
            return DOWN
        elif self.y < 0:
            return UP
        elif self.x > 0:
            return LEFT
        elif self.x < 0:
            return RIGHT
        else:
            print("Error: Cannot determine target direction")
            raise RuntimeError

    def pick_up(self):
        self.send(SERVER_PICK_UP)
        print(self.receive())
        self.logout()

    def logout(self):
        self.send(SERVER_LOGOUT)
        self.client_socket.close()

    def has_moved(self, previous_x, previous_y):
        return self.x != previous_x or self.y != previous_y


def calculate_hash(username):
    ascii_sum = sum(ord(c) for c in username)
    resulting_hash = (ascii_sum * 1000) % 65536
    return resulting_hash


def send_message(client_socket, message):
    print(f"Sending message: {message}")
    message_bytes = message.encode('utf-8')
    client_socket.sendall(message_bytes)


def receive_message(client_socket, buffer_size=1024, timeout=2):
    global message_buffer
    print(message_buffer)
    # Check if a complete message is already available in the buffer
    message_str = get_complete_message()
    if message_str is not None:
        return message_str

    while True:
        ready_to_read, _, _ = select.select([client_socket], [], [], timeout)

        # If there's no data to be read within the timeout, raise TimeoutError
        if not ready_to_read:
            client_socket.close()
            raise TimeoutError("Timeout reached while waiting for a message")

        message = client_socket.recv(buffer_size)
        message_buffer += message.decode('utf-8')

        message_str = get_complete_message()
        if message_str is not None:
            return message_str


def get_complete_message():
    global message_buffer

    if "\a\b" in message_buffer:
        split_buffer = message_buffer.split("\a\b", 1)
        message = split_buffer[0]
        message_buffer = split_buffer[1]

        print(f"Received message: {message}")
        return message
    else:
        return None


def extract_coordinates(s):
    s = s.rstrip('\a\b')

    parts = s.split()
    x = int(parts[1])
    y = int(parts[2])

    return x, y


def handle_client(client_socket, client_address):
    global message_buffer

    try:
        username = receive_message(client_socket)
        send_message(client_socket, SERVER_KEY_REQUEST)
        print(message_buffer)

        key_id_str = receive_message(client_socket)
        if not key_id_str:
            print("Error: Received empty message for key_id")
            return

        print(message_buffer)

        key_id = int(key_id_str)
        if key_id < 0 or key_id > 4:
            send_message(client_socket, SERVER_KEY_OUT_OF_RANGE_ERROR)
            return

        server_key = SERVER_KEYS[key_id]
        client_key = CLIENT_KEYS[key_id]

        username_hash = calculate_hash(username)
        server_confirm = (username_hash + server_key) % 65536
        send_message(client_socket, f"{server_confirm}\a\b")

        client_confirmation_str = receive_message(client_socket)
        if not client_confirmation_str:
            print("Error: Received empty message for client_confirmation")
            return

        client_confirmation = int(client_confirmation_str)
        expected_client_confirmation = (username_hash + client_key) % 65536

        if client_confirmation != expected_client_confirmation:
            send_message(client_socket, SERVER_LOGIN_FAILED)
            return

        send_message(client_socket, SERVER_OK)

        robot = Robot(client_socket)
        robot.move_to_origin()
        robot.pick_up()
        robot.logout()

    except TimeoutError as e:
        print(f"TimeoutError handling client {client_address}: {e}")
        message_buffer = ""
    except OSError as e:
        print(f"Error handling client {client_address}: {e}")
        message_buffer = ""
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
        print(robot.x, robot.y, robot.direction)
        message_buffer = ""
        send_message(client_socket, SERVER_LOGIC_ERROR)
    except BrokenPipeError as e:
        print(f"Error handling client {client_address}: {e}")
        message_buffer = ""
        
    finally:
        message_buffer = ""
        client_socket.close()
