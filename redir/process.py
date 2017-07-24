#!/usr/bin/python3
# coding: utf-8


PROCESS = '''
           send              EPOLLIN
 client ----------> local -------------> local_sock.recv() ------> build & save
                                                                   remote socket
                                                                             |
                                                                             |
                                                              send to server |
                                                                             |
                                                                             |
                                                              EPOLLIN        V
   build & save  <------------------ server_socket.recv() <-------------- server
   remote socket
         |
         | send to dest server
         |
         V
  ---------------
  |             |
  | dest server |
  |             |
  ---------------
         |
         | dest server return
         |
         V
      server
         |
         |    EPOLLIN                              return to local
         ----------------> server_socket.recv() --------------------> local-----
            find socket                                                        |
                                                                               |
                                                                     EPOLLIN   |
                                                                   find socket |
                                                                               |
                         return to client                                      |
               client <-------------------- local_sock.recv() <-----------------
'''


def show_process():
    print(PROCESS)


if __name__ == '__main__':
    show_process()
