"""Take picture from webcam"""
import os
import time
import re
from functools import partial
import cv2
import pytesseract
from bs4 import BeautifulSoup
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.uix.button import Label, Button
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
import numpy as np
from skimage.transform import rotate
from deskew import determine_skew
from modules import load_config as config
from classes import sickw_results

# from classes import google_sheets


print(f"Importing {os.path.basename(__file__)}...")


BLACKLIST = ["BCGA"]


def deskew(image: Image):
    """take image and return straight image"""

    angle = determine_skew(image)
    if angle is None:
        angle = 0
    rotated = rotate(image, angle, resize=False) * 255
    return rotated.astype(np.uint8)


def sickw_html_to_dict(html):
    soup = BeautifulSoup(html, "html.parser")
    return_dict = {}
    for line in soup.findAll("br"):
        line_next = line.nextSibling
        if line_next != line and line_next is not None:
            data = line_next.split(":")
            return_dict[data[0]] = data[1].strip()
            # return_list.append(br_next)

    return return_dict


class SerialCamera(GridLayout):
    """Independent app to scan serials"""

    def __init__(self, **kwargs):
        """Create GUI"""
        super(SerialCamera, self).__init__(**kwargs)
        # self.width = config.CAM_WIDTH
        # self.height = config.CAM_HEIGHT
        # self.size = [1920, 1080]

        self.cols = 1
        self.padding = 100

        self.rotate_button = Button(text="Rotate", halign="center", size_hint=(0.1, 0.1))
        self.rotate_button.bind(on_press=self.rotate_button_fn)
        self.add_widget(self.rotate_button)

        self.threshold_slider = Slider(min=0, max=255, value=180, size_hint=(1, 0.15))
        self.threshold_slider.bind(value=self.threshold_change)
        self.add_widget(self.threshold_slider)

        self.threshold_grid = GridLayout()
        self.threshold_grid.cols = 3
        self.threshold_grid.size_hint_y = 0.1

        self.threshold_down_button = Button(text="Threshold down", halign="center")
        self.threshold_down_button.bind(on_press=partial(self.threshold_change, value=-5))
        self.threshold_grid.add_widget(self.threshold_down_button)

        self.threshold_label = Label(text=str(self.threshold_slider.value))
        self.threshold_grid.add_widget(self.threshold_label)

        self.threshold_up_button = Button(text="Threshold up", halign="center")
        self.threshold_up_button.bind(on_press=partial(self.threshold_change, value=5))
        self.threshold_grid.add_widget(self.threshold_up_button)

        self.add_widget(self.threshold_grid)

        self.image_grid = GridLayout()
        self.image_grid.cols = 2

        self.scanned_image = Image()
        self.scanned_image.width = cv2.CAP_PROP_FRAME_WIDTH
        self.scanned_image.height = cv2.CAP_PROP_FRAME_HEIGHT
        self.image_grid.add_widget(self.scanned_image)

        self.threshed_image = Image()
        self.threshed_image.width = cv2.CAP_PROP_FRAME_WIDTH
        self.threshed_image.height = cv2.CAP_PROP_FRAME_HEIGHT
        self.image_grid.add_widget(self.threshed_image)

        self.add_widget(self.image_grid)

        self.status = Label(size_hint=(0.8, 0.2))
        self.add_widget(self.status)

        self.capture = cv2.VideoCapture(config.CAM_PORT)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
        Clock.schedule_interval(self.update, 1 / 30)
        self.sickw_history = []
        self.fps_previous = 0
        self.fps_current = 0
        self.rotation = 1
        # self.theshold_value = 180

    def thresh_image(self, image):
        """take grayscale image and return Threshholded image"""
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = deskew(image)
        _, image = cv2.threshold(image, self.threshold_slider.value, 255, cv2.THRESH_BINARY)
        # image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 15)

        return image

    def rotate_button_fn(self, _):
        if self.rotation < 2:
            self.rotation += 1
        else:
            self.rotation = -1

    def threshold_change(self, caller, value=None):
        if isinstance(caller, Button):
            self.threshold_slider.value += value
        self.threshold_label.text = str(int(self.threshold_slider.value))

    def update(self, _):
        """Handle clock updates"""
        result, serial_image = self.capture.read()
        if self.rotation > -1:
            serial_image = cv2.rotate(serial_image, self.rotation)
        if result:
            threshed = self.thresh_image(serial_image)
            serial_image_data = pytesseract.image_to_data(
                threshed,
                output_type=pytesseract.Output.DICT,
                config="--psm 11",  # -c tessedit_char_whitelist=' 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'",
            )
        display_lines = "No succesful reads"
        for conf, word in zip(serial_image_data["conf"], serial_image_data["text"]):
            if conf > 40 and len(word) >= 8 and re.sub(r"[^A-Z0-9]", "", word) == word:
                blacklisted = False
                for black in BLACKLIST:
                    if black in word:
                        blacklisted = True

                if not any(d.serial_number == word for d in self.sickw_history) and not blacklisted:
                    sickw = sickw_results.SickwResults(word, sickw_results.APPLE_SERIAL_INFO)
                    self.sickw_history.append(sickw)
                if not blacklisted:
                    output = f"Conf: {conf} {word} Total: {len(self.sickw_history)} "
                    output += f"Matches: {sickw_results.SickwResults.search_list_for_serial(word, self.sickw_history)} "
                    output += f"Sucessful: {sickw_results.SickwResults.success_count(self.sickw_history)}"
                    display_lines += f" {output}\n"
                    print(display_lines)
        self.status.text = display_lines

        self.fps_current = time.time()
        fps = 1 / (self.fps_current - self.fps_previous)
        self.fps_previous = self.fps_current
        cv2.putText(threshed, str(round(fps, 2)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (0, 0, 0), 3)
        cv2.putText(serial_image, str(round(fps, 2)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (0, 0, 0), 3)

        # cv2.imshow("test", threshed)
        buf1 = cv2.flip(serial_image, 0)
        buf = buf1.tobytes()
        # if self.scanned_image.texture is None:
        self.scanned_image.texture = Texture.create(size=(config.CAM_WIDTH, config.CAM_HEIGHT), colorfmt="bgr")
        self.scanned_image.texture.blit_buffer(buf, colorfmt="bgr", bufferfmt="ubyte")

        buf1 = cv2.flip(threshed, 0)
        buf = buf1.tobytes()
        # if self.scanned_image.texture is None:
        self.threshed_image.texture = Texture.create(size=(config.CAM_WIDTH, config.CAM_HEIGHT), colorfmt="luminance")
        self.threshed_image.texture.blit_buffer(buf, colorfmt="luminance", bufferfmt="ubyte")


class SerialCameraApp(App):
    """Get image from camera and start serial check"""

    def build(self):
        Window.left = 0  # 0
        Window.top = 0
        Window.size = (config.CAM_WIDTH / 2, config.CAM_HEIGHT * 0.7)
        return SerialCamera()


if __name__ == "__main__":
    SerialCameraApp().run()