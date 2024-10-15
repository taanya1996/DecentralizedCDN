#Script to plot metrics
import csv
import matplotlib.pyplot as plt
import numpy as np
import re

n_nodes = 4

def plot_latency_metrics():
    colors = ['blue', 'green', 'red', 'purple']
    counter =1
    min_latency = 10000000 
    max_latency = -1
    for i in range(1, n_nodes+1):
        file_name = f"metrics/latency_data_{i}.txt"
        data_points = []
        latency = []
        with open(file_name, "r") as file:
            lines =  file.readlines()
        
        node_latencies = []
        for line in lines:
            latency_vals = line.split(' ')
            node_latencies.append(float(latency_vals[-4]))
            
        data_points.append(counter)
        counter +=1
        avg_latency = sum(node_latencies)/len(node_latencies)
        latency.append(avg_latency)
        min_latency = min(min_latency, min(latency))
        max_latency = max(max_latency, max(latency))
        plt.plot(data_points, latency, marker = 'o', linestyle='-', color=colors[i-1])
    
    plt.ylim(min_latency - 1, max_latency + 1)
    plt.xlabel('Nodes')
    plt.ylabel('Avg Latency to communicate with nodes.')
    plt.title(f'Average Latency observed in {n_nodes} nodes')
    plt.grid(True)
    plt.show()

def plot_dag_progress_rate():
    colors = ['blue', 'green', 'red', 'purple']
    counter = 1
    min_time_delta = 10000000
    max_time_delta =  -1
    for i in range(1, n_nodes+1):
        data_points = []
        time_delta = []
        file_name = f"metrics/dag_round_rate_{i}.csv"
        with open(file_name, "r") as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                row = [float(val) for val in row]
                data_points.append(counter)
                counter += 1
                time_delta.append(row[0])
            print(f"Average time to progress round for node {i}: {sum(time_delta)/len(time_delta)}")
            min_time_delta = min(min_time_delta, min(time_delta))
            max_time_delta = max(max_time_delta, max(time_delta))
            plt.plot(data_points, time_delta, marker = 'o', linestyle='-', color=colors[i-1])
    
    plt.ylim(min_time_delta - 1, max_time_delta + 1)
    plt.xlabel('Datapoints for round progress rate')
    plt.ylabel('Time delta for round progress')
    plt.title(f'Time delta to progress rounds in a system of {n_nodes} nodes')
    plt.grid(True)
    plt.show()
        
def plot_block_time_delta():
    #block_rows : Array of rows

    colors = ['blue', 'green', 'red', 'purple']
    counter =1
    min_time_delta = 10000000
    max_time_delta =  -1
    for i in range(1, n_nodes+1):
        data_points = []
        time_delta = []
        block_file_name = f"metrics/block_time_delta_node_{i}.csv"  
        with open(block_file_name, "r") as file:
            csv_reader = csv.reader(file)
            #Skip reading header
            next(csv_reader)
            for row in csv_reader:
                row = [int(val) if val.isdigit() else float(val) if val.replace('.','').isdigit() else val for val in row]
                data_points.append(counter)
                counter += 1
                time_delta.append(row[-1])
            print(f"Average time delay to identify and block the IP for node {i}: {sum(time_delta)/len(time_delta)}")
            min_time_delta = min(min_time_delta, min(time_delta))
            max_time_delta = max(max_time_delta, max(time_delta))
            plt.plot(data_points, time_delta, marker = 'o', linestyle='-', color=colors[i-1])
    
    
    plt.ylim(min_time_delta - 1, max_time_delta + 1)
    plt.xlabel('Datapoints for block time delta')
    plt.ylabel('Time delta')
    plt.title(f'Time delta between identifying block and actual block in a system of {n_nodes} nodes')
    plt.grid(True)
    plt.show()

def plot_unblock_time_delta():
    colors = ['blue', 'green', 'red', 'purple']
    counter =1
    min_time_delta = 10000000
    max_time_delta =  -1
    for i in range(1, n_nodes+1):
        data_points = []
        time_delta = []
        block_file_name = f"metrics/unblock_time_delta_node_{i}.csv"  
        with open(block_file_name, "r") as file:
            csv_reader = csv.reader(file)
            #Skip reading header
            next(csv_reader)
            for row in csv_reader:
                row = [int(val) if val.isdigit() else float(val) if val.replace('.','').isdigit() else val for val in row]
                data_points.append(counter)
                counter += 1
                time_delta.append(row[-1])
            print(f"Average time delay to identify and block the IP for node {i}: {sum(time_delta)/len(time_delta)}")
            min_time_delta = min(min_time_delta, min(time_delta))
            max_time_delta = max(max_time_delta, max(time_delta))
            plt.plot(data_points, time_delta, marker = 'o', linestyle='-', color=colors[i-1])
    
    
    plt.ylim(min_time_delta - 1, max_time_delta + 1)
    plt.xlabel('Datapoints for block time delta')
    plt.ylabel('Time delta')
    plt.title(f'Time delta between identifying unblock and actual unblock in a system of {n_nodes} nodes')
    plt.grid(True)
    plt.show()

    
def plot_rbcast_overhead():
    counter = 1
    colors = ['blue', 'green', 'red', 'purple']
    min_time_delta = 10000000
    max_time_delta =  -1
    
    for i in range(1, n_nodes+1):
        file_name = f"metrics/rbcast_time_delta_{i}.csv"
        data_points = []
        time_delta = []
        with open(file_name, "r") as file:
            csv_reader = csv.reader(file)
            #Skip reading header
            next(csv_reader)
            for row in csv_reader:
                row = [int(val) if val.isdigit() else float(val) if val.replace('.','').isdigit() else val for val in row]
                data_points.append(counter)
                counter +=1
                time_delta.append(row[-1])
            min_time_delta = min(min_time_delta, min(time_delta))
            max_time_delta = max(max_time_delta, max(time_delta))
            plt.plot(data_points, time_delta, marker = 'o', linestyle='-', color=colors[i-1])
        
    plt.xlabel('Datapoints for rbcast overhead')
    plt.ylabel('Time delta')
    plt.title(f'Reliable Broadcast overhead in a system of {n_nodes} nodes')
    plt.grid(True)
    plt.show()

if __name__ == '__main__':
    plot_latency_metrics()
    plot_dag_progress_rate()
    plot_block_time_delta()
    plot_unblock_time_delta()
    plot_rbcast_overhead()