import argparse
import subprocess
import logging
import os
import sys

from gitma_canspin._helper import module_path
import gitma_canspin.gui.main as gui

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

this_file = os.path.abspath(__file__)

def run():
    logger.info("GUI started.")
    args = sys.argv
    subprocess.call(
        [
            "streamlit",
            "run",
            this_file,
            "--theme.base",
            "light",
            "--browser.gatherUsageStats",
            "false",
            "--logger.messageFormat",
            "%(asctime)s %(levelname) -7s %(name)s: %(message)s",
            "--",
            *args,
        ]
    )

def main():
    parser = argparse.ArgumentParser(description="The gitma_CANSpiN app")
    parser.add_argument(
        "--start_state",
        default=0,
        type=int,
        help="set start page for app",
    )

    args, unknown = parser.parse_known_args()
    gui.Main(args)

if __name__ == "__main__":
    main()
    