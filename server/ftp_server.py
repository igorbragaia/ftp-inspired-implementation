from ftp import FTP, Message, decode_message, encode_message
import socket
import os
import re
import sys
import json
import shutil


pathRegex = "([a-zA-Z0-9/.])*"


class FTPServer(FTP):
    def __init__(self):
        super().__init__()
        self.status = None
        self.tcp = None

    @staticmethod
    def make_message(path: str, base_path: str, auth: str, text: str):
        return Message('response', {
            'path': '~/{0}'.format(os.path.relpath(path, base_path)) if auth == 'AUTHENTICATED' else '',
            'text': text
        })

    def connect(self, address='127.0.0.1:5000'):
        try:
            host = address.split(':')[0]
            port = int(address.split(':')[1])
            self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp.bind((host, port))
            self.tcp.listen(1)
            self.status = 'NOT AUTHENTICATED'
            return [True, None]
        except Exception as e:
            print(e)
            return [False, e]

    def close(self):
        if self.tcp is not None:
            self.tcp.close()
            self.tcp = None
            self.status = None
            print("server conn closed")

    def run(self):
        self.connect()
        while True:
            con, cliente = self.tcp.accept()
            base_path = os.path.join(os.getcwd(), "files")
            path = os.path.join(os.getcwd(), "files")
            print('Conectado por', cliente)
            self.status = 'NOT AUTHENTICATED'

            message = self.make_message(path, base_path, self.status, 'ENTER YOUR AUTH CODE')
            con.send(encode_message(message))
            while True:
                msg = con.recv(1024)
                if not msg:
                    break

                request = decode_message(msg)

                print(cliente, msg)
                message = self.make_message(path, base_path, self.status, '')
                if self.status == 'NOT AUTHENTICATED':
                    if request.data == {'username': 'igor', 'password': 'bragaia'}:
                        self.status = 'AUTHENTICATED'
                        message = self.make_message(path, base_path, self.status,
                                                    'LOGGED IN')
                    else:
                        message = self.make_message(path, base_path, self.status,
                                                    'PERMISSION DENIED\nENTER YOUR AUTH CODE')
                elif self.status == 'AUTHENTICATED':
                    # **********************************
                    # NAVEGACAO E LISTAGEM DE DIRETORIOS
                    # **********************************
                    # $ cd <dirname>
                    if request.method == 'cd':
                        dirname = request.data['dirname']
                        new_path = os.path.realpath(os.path.join(path, dirname))
                        if os.path.exists(new_path) and os.path.isdir(new_path) \
                                and not str.endswith(os.path.relpath(new_path, base_path), '..'):
                            path = new_path
                            message = self.make_message(path, base_path, self.status, '')
                        else:
                            message = self.make_message(path, base_path, self.status, 'No such file or directory')
                    # $ ls <dirname>
                    elif request.method == 'ls':
                        dirname = request.data['dirname']
                        new_path = os.path.realpath(os.path.join(path, dirname))
                        if os.path.exists(new_path) and os.path.isdir(new_path) \
                                and not str.endswith(os.path.relpath(new_path, base_path), '..'):
                            content = os.listdir(new_path)
                            content_str = '\t'.join(content)
                            message = self.make_message(path, base_path, self.status,
                                                        content_str)
                        else:
                            message = self.make_message(path, base_path, self.status,
                                                        'No such file or directory')
                    # $ pwd
                    elif request.method == 'pwd':
                        message = self.make_message(path, base_path, self.status,
                                                    os.path.relpath(path, base_path))
                    # *************************
                    # MANIPULACAO DE DIRETORIOS
                    # *************************
                    # $ mkdir <dirname>
                    elif request.method == 'mkdir':
                        dirname = request.data['dirname']
                        dirname = os.path.realpath(os.path.join(base_path, dirname))
                        previous_dir = os.path.realpath(os.path.join(dirname, '..'))
                        if not os.path.exists(dirname) and os.path.isdir(previous_dir) \
                            and not str.endswith(os.path.relpath(previous_dir, base_path), '..'):
                            os.mkdir(dirname)
                            message = self.make_message(path, base_path, self.status, '')
                        else:
                            message = self.make_message(path, base_path, self.status,
                                                        'cannot create directory: no such file or directory')
                    # rmdir <dirname>
                    elif request.method == 'rmdir':
                        dirname = request.data['dirname']
                        dirname = os.path.realpath(os.path.join(base_path, dirname))
                        if str.endswith(os.path.relpath(path, dirname), '..') and os.path.isdir(dirname):
                            shutil.rmtree(dirname)
                            message = self.make_message(path, base_path, self.status, '')
                        else:
                            message = self.make_message(path, base_path, self.status,
                                                        'cannot remove directory: no such file or directory')
                    # ***********************
                    # MANIPULACAO DE ARQUIVOS
                    # ***********************
                    # get <dirname>
                    elif request.method == 'get':
                        dirname = request.data['dirname']
                    # put <dirname>
                    elif request.method == 'put':
                        dirname = request.data['dirname']
                    # delete <dirname>
                    elif request.method == 'delete':
                        dirname = request.data['dirname']

                con.send(encode_message(message))

            print('Finalizando conexao do cliente', cliente)
            con.close()

    def __del__(self):
        self.close()


if __name__ == '__main__':
    server = FTPServer()
    server.run()