import logging
from flask import Flask, request

# Configure the logging
logging.basicConfig(level=logging.INFO)  # Set the desired logging level

app = Flask(__name__)

# CPU Usage-Intensive Code
def cpu_usage_intensive_task(iterations):
    for _ in range(iterations):
        # A simple calculation to consume CPU
        result = 0
        for i in range(10000):
            result += i

# Memory Usage-Intensive Code
def memory_usage_intensive_task(memory_mb):
    # Convert MB to bytes
    bytes_to_allocate = memory_mb * 1024 * 1024

    # Create a large list to consume memory
    data = [0] * (bytes_to_allocate // 4)  # Assuming each integer takes 4 bytes

    # Optionally, you can modify the list to increase memory usage further
    # For example, fill the list with some data:
    # data = [i for i in range(bytes_to_allocate // 4)]

    # Ensure the list is not garbage collected
    global _global_data
    _global_data = data

@app.route('/')
def health_check():
    return 'Service is up!', 200

@app.route('/cpu_intensive')
def cpu_intensive():
    iterations = int(request.args.get('iterations', '10'))

    # Log the request
    logging.info(f"Received CPU intensive request with {iterations} iterations")

    # Execute the CPU intensive task with the specified iterations
    cpu_usage_intensive_task(iterations)

    # Log the completion of the task
    logging.info("CPU intensive task completed successfully")

    return f'CPU Intensive Task Executed Successfully with {iterations} iterations'

@app.route('/memory_intensive')
def memory_intensive():
    memory_mb = int(request.args.get('memory_mb', '100'))

    # Log the request
    logging.info(f"Received memory intensive request with {memory_mb} MB")

    # Execute the memory intensive task with the specified memory_mb
    memory_usage_intensive_task(memory_mb)

    # Log the completion of the task
    logging.info(f"Memory intensive task completed successfully with {memory_mb} MB")

    return f'Memory Intensive Task Executed Successfully with {memory_mb} MB of memory consumption'

if __name__ == '__main__':
    app.run()
