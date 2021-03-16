#!/usr/bin/env python3
"""
This class simulates the temperature with dependency of day, year and a random (moving average) part. The speed of
time can be accelerated.
"""

import random
import math
import time


class SimulateTemperatures:
    def __init__(self, time_factor=100, day_amplitude=5, year_amplitude=-5, average=2.5, seed=None):
        # Config parameters
        self.t_factor = time_factor  # the simulated time is t_factor faster than the real time, 100: 1 day in 14,4 min
        self.day_amplitude = day_amplitude
        self.year_amplitude = year_amplitude  # if <0, it starts in winter
        self.average = average
        self.skew_factor = 0.1  # for the moving average, the higher, the faster the changes
        self.moving_avg_boundary = 7.5

        # Internal Variables
        self.start_time = time.time()
        self.moving_average = 0
        random.seed(seed)

    def get_temp(self):
        current_time = time.time() - self.start_time

        # Build the deterministic part of the temperature
        temperature = self.average
        temperature += self.day_amplitude * math.cos(2*math.pi*current_time*self.t_factor/(24*3600))
        temperature += self.year_amplitude * math.cos(2*math.pi*current_time*self.t_factor/(365.25*24*3600))

        # Calculate the moving average part of the simulated temperature, which is between +-5°C
        self.moving_average += random.normalvariate(mu=0, sigma=self.skew_factor)
        if self.moving_average > self.moving_avg_boundary:
            self.moving_average -= self.skew_factor
        elif self.moving_average < -self.moving_avg_boundary:
            self.moving_average += self.skew_factor
        # print("moving avg: {} °C".format(self.moving_average))
        temperature += self.moving_average

        # return the simulated part
        return round(temperature, 3)


if __name__ == "__main__":
    print("Creating a class of simulated temperatures with day, year and random influence.")
    simulator = SimulateTemperatures(time_factor=100, day_amplitude=5, year_amplitude=-5, average=2.5)

    while True:
        print("The temperature is: {} °C".format(simulator.get_temp()))
        time.sleep(1)
