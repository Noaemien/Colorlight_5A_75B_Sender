import socket
import numpy as np
import cv2
import base64

#Connect and send frames to Colorlight 5A-75B
class Colorlight:
    BRIGHTNESS_FRAME_DATA_LEN = 64
    DISPLAY_FRAME_DATA_LEN = 98
    SOURCE_MAC = b'\x22\x22\x33\x44\x55\x66'
    DESTINATION_MAC = b'\x11\x22\x33\x44\x55\x66'
    ETH_P_ALL = 3

    def __init__(self, interface: str, verbose: bool):
        self.interface = interface
        self.verbose = verbose
        print(interface, self.verbose)
        self.init_socket()
        if self.verbose:
            self.detect_colorlight_5A75B()
        
        self.set_brightness(10, 10, 10)


    def init_socket(self):
        if self.verbose:
            print("Binding to interface " + self.interface, flush=True)
        self.s =  socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(self.ETH_P_ALL))
        self.s.bind((self.interface, 0))
    
    def __send(self, frame_type: bytes, payload: bytes):
        self.s.sendall(self.DESTINATION_MAC + self.SOURCE_MAC + frame_type + payload)

    #Inspired by https://github.com/haraldkubota/colorlight/blob/main/py/detect.py
    def detect_colorlight_5A75B(self):
        #Establish three way handshake
        '''
        Detection frame structure:
            dst: 11:22:33:44:55:66
            src: 22:22:33:44:55:66
            frame_type: 0x0700
            data: 270 null bytes
        '''
        frame_type = b'\x07\x00'
        payload = b'\x00' * 270
        self.__send(frame_type, payload)

        #TODO: Complete documentation
        '''
        Response is expected to have following structure:
            dst: ff:ff:ff:ff:ff:ff (broadcast)
            src: 11:22:33:44:55:66
            frame_type: 0x0805
            Data length: 1056
            data[0]: Reciever card version
            data[62]: Controller number (0 or 1)
        '''
        response = self.s.recv(1540)
        #Verify correct frame type
        if response[12] == 0x8 and response[13] == 0x5:
            print("Colorlight card detected")
            x_res = response[34] * 256 + response[35]
            y_res = response[36] * 256 + response[37]
            print("Resolution: " + str(x_res) + " x " + str(y_res))
        else:
            #TODO: call error when no card detected
            print("No Colorlight detected")
        
        '''
        ACK has following structure:
            dst: 11:22:33:44:55:66
            src: 22:22:33:44:55:66
            frame_type: 0x0700
            Data length: 270 bytes
            data[2]: Controller number + 1 (1 or 2)

        '''
        payload = [0] * 270
        payload[2] = 1 #Controller number TODO add support for daisy chained controllers
        self.__send(frame_type, bytearray(payload))

    # Send Brightness Frame (Not necessarily required)
    def set_brightness(self, red_brightness: int = 255, green_brightness: int = 255, blue_brightness: int = 255):
        '''
        Brightness frame structure:
            frame_type: 0x0A
            Data length: 64 bytes
            data[0]: red brightness
            data[1]: green brightness
            data[2]: blue brightness
            data[3]: alwayse 0xFF
    
        '''
        
        frame_type = b'\x0A'
        payload = [0] * self.BRIGHTNESS_FRAME_DATA_LEN
        payload[0] = red_brightness
        payload[1] = green_brightness
        payload[2] = blue_brightness
        payload[3] = 0xFF
        if self.verbose:
            print("Brightness Frame Data: ", bytearray(payload))
        self.__send(frame_type, bytearray(payload))

    # Send display frame: used to refresh display
    def display(self, brightness: int = 128):
        '''
        Display frame structure:
            frame type: 0x0107
            data length: 98 bytes
            data[21]: brightness
            data[22]: alwayse 0x05
            data[24]: red brightness
            data[25]: green brightness
            data[26]: blue brightness
        '''
        frame_type = b'\x01\x07'
        payload = [0] * self.DISPLAY_FRAME_DATA_LEN
        payload[21] = brightness #Brightness
        payload[22] = 0x05 #Nothing specific but necessary
        payload[24] = 0xFF #Red brightness
        payload[25] = 0xFF #Green brightness
        payload[26] = 0xFF #Blue brightness
        self.__send(frame_type, bytearray(payload))  

    #TODO make modular: this works only for set dimentions
    def send_row(self, row, row_number: int):
        frame_type = b'\x55'
        horizontal_offset = 0
        pixel_count = 256
        pixel_data = [bytes([pixel[0]]) + bytes([pixel[1]]) + bytes([pixel[2]]) for pixel in row] 
        data = (row_number).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
            2, 'big') + b'\x08\x88'
        data += b''.join(pixel_data[:256])
        self.__send(frame_type, data)

        horizontal_offset = 256
        pixel_count = 128
        data = (row_number).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
            2, 'big') + b'\x08\x88'
        data += b''.join(pixel_data[256:384])
        self.__send(frame_type, data) 

    def send_frame(self, frame):
        for i, row in enumerate(frame):
            self.send_row(row, i)
        self.display(255)
  

        
if __name__ == "__main__":
    colorlight = Colorlight(interface='enp0s20f0u4', verbose=True)

    UDP_IP = "192.168.0.26" #rpi ip
    UDP_PORT = 5005

    udp_sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
    udp_sock.bind((UDP_IP, UDP_PORT))
    i = 0
    while True:
        data, addr = udp_sock.recvfrom(65536) # buffer size is 1024 bytes
        data = base64.b64decode(data,' /')
        npdata = np.frombuffer(data,dtype=np.uint8)
        frame = cv2.imdecode(npdata,1)
        #cv2.imshow("RECEIVING VIDEO",frame)
        colorlight.send_frame(frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            udp_sock.close()
            break

    colorlight.s.close()
