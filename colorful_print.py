# color_set_print(text:str, color:str = "normat"):
    


# print("\033[31m赤文字\033[0m")
# print("\033[32m緑文字\033[0m")
# print("\033[33m黄色文字\033[0m")
# print("\033[34m青文字\033[0m")


from typing import Literal

def color_set_print(
    text: str,
    color: Literal[
        "black", "red", "green", "yellow",
        "blue", "magenta", "cyan", "white", "normal"
    ] = "normal"
):
    colors = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "normal": "\033[0m"
    }

    color_code = colors[color]
    return f"{color_code}{text}\033[0m"