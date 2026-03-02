from phy_flowgraph import phy_flowgraph
import time

tb = phy_flowgraph()
# tb.set_noise_voltage(2.0)   # set BEFORE start
tb.start()

print("Noise = 2")
tb.set_noise_voltage(2.0)
time.sleep(30)

# print("Noise = 0.5")
# tb.set_noise_voltage(0.5)
# time.sleep(5)

# print("Noise = 1.0")
# tb.set_noise_voltage(1.0)
# time.sleep(5)

print("Noise = 0.0")
tb.set_noise_voltage(0.0)
time.sleep(5)

tb.stop()
tb.wait()