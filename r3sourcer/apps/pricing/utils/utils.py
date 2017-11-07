def format_timedelta(time_delta, with_seconds=False):
    seconds = time_delta.total_seconds()
    hours = seconds // 3600

    if hours:
        res_str = '{:g}h '.format(hours)
    else:
        res_str = ''

    minutes = (seconds % 3600) // 60

    if minutes:
        res_str = '{}{:g}min '.format(res_str, minutes)

    seconds = seconds % 60
    if with_seconds and seconds:
        res_str = '{}{:g}s'.format(res_str, seconds)

    return res_str.rstrip()
