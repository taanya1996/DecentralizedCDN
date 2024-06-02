import definitions
import application
import json

application.initialize_nodes()

no_waves = 5

my_node = application.my_node

print('Testing Threshold signature functionality.')
for wave in range(no_waves):
    #TODO start with partial signature.
    application.sign(my_node.node_id, wave, my_node.private_key_share)

