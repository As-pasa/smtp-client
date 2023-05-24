import json
import socket
import base64
import ssl
import pathlib
import mimetypes

HOST_ADDRESS = "smtp.yandex.ru"
PORT = 465


def request(socket, request):
    socket.send((request + '\n').encode())
    recv_data = socket.recv(1024).decode()
    return recv_data


with open("acc_config.json", 'r') as file:
    cont = json.load(file)
    USER_NAME = cont["login"]
    PASSWORD = cont["password"]

with open("envelope_config.json", 'r') as file:
    cont = json.load(file)
    RECEIVERS = cont["receivers"]
    SUBJECT = cont['subject']
    FROM = cont['from']

ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_contex.check_hostname = False
ssl_contex.verify_mode = ssl.CERT_NONE


def wrap_attachment(boundary: str) -> str:
    p = pathlib.Path("MailComponents")
    body = ""
    body += f"--{boundary}\n"
    body += 'Content-Type: text/plain; charset=utf-8\n\n'
    with open("MailText", 'r') as ff:
        body += ff.read() + "\n"
    for i in p.iterdir():
        mime = mimetypes.guess_type(i.absolute().as_posix())[0]
        if mime is None:
            mime = "application/octet-stream"
        with open(i, 'rb') as ff:
            content = base64.b64encode(ff.read()).decode("UTF-8")
        body += f"--{boundary}\n"
        body += "Content-Disposition: attachment;\n" \
                f"   filename={i.name}\n"
        body += 'Content-Transfer-Encoding: base64\n'
        body += f"Content-Type: {mime}\n\n"
        body += content + "\n"

    return body + f"--{boundary}--"


def construct_headers(boundary: str):
    ans = ""
    ans += f"from: {FROM}\n"
    res = RECEIVERS[0]
    for i in RECEIVERS[1:]:
        res += f", {i}"
    ans += f"to: {res}\n"
    subj = [SUBJECT[i:i + 80] for i in range(0, len(SUBJECT), 80)]
    s = subj[0]
    for i in subj[1:]:
        s += "\n   " + i
    ans += f"subject: {s}\n"
    ans += 'MIME-Version: 1.0\n'
    ans += f"Content-Type: multipart/mixed;\n" \
           f"    boundary={boundary}\n"
    return ans + "\n"


def construct_message() -> str:
    boundary = "----==--bound.21355.qvxj4z7i6zm4ub2j"
    headers = construct_headers(boundary)

    attachments = wrap_attachment(boundary)

    return headers + attachments + "\n.\n"


if __name__ == "__main__":

    with socket.create_connection((HOST_ADDRESS, PORT)) as sock:
        with ssl_contex.wrap_socket(sock, server_hostname=HOST_ADDRESS) as client:
            print(client.recv(1024))
            print(request(client, f"ehlo {USER_NAME}"))
            print(request(client, f"AUTH LOGIN"))
            print(request(client, base64.b64encode(USER_NAME.encode()).decode()))
            print(request(client, base64.b64encode(PASSWORD.encode()).decode()))
            print("from status:", request(client, f"mail from: {USER_NAME}@yandex.ru"))
            for i in RECEIVERS:
                print("to status: ", request(client, f"RCPT TO: {i}"))
            print("data status: ", request(client, "DATA"))
            print("data transfer status: ", request(client, construct_message()))
            print("closure status: ", request(client, "quit"))
