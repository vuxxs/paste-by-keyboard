import os
import pyautogui
import time
import clipboard
import keyboard
import configparser
from loguru import logger


def type_clipboard_text(kpdelay):
    text = clipboard.paste()

    pyautogui.typewrite(text, interval=kpdelay)


def release_held_keys():
    keyboard.release("ctrl")
    keyboard.release("shift")


def on_termination_hotkey():
    logger.debug("Exit hotkey pressed. Terminating script..")
    release_held_keys()
    quit()


def main():
    FILE_DIR = os.path.dirname(os.path.abspath(__file__))

    logger.info("Welcome to paste-by-keyboard 4.0")
    logger.debug("Reading settings.ini")

    config = configparser.ConfigParser()

    try:
        config.read(os.path.join(FILE_DIR, "settings.ini"))

        PASTE_HOTKEY = config["Hotkeys"].get("paste", "")
        key_press_delay = config.get("Misc", "delay")
        if PASTE_HOTKEY == "" or key_press_delay == "":
            raise ValueError("Values in config file can't be blank")

        logger.debug("Finished reading settings.ini successfully")
    except Exception as e:
        logger.debug("Error trying to read settings.ini")
        logger.debug("Resulting to default values. (Paste=F12, delay=0)")
        PASTE_HOTKEY = "F12"
        key_press_delay = 0

    logger.debug(f"Listening for hotkeys. Paste Hotkey={PASTE_HOTKEY}")

    logger.info("Press ctrl + shift + Q to quit anytime")

    hotkey_was_pressed = False
    while True:
        hotkey_is_pressed = keyboard.is_pressed(PASTE_HOTKEY)

        if hotkey_is_pressed and not hotkey_was_pressed:
            release_held_keys()
            type_clipboard_text(key_press_delay)

        hotkey_was_pressed = hotkey_is_pressed

        if keyboard.is_pressed("ctrl+shift+q"):
            on_termination_hotkey()

        time.sleep(0.01)


if __name__ == "__main__":
    main()
