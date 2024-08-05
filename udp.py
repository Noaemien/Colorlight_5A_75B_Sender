import socket
import numpy as np
import cv2, base64

#Detect Colorlight 5A-75B
#Code from https://github.com/haraldkubota/colorlight/blob/main/py/detect.py
ETH_P_ALL = 3
ETH_FRAME_LEN = 1540
interface = 'eth0'
dst = b'\x11\x22\x33\x44\x55\x66'  # destination MAC address
src = b'\x22\x22\x33\x44\x55\x66'  # source MAC address
proto = b'\x07\x00'                # ethernet frame type
payload = b'\x00' * 270            # payload
payload2 = b'\0x00\0x00\0x01' + b'\x00' * 267

colorlight_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
colorlight_socket.bind((interface, 0))
colorlight_socket.sendall(dst + src + proto + payload)

data = colorlight_socket.recv(ETH_FRAME_LEN)

if data[12]==8 and data[13]==5:
    print("Detected a Colorlight card...")
    if data[14]==4:
        print("Colorlight 5A "+str(data[15])+"."+str(data[16])+" on "+interface)
        print("Resolution X:"+str(data[34]*256+data[35])+" Y:"+str(data[36]*256+data[37]))

colorlight_socket.sendall(dst + src + proto + payload2)

def display():
    # Send display Frame
    DISPLAY_FRAME_DATA_LEN = 98

    proto = b'\x01\x07'
    data = [0] * DISPLAY_FRAME_DATA_LEN
    data[21] = 0xFF #Brightness
    data[22] = 0x05 #Nothing specific but necessary
    data[24] = 0xFF #Red brightness
    data[25] = 0xFF #Green brightness
    data[26] = 0xFF #Blue brightness
    #print("Display Frame Data: ", bytearray(data))
    colorlight_socket.sendall(dst + src + proto + bytearray(data))

# Send Brightness Frame (Not necessarily required)
BRIGHTNESS_FRAME_DATA_LEN = 64

proto = b'\x0A'
data = [0] * BRIGHTNESS_FRAME_DATA_LEN
data[0] = 0xFF #Red brightness
data[1] = 0xFF #Green brightness
data[2] = 0xFF #Blue brightness
data[0] = 0xFF #Alwayse 0xFF
print("Brightness Frame Data: ", bytearray(data))
colorlight_socket.sendall(dst + src + proto + bytearray(data))


def send_frame(frame):
    proto = b'\x55'
    
    
    for i, row in enumerate(frame):
        horizontal_offset = 0
        pixel_count = 128
        pixel_data = [bytes([pixel[0]]) + bytes([pixel[1]]) + bytes([pixel[2]]) for pixel in row] #[b'\x00\x00\xFF' for pixel in row]
        data = (127-i).to_bytes(2, 'big') + horizontal_offset.to_bytes(2, 'big') + pixel_count.to_bytes(
            2, 'big') + b'\x08\x88'
        data += b''.join(pixel_data)
        colorlight_socket.send(dst + src + proto + data)
        



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
    send_frame(frame)
    display()
    #print("frame sent")
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        udp_sock.close()
        break


colorlight_socket.close()