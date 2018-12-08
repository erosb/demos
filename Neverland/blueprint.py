#!/usr/bin/python3.6
#coding: utf-8


'''
Neverland 设计图初稿


Neverland 是一个类似区块链社区的 UDP 数据包转发集群，集群将来自应用程序的数据包通过最优路径转发到目标服务器。


社区节点类型：

    客户端节点：运行于客户机上的 Neverland 节点。社区的数据来源，将客户机上的所有数据转发入社区。
                将所有 TCP 流通过自有 TCP Over UDP 协议或第三方工具转换为 UDP 流。

    出口节点：数据包离开社区的节点，过滤重复的 UDP 包并将 TCP Over UDP 包还原回 TCP 流。
              最终将所有数据发送到目标服务器。

    中继节点：在接收到来自其它节点的数据包后根据数据包中所配置的数据包信息转发或
              放大（UDP 多线路多倍发包）UDP 包，并且需要完成最优路径计算。

    控制节点：一个特殊的中继节点，作为社区的中央管控节点使用，负责提供社区中的关键信息


社区拓扑样例：

    社区拓扑为网状拓扑，受限于字符画排版，没有完全表现出网状结构


                                           |                                                
                                           |          +------+              +------+        
                                           |          | 中继 |--------------| 控制 |        
                                           |         /+------+\             +------+        
                                           |        /          \                            
                                           |       /            \                           
                              +------+     |      /              \+------+                  
                              | 中继 |-----|-----+----------------| 出口 |----------+       
                             /+------+     |      \              /+------+          |       
                            /    |         |       \            /                   |       
                           /     |         |        \          /                    |       
                          /      |         |         \        /                     |       
                  +------+       |         |          +------+                      |       
        +-------> | 中继 |       |         |          | 中继 |                      |       
        |         +------+       |         |          +------+                      |       
        |            |    \      |         |         /    |   \                     |       
        |            |     \     |         |        /     |    \                    |       
        |            |      \    |         |       /      |     \                   V       
        |            |       \+------+     |      /       |      \                          
        |            |        | 中继 |-----|------        |       \+------+     +------+    
        |            |        +------+     |      \       |        | 出口 |---> | 目标 |    
        |            |       /   |         |       \      |       /+------+     +------+    
        |            |      /    |         |        \     |      /                          
        |            |     /     |         |         \    |     /                   ^       
        |            |    /      |         |          \   |    /                    |       
        |         +------+       |         |          +------+/                     |       
        +-------> | 中继 |       |         |          | 中继 |                      |       
        |         +------+       |         |          +------+\                     |       
        |                 \      |         |         /         \                    |       
        |                  \     |         |        /           \                   |       
        |                   \    |         |       /             \                  |       
        |                    \   |         |      /               \                 |       
    +--------+                +------+     |     /                 +------+         |       
    | 客户端 |--------------> | 中继 |-----|----+------------------| 出口 |---------+       
    +--------+                +------+     |                       +------+                 
                                           |                                                
                                           |                                                


一些假想的重要 Feature：

    UDP Only: 社区内部只转发 UDP 包。

    社区新成员接入：新成员向社区中的任意一个中继节点发起接入请求，中继节点比对控制节点提供的
                    密钥判断是否允许接入，若允许接入，则向新成员提供完整的节点列表。
                    节点列表只存在于内存中，当节点重启后，必须重新接入

    UDP 多路多倍发包：中继节点根据客户端数据包中配置的多倍发包信息将同一个 UDP 包从多条线路发出
                      单条线路不会发出2个相同内容的包，所有多倍发包均采用多线路分流

    中继节点最佳路由计算：中继节点需要计算到客户端所指定的出口节点的最优路径并将数据包导向最优路径

    核心控制节点：社区中有且只有一个控制节点，由控制节点提供社区中所有的关键信息。
                  控制节点是一个特殊的中继节点，且在传输过程中必须对 GFW 不可见。

    临时入口不变原则：客户端接入后，可以选择使用多个社区入口和一个社区出口，
                      在其重新接入之前这些被选择的节点不会改变。
                      客户端应当为社区提供数据包的第一跳信息，最终此数据包的响应包将由第一跳回传给客户端。


功能分层：

    +-------------------+
    | 第三方 TCP 适配器 |
    +-------------------+------------------+
    |    UDP 接收器     |    TCP 适配器    |
    +-------------------+------------------+
    |              数据接入层              |
    +--------------------------------------+
    |                逻辑层                |
    +--------------------------------------+
    |                协议层                |
    +--------------------------------------+
    |                传出层                |
    +--------------------------------------+


    第三方 TCP 适配器：可以使用第三方软件进行 TCP 适配，由第三方 TCP 适配器适配得到的
                       UDP 数据包将被当作来自于普通应用程序的 UDP 数据包

    UDP 接收器：负责接收 UDP 数据包并将数据传入数据接入层

    TCP 适配器：负责 TCP 流于 UDP 流之间的转换，并将数据传入数据接入层。
                TCP 适配器只存在于客户端节点和出口节点上

    数据接入层：解析接收到的数据包，将纯粹的数据传入逻辑层

    逻辑层：执行逻辑判断、路由计算、数据包改装等任务，并将将要传出的数据传入协议层

    协议层：对即将要发出的数据进行封装，使其成为一个合法的 Neverland 数据包

    传出层：将协议层封装好的数据包发出
'''


if __name__ == '__main__':
    print(__doc__)