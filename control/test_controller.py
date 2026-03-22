# test the controller

import time

from control.controller import Controller

c = Controller()
# c.set_param("noise", 0.5, source="test")
# c.set_param("packet_rate", 200, source="test")
# c.set_param("modulation", "16qam", source="test")
# c.set_param("frequency", 2450000000, source="test")

# print("Current state:")
# print(f"Noise: {c.get_param('noise')}")
# print(f"Packet Rate: {c.get_param('packet_rate')}")
# print(f"Modulation: {c.get_param('modulation')}")
# print(f"Frequency: {c.get_param('frequency')}")

c.set_param("noise", 0.5, source="test")
print(f"Noise after update: {c.get_param('noise')}")

time.sleep(5)

c.set_param("noise", 0.8, source="test")
print(f"Noise after second update: {c.get_param('noise')}")

time.sleep(5)
    
c.set_param("noise", 0.0, source="test")
print(f"Noise after third update: {c.get_param('noise')}")