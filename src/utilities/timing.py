from datetime import datetime

def print_human_readable_delta(start: datetime, end: datetime):
    """
    Calculate the delta between two datetime objects
    and print it in a human-readable format.
    """
    delta = end - start

    # Extract days, hours, minutes, and seconds
    days = delta.days
    seconds = delta.seconds
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    # Construct a human-readable format
    formatted_time = (
        f"{days}d {hours}h {minutes}m {seconds}s" if days > 0 else
        f"{hours}h {minutes}m {seconds}s" if hours > 0 else
        f"{minutes}m {seconds}s" if minutes > 0 else
        f"{seconds}s"
    )

    print(f"Elapsed time: {formatted_time}")


import time

def time_it(func):
    """
    Decorator to measure the execution time of a function
    and print it in a human-readable format.
    """
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        # Convert to human-readable format
        hours, rem = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(rem, 60)
        formatted_time = f"{int(hours)}h {int(minutes)}m {seconds:.2f}s" if hours else (
            f"{int(minutes)}m {seconds:.2f}s" if minutes else f"{seconds:.2f}s")
        
        print(f"Execution time of '{func.__name__}': {formatted_time}")
        return result

    return wrapper

# Example usage:
@time_it
def example_function():
    time.sleep(2.5)  # Simulate some work

example_function()
