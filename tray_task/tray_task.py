import base64
import os
import signal
from io import BytesIO

from PIL import Image
from pystray import MenuItem, Icon


class TrayTask:
    logo_base64 = "iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAIAAAADnC86AAAACXBIWXMAAC4jAAAuIwF4pT92AAAB6UlEQVRYhe2XvariQBiG31m2G+tcQIRYCIKIIBoQg4VgJ6ijN2ARbyGVV2CvrYQU1lZKbsHOQnu9iWzxLWM2fyecDEcW8laTLzPzyJMvGWRBEOAT+fURagkuwR8E7/d7xhhjbLFYfLnXer2myQrAh8OBBq7rvl6vPDvmTBb48Xicz2fDMIQQAHzf/yHw5XIBsFqthsMhgOPx+ENg8lyv19vtNlTbTgWTZwCmaTYaDcMwoNR2Kpg8CyE45wDm8zmU2k4Fk2d6ugB6vR6U2k4GS8+DwYAqpmnSQJXtZDB5tixL13WqcM7ppVJlOxlMnsfjcbg4mUygznYCWHrudDrher/fp4ES2wlg8gyg2+2G65qmWZYFRbYTwOTZcZz4reVyCUW2o2Dpmd6fSGSTF7cdBUvPo9GIxVKtVulucdtRsDwHs1Pc9u/whfTseV6tVktccLvdZrMZAN/3p9Pp98lBKLvdjorP5zNIDx0YQohI3bbt+J5p+Uc1eRZCaJqW8VvpwCho+w2WnukLlRHZ8EV6+w2W/Sy/UGmRB0aR3n43V07PADjnjuNsNhvXdbfbbXz+9XrNWF6pVHRd/9sI9/udqp7n5WmN0+kUny+bKzu2bb+bS3putVp5FjebTRp82zYLyv/HJbgE/+/gP8FsXYe+opj9AAAAAElFTkSuQmCC"

    def quit_application(self):
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)

    def setup_systray(self):
        menu = (
            MenuItem('退出', self.quit_application),
        )
        logo = BytesIO(base64.b64decode(self.logo_base64))
        # image = Image.open("logo.png")
        image = Image.open(logo)
        icon = Icon("name", image, "AutoLoader", menu=menu)
        icon.run()
