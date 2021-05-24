import retrying


@retrying.retry(stop_max_attempt_number=3, wait_fixed=5000)
def init():
    ...  # TODO
