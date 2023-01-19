"""Zebra printing module"""
import socket
import os

print(f"Importing {os.path.basename(__file__)}...")


def print_text(text: str):
    """Open socket to printer and send text"""
    mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = "192.168.1.240"
    port = 9100
    if socket.gethostname().lower() != "chris-mbp":
        mysocket.connect((host, port))  # connecting to host
        mysocket.send(b"^XA^A0N,50,50^FO0,50^FB450,4,,C,^FD" + bytes(text, "utf-8") + b"^FS^XZ")  # using bytes
        mysocket.close()  # closing connection
