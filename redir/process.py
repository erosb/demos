#!/usr/bin/python3
# coding: utf-8


PROCESS = '''             local socket
           send              EPOLLIN
 client ----------> local -------------> local_sock.recv() ------> build & save
                                                                   remote socket
                                                                             |
                                                                             |
                                                     remote socket EPOLLOUT  |
                                                       & send to server      |
                                                                             |
                     unpack data                                             V
   build & save  <------------------ local_sock.recv() <----------------- server
   remote socket                                            local socket
         |                                                    EPOLLIN
         |   remote socket EPOLLOUT
         |   & send to dest server
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
         | remote socket
         |    EPOLLIN                             return to local
         ----------------> remote_sock.recv() ----------------------> local ----
            find socket                                                        |
                                                                               |
                                                        remote socket EPOLLIN  |
                                                             find socket       |
                         return data to                                        |
                         client's socket                                       |
               client <-------------------- remote_sock.recv() <----------------
'''


def show_process():
    print(PROCESS)


if __name__ == '__main__':
    show_process()
