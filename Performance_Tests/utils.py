import random
import string
import os


class Colors:
    """ Class to set the colors for text.  Syntax:  print(Colors.OKGREEN +"TEXT HERE" +Colors.ENDC) """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'  # Normal default color
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_with_color(message: str, color: str):
    """
    Print a message with specified color onto console.
    :param message:
    :param color:
    """
    print(color + message + Colors.ENDC)


def print_error(message: str):
    """
    Print message onto console with "Fail" color.
    :param message:
    """
    print_with_color(message, Colors.FAIL)


def print_header(message: str):
    """
    Print message onto console with "Header" color.
    :param message:
    """
    print_with_color(message, Colors.HEADER)


def print_ok_green(message: str):
    """
    Print message onto console with "OK_GREEN" color.
    :param message:
    """
    print_with_color(message, Colors.OKGREEN)


def print_ok_blue(message: str):
    """
    Print message onto console with "OK_BLUE" color.
    :param message:
    """
    print_with_color(message, Colors.OKBLUE)


def print_header_for_step(message: str):
    print_header("\n======= {} =======".format(message))


def generate_random_string(
        prefix="", suffix="", size=20,
        characters: str=string.ascii_uppercase + string.digits):
    """
    Generate random string .
    :param prefix:  (optional) Prefix of a string.
    :param suffix:  (optional) Suffix of a string.
    :param size: (optional) Max length of a string (include prefix and suffix)
    :param characters: the characters to make string.
    :return: The random string.
    """
    left_size = size - len(prefix) - len(suffix)
    random_str = ""
    if left_size > 0:
        random_str = ''.join(
            random.choice(characters) for _ in range(left_size))
    else:
        print("Warning: Length of prefix and suffix more than %s chars"
              % str(size))
    result = str(prefix) + random_str + str(suffix)
    return result


def run_async_method(loop, method, *args):
    import asyncio
    if not loop:
        loop = asyncio.get_event_loop()
    return loop.run_until_complete(method(*args))


def create_folder(folder):
    """
    Create folder if it is not exist.
    :param folder: folder need to create.
    :return:
    """
    import errno
    try:
        os.makedirs(folder)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e
