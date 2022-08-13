# Copyright Can Metan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import os


def setup_logger(export_folder_path: str = None, logging_level: int = logging.INFO):
    # Get the root logger and remove all handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:  # remove all old handlers
        logger.removeHandler(handler)

    # Set up the console Handler first
    console_handler = logging.StreamHandler()
    logger.setLevel(logging_level)
    console_handler.setLevel(logging_level)
    formatter = logging.Formatter(fmt='%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Setup a file handler if a valid folder path was given.
    if export_folder_path and os.path.isdir(export_folder_path):
        file_handler = logging.FileHandler(os.path.join(export_folder_path, 'output.log'), 'a')
        file_handler.setLevel(logging_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)  # set the new handler
