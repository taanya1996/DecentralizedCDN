#Script to plot metrics
import csv
import matplotlib.pyplot as plt

n_nodes = 4

def read_csv():  
    block_rows = []
    unblock_rows = [] 
    
    for i in range(1, n_nodes+1):
        block_file_name = f"block_time_delta_node_{i}.csv"    
        with open(block_file_name, "r") as file:
            csv_reader = csv.reader(file)
            #Skip reading header
            next(csv_reader)
            for row in csv_reader():
                block_rows.append(row)
                
        unblock_file_name = f"unblock_time_delta_node_{i}.csv"
        with open(unblock_file_name, "r") as file:
            csv_reader = csv.reader(file)
            #Skip reading header
            next(csv_reader)
            for row in csv_reader():
                unblock_rows.append(row)
     
    return block_rows, unblock_rows

def plot_block_time_delta(block_rows):
    #block_rows : Array of rows
    counter =1
    data_points = []
    time_delta = []
    for row in block_rows:
        data_points.append(counter)
        counter +=1
        time_delta.append(row[-1])
    
    plt.plot(data_points, time_delta, marker = 'o', linestyle='-', color='b')
    plt.xlabel('Datapoints for block time delta')
    plt.ylabel('Time delta')
    plt.title(f'Time delta between identifying block and actual block in a system of {n_nodes} nodes')

def plot_unblock_time_delta(unblock_rows):
    #block_rows : Array of rows
    counter =1
    data_points = []
    time_delta = []
    for row in unblock_rows:
        data_points.append(counter)
        counter +=1
        time_delta.append(row[-1])
    
    plt.plot(data_points, time_delta, marker = 'o', linestyle='-', color='b')
    plt.xlabel('Datapoints for unblock time delta')
    plt.ylabel('Time delta')
    plt.title(f'Time delta between identifying unblock and actual unblock in a system of {n_nodes} nodes')


if __name__ == '__main__':
    block_rows, unblock_rows = read_csv()
    plot_block_time_delta(block_rows)
    plot_unblock_time_delta(unblock_rows)
    