#!/usr/bin/env python3
# coding=utf-8
import time
import os
import sys
import Adafruit_SSD1306 as SSD

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

# V1.0.6 - Modified: added CPU temp, removed time
class Yahboom_OLED:
    def __init__(self, i2c_bus=7, clear=False, debug=False):
        self.__debug = debug
        self.__clear = clear
        self.__clear_count = 0
        self.__top = -2
        self.__x = 0

        self.__BUS_LIST = [1, 0, 7, 8]
        self.__bus_index = 0
        if i2c_bus != "auto":
            self.__i2c_bus = int(i2c_bus)
            self.__bus_index = 0xFF
        else:
            self.__i2c_bus = self.__BUS_LIST[self.__bus_index]

        self.__total_last = 0
        self.__idle_last = 0
        self.__str_CPU = "CPU:0%"

        self.__WIDTH = 128
        self.__HEIGHT = 32
        self.__image = Image.new('1', (self.__WIDTH, self.__HEIGHT))
        self.__draw = ImageDraw.Draw(self.__image)
        self.__font = ImageFont.load_default()

    def __del__(self):
        if self.__debug:
            print("---OLED-DEL---")

    def begin(self):
        try:
            self.__oled = SSD.SSD1306_128_32(
                rst=None, i2c_bus=self.__i2c_bus, gpio=1)
            self.__oled.begin()
            self.__oled.clear()
            self.__oled.display()
            if self.__debug:
                print("---OLED begin ok!---")
            return True
        except:
            if self.__debug:
                print("---OLED No Found!---:", self.__BUS_LIST[self.__bus_index])
            if self.__bus_index == 0xFF:
                return
            max_bus = len(self.__BUS_LIST)
            self.__bus_index = (self.__bus_index + 1) % max_bus
            self.__i2c_bus = self.__BUS_LIST[self.__bus_index]
            return False

    def clear(self, refresh=False):
        self.__draw.rectangle(
            (0, 0, self.__WIDTH, self.__HEIGHT), outline=0, fill=0)
        if refresh:
            try:
                self.refresh()
                return True
            except:
                return False

    def add_text(self, start_x, start_y, text, refresh=False):
        if start_x > self.__WIDTH or start_x < 0 or start_y < 0 or start_y > self.__HEIGHT:
            if self.__debug:
                print("oled text: x, y input error!")
            return
        x = int(start_x + self.__x)
        y = int(start_y + self.__top)
        self.__draw.text((x, y), str(text), font=self.__font, fill=255)
        if refresh:
            self.refresh()

    def add_line(self, text, line=1, refresh=False):
        if line < 1 or line > 4:
            if self.__debug:
                print("oled line input error!")
            return
        y = int(8 * (line - 1))
        self.add_text(0, y, text, refresh)

    def refresh(self):
        self.__oled.image(self.__image)
        self.__oled.display()

    def getCPULoadRate(self, index):
        count = 10
        if index == 0:
            f1 = os.popen("cat /proc/stat", 'r')
            stat1 = f1.readline()
            data_1 = []
            for i in range(count):
                data_1.append(int(stat1.split(' ')[i+2]))
            self.__total_last = data_1[0]+data_1[1]+data_1[2]+data_1[3] + \
                data_1[4]+data_1[5]+data_1[6]+data_1[7]+data_1[8]+data_1[9]
            self.__idle_last = data_1[3]
        elif index == 4:
            f2 = os.popen("cat /proc/stat", 'r')
            stat2 = f2.readline()
            data_2 = []
            for i in range(count):
                data_2.append(int(stat2.split(' ')[i+2]))
            total_now = data_2[0]+data_2[1]+data_2[2]+data_2[3] + \
                data_2[4]+data_2[5]+data_2[6]+data_2[7]+data_2[8]+data_2[9]
            idle_now = data_2[3]
            total = int(total_now - self.__total_last)
            idle = int(idle_now - self.__idle_last)
            usage = int(total - idle)
            usageRate = int(float(usage / total) * 100)
            self.__str_CPU = "CPU:" + str(usageRate) + "%"
            self.__total_last = 0
            self.__idle_last = 0
        return self.__str_CPU

    def getCPUTemp(self):
        try:
            with open("/sys/devices/virtual/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000.0
            return "{:.1f}C".format(temp)
        except:
            return "--.-C"

    def getUsagedRAM(self):
        cmd = "free | awk 'NR==2{printf \"RAM:%2d%% -> %.1fGB \", 100*($2-$7)/$2, ($2/1048576.0)}'"
        FreeRam = subprocess.check_output(cmd, shell=True)
        str_FreeRam = str(FreeRam).lstrip('b\'')
        str_FreeRam = str_FreeRam.rstrip('\'')
        return str_FreeRam

    def getUsagedDisk(self):
        cmd = "df -h | awk '$NF==\"/\"{printf \"SDC:%s -> %.1fGB\", $5, $2}'"
        Disk = subprocess.check_output(cmd, shell=True)
        str_Disk = str(Disk).lstrip('b\'')
        str_Disk = str_Disk.rstrip('\'')
        return str_Disk

    def getLocalIP(self):
        ip = os.popen(
            "/sbin/ifconfig enP8p1s0 | grep 'inet' | awk '{print $2}'").read()
        ip = ip[0: ip.find('\n')]
        if(ip == '' or len(ip) > 15):
            ip = os.popen(
                "/sbin/ifconfig wlP1p1s0 | grep 'inet' | awk '{print $2}'").read()
            ip = ip[0: ip.find('\n')]
            if(ip == ''):
                ip = 'x.x.x.x'
        if len(ip) > 15:
            ip = 'x.x.x.x'
        return ip

    def getWifiSetupMode(self):
        """Check if WiFi setup portal is active. Returns IP string or None."""
        try:
            with open("/tmp/wifi_setup_active", "r") as f:
                return f.read().strip()
        except:
            return None

    def main_program(self):
        state = False
        try:
            cpu_index = 0
            state = self.begin()
            while state:
                self.clear()
                if self.__clear:
                    self.refresh()
                    return True

                setup_ip = self.getWifiSetupMode()
                if setup_ip:
                    self.add_line("** WiFi Setup **", 1)
                    self.add_line("Join: JetsonSetup", 2)
                    self.add_line("Pass: jetson1234", 3)
                    self.add_line("Open:" + setup_ip, 4)
                    self.refresh()
                    time.sleep(1)
                    continue

                str_CPU = self.getCPULoadRate(cpu_index)
                str_Temp = self.getCPUTemp()
                if cpu_index == 0:
                    str_FreeRAM = self.getUsagedRAM()
                    str_Disk = self.getUsagedDisk()
                    str_IP = "IP:" + self.getLocalIP()
                self.add_text(0, 0, str_CPU)
                self.add_text(68, 0, str_Temp)
                self.add_line(str_FreeRAM, 2)
                self.add_line(str_Disk, 3)
                self.add_line(str_IP, 4)
                self.refresh()
                cpu_index = cpu_index + 1
                if cpu_index >= 5:
                    cpu_index = 0
                time.sleep(.1)
            if self.__clear:
                self.__clear_count = self.__clear_count + 1
                if self.__clear_count > len(self.__BUS_LIST):
                    return True
            return False
        except:
            if self.__debug:
                print("!!!---OLED refresh error---!!!")
            return False


if __name__ == "__main__":
    try:
        oled_clear = False
        oled_debug = False
        state = False
        for arg in sys.argv:
            if str(arg) == "clear":
                oled_clear = True
            if str(arg) == "debug":
                oled_debug = True
        oled = Yahboom_OLED(clear=oled_clear, debug=oled_debug)
        while True:
            state = oled.main_program()
            if state:
                del oled
                print("---OLED CLEARED!---")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        oled.clear(True)
        del oled
        print("---Program closed!---")
        pass
