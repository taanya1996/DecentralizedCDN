# This script is to test reliable broadcast features

import definitions
import application
import json

application.initialize_nodes()

#creating Vertex
round = 1
ip = 1
block = '12.1.1.1'
while(True):
    print("Do you want to bcast a vertex. Type 1 for yes, 2 for no")
    option = int(input())
    if(option==1):
        vertex_id = "1:" + str(round)
        block = block[:-1]+str(ip)
        v= definitions.Vertex(id= vertex_id,round=round,source=1,block=block)
        round +=1
        ip += 1
        application.reliable_bcast(v)
    else:
        break



