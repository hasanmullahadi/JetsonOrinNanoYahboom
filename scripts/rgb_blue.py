#!/usr/bin/env python3
from CubeNanoLib import CubeNano

bot = CubeNano(i2c_bus=7)
bot.set_RGB_Color(2)    # Blue
bot.set_RGB_Effect(6)   # Cycle breathing
bot.set_RGB_Speed(2)    # Medium
bot.set_Fan(1)          # Fan on
del bot
