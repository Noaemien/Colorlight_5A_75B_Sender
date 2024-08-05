import socket
import numpy as np
import cv2, base64
import time

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
        #self.s.setsockopt(socket.SOL_SOCKET, 25, str("enp0s20f0u4" + '\0').encode('utf-8'))
        for i in range(100):
            try:
                
                pass
            except:
                continue
            #print("Worked with", i, flush=True)
    
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
        #print("Display Frame Data: ", bytearray(data))
        self.__send(frame_type, bytearray(payload))  

    #TODO make modular: this works only for set dimentions
    def send_row(self, row, row_number: int):
        #t1 = time.time()
        frame_type = b'\x55'
        horizontal_offset = 0
        pixel_count = 256
        pixel_data = [bytes([pixel[0]]) + bytes([pixel[1]]) + bytes([pixel[2]]) for pixel in row] #[b'\x00\x00\xFF' for pixel in row]
        data = (row_number).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
            2, 'big') + b'\x08\x88'
        data += b''.join(pixel_data[:256])
        self.__send(frame_type, data)
        #t2 = time.time()
        #print("p1:", t2-t1)

        #t1 = time.time()
        horizontal_offset = 256
        pixel_count = 128
        data = (row_number).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
            2, 'big') + b'\x08\x88'
        data += b''.join(pixel_data[256:384])
        self.__send(frame_type, data) 
        #t2 = time.time()
        #print("p2:", t2 - t1)


        # horizontal_offset = 512
        # data = (row_number).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
        #     2, 'big') + b'\x08\x88'
        # data += b''.join(pixel_data[512:768])
        # self.__send(frame_type, data) 

    def send_frame(self, frame):
        t1 = time.time()
        for i, row in enumerate(frame):
            self.send_row(row, i)
        self.display(255)
        t2 = time.time()
        #print("image:", t2-t1)
        #time.sleep(0.01)
  

# #Detect Colorlight 5A-75B
# #Code inspired by https://github.com/haraldkubota/colorlight/blob/main/py/detect.py
# ETH_P_ALL = 3
# ETH_FRAME_LEN = 1540
# interface = 'eth0'
# dst = b'\x11\x22\x33\x44\x55\x66'  # destination MAC address
# src = b'\x22\x22\x33\x44\x55\x66'  # source MAC address
# proto = b'\x07\x00'                # ethernet frame type
# payload = b'\x00' * 270            # payload
# payload2 = b'\0x00\0x00\0x01' + b'\x00' * 267

# colorlight_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
# colorlight_socket.bind((interface, 0))
# colorlight_socket.sendall(dst + src + proto + payload)

# data = colorlight_socket.recv(ETH_FRAME_LEN)

# if data[12]==8 and data[13]==5:
#     print("Detected a Colorlight card...")
#     if data[14]==4:
#         print("Colorlight 5A "+str(data[15])+"."+str(data[16])+" on "+interface)
#         print("Resolution X:"+str(data[34]*256+data[35])+" Y:"+str(data[36]*256+data[37]))

# colorlight_socket.sendall(dst + src + proto + payload2)

# def display():
#     # Send display Frame
#     DISPLAY_FRAME_DATA_LEN = 98

#     proto = b'\x01\x07'
#     data = [0] * DISPLAY_FRAME_DATA_LEN
#     data[21] = 0xFF #Brightness
#     data[22] = 0x05 #Nothing specific but necessary
#     data[24] = 0xFF #Red brightness
#     data[25] = 0xFF #Green brightness
#     data[26] = 0xFF #Blue brightness
#     #print("Display Frame Data: ", bytearray(data))
#     colorlight_socket.sendall(dst + src + proto + bytearray(data))

# # Send Brightness Frame (Not necessarily required)
# BRIGHTNESS_FRAME_DATA_LEN = 64

# proto = b'\x0A'
# data = [0] * BRIGHTNESS_FRAME_DATA_LEN
# data[0] = 0xFF #Red brightness
# data[1] = 0xFF #Green brightness
# data[2] = 0xFF #Blue brightness
# data[0] = 0xFF #Alwayse 0xFF
# print("Brightness Frame Data: ", bytearray(data))
# colorlight_socket.sendall(dst + src + proto + bytearray(data))


# def send_frame(frame):
#     proto = b'\x55'
    
    
#     for i, row in enumerate(frame):
#         horizontal_offset = 0
#         pixel_count = 128
#         pixel_data = [bytes([pixel[0]]) + bytes([pixel[1]]) + bytes([pixel[2]]) for pixel in row] #[b'\x00\x00\xFF' for pixel in row]
#         data = (127-i).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
#             2, 'big') + b'\x08\x88'
#         data += b''.join(pixel_data)
#         colorlight_socket.send(dst + src + proto + data)
        
if __name__ == "__main__":
    colorlight = Colorlight(interface='enp0s20f0u4', verbose=True)

    UDP_IP = "192.168.0.26" #rpi ip
    UDP_PORT = 5005

    udp_sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
    udp_sock.bind((UDP_IP, UDP_PORT))
    #udp_sock.setblocking(0)
    i = 0
    while True:
        #TODO Latency upgrade
        data, addr = udp_sock.recvfrom(65536) # buffer size is 1024 bytes
        data = base64.b64decode(data,' /')
        npdata = np.frombuffer(data,dtype=np.uint8)
        frame = cv2.imdecode(npdata,1)
        #cv2.imshow("RECEIVING VIDEO",frame)
        #print(frame.shape)
        colorlight.send_frame(frame)
        #print("frame sent")
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            udp_sock.close()
            break


    colorlight.s.close()