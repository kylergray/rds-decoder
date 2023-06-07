import matplotlib.pyplot as plt
import numpy as np

with open('stats.txt', 'r') as file:
    samples = []
    for line in file:
        values = line.strip().split(", ")
        if len(values) == 2:
            samples.append(float(values[0]) / float(values [1]))
    print(len(samples))
    print(range(0, len(samples)))
    plt.plot(samples[:300])
    plt.xlim((0,300))
    plt.xlabel('Time (Seconds)')
    plt.ylabel('Percentage of Good Blocks (# Good Blocks / Theoretical Max)')
    average = sum(samples) / len(samples)
    plt.axhline(average, color='red', linestyle='--', label='Average')
    plt.title('Good Block Success Rate Over Time')
    plt.show()