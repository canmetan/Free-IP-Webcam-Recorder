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
import time
import argparse
import cv2
import os
import logging
import threading
import sys
from pathlib import Path
from datetime import datetime
from collections import deque

from logging_util import setup_logger


class VideoStreamCapture:
    def __init__(self, stream_url: str, target_folder_path: str, buffer_size: int = 600, verbose: bool = True,
                 micro_sleep_time: float = 0.01, max_sequential_fail_attempts: int = 20):
        """
        Parameters for video stream capture

        :param stream_url: URL or IP of the video stream
        :param target_folder_path: If the images are to be saved, both the logs and the images will be written here.
        If left empty, just a folder with date time will be written to the disk.
        :param buffer_size: Size of the frame buffer.
        :param verbose: If True, informational outputws will be there
        :param micro_sleep_time: When we wait for a frame to come in etc we will wait this amount.
        :param max_sequential_fail_attempts: Back to back, we will attempt this many number of requests until termination.
        """
        # Setting up the video stream
        self.stream_url = stream_url
        self.video_capture = cv2.VideoCapture(stream_url)
        self.max_sequential_fail_attempts: int = max_sequential_fail_attempts
        self.frames: deque = deque(maxlen=buffer_size)
        self.micro_sleep_time: float = micro_sleep_time
        self.keep_querying = True  # Making this false will stop the requests
        self.verbose = verbose

        # Create a directory to save the files to.
        if not target_folder_path or target_folder_path == '':
            target_folder_path = os.path.join(os.getcwd(), f'capture_{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}')
            self.target_folder_path = target_folder_path

    def _query_frame(self):
        """
        :return: A single frame
        """
        # Local variables
        num_failed_attempts: int = 0
        frame = None

        while num_failed_attempts < self.max_sequential_fail_attempts:
            _, frame = self.video_capture.read()

            # Check for a frame from the stream.
            if frame is None:
                num_failed_attempts += 1
                # This is necessary not to hog the network nor the CPU
                time.sleep(self.micro_sleep_time)
                continue
            # Frame retrieval successful
            return frame

        # Max attempts were reached.
        raise IOError('No output from the stream. Ran out of maximum number of attempts.')

    def _query_frames(self):
        """
        Takes frames from the web stream.

        :return: Nothing
        """

        while self.keep_querying:
            try:
                frame = self._query_frame()
                assert (frame is not None)
            except (IOError, AssertionError) as err:
                logging.error(str(err))
                sys.exit(1)

            self.frames.append(frame)

        logging.info('Querying has just finished.')

        self.video_capture.release()

    def signal_stop_querying(self):
        # This will terminate the query_frames function.
        self.keep_querying = False

    def get_frame_from_deque(self, pop_right=False):
        """
        Fetches frames from the dequeue.

        :param pop_right: When True, fetches from the front (the latest frame). When False, takes the last frame.
        :return: Image
        """
        # if self.verbose:
        #     logging.info(f'Number of frames in the buffer: {len(self.frames)}')
        # If the deque is empty return a frame
        if self.frames:
            if pop_right:
                return self.frames.pop()
            else:
                return self.frames.popleft()
        else:
            # Dequeue is empty...
            return None

    def show_live_stream_video(self):
        """
        Use this function if you want to only display the video stream.

        :return:
        """
        setup_logger()
        # First setup the console logger....

        logging.info(f'Starting to capture stream from: {self.stream_url}')

        # Now display the image
        while True:
            try:
                frame = self._query_frame()
                assert (frame is not None)
            except (IOError, AssertionError) as err:
                logging.error(str(err))
                sys.exit(1)

            cv2.imshow('frame', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        self.signal_stop_querying()

    def record_live_stream_to_folder(self,
                                     interval_in_seconds: float,
                                     max_num_images: int):
        # First, setup the output folder and the logger....
        Path.mkdir(Path(self.target_folder_path), exist_ok=True)
        setup_logger(self.target_folder_path)

        # Temporary variables
        num_images_saved: int = 0

        logging.info(f'Recording images to: "{self.target_folder_path}"')
        logging.info(f'It will record every {interval_in_seconds} seconds.')
        if max_num_images == -1:
            logging.info(f'Indefinitely')
        else:
            logging.info(f'Until {max_num_images} images have been written to the disk.')
        logging.info('You can kill this program at any time.')

        # Start the stream
        logging.info(f'Starting to capture stream from: {self.stream_url}')
        reader_thread = threading.Thread(target=self._query_frames, daemon=True, args=())
        reader_thread.start()

        # Either do it infinitely or until max num images are saved
        while num_images_saved < max_num_images or max_num_images == -1:
            frame = self.get_frame_from_deque()
            image_path: str = os.path.join(self.target_folder_path,
                                           f'{datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}.png')
            if frame is None:
                # Only wait 0.01 seconds if there are currently no frames. Needed for fast computers / slow internet
                time.sleep(self.micro_sleep_time)
            else:
                cv2.imwrite(image_path, frame)
                time.sleep(interval_in_seconds)
                num_images_saved += 1

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            if self.verbose and num_images_saved > 0 and num_images_saved % 10 == 0:
                logging.info(f'{num_images_saved} images have been saved.')
            if self.verbose and num_images_saved > 0 and num_images_saved % 100 == 0:
                logging.info(f'{self.target_folder_path} contains all the saved images...')

        self.signal_stop_querying()
        if self.verbose:
            logging.info(f'In total {num_images_saved} images have been saved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Live stream handler to display or record IP webcams.',
                                     prog='live_stream_handler', usage='python %(prog)s.py [options]')
    parser.add_argument('-u', '--url', type=str, nargs='+',
                        default='https://s82.ipcamlive.com/streams/52m18dihyryxpvwv7/stream.m3u8',
                        help='Stream URL or IP address. Default: '
                             '"https://s82.ipcamlive.com/streams/52m18dihyryxpvwv7/stream.m3u8"')
    parser.add_argument('-d', '--display_only', help='Only displays the stream and does not record it.',
                        action='store_true')
    parser.add_argument('-b', '--buffer_size', type=int, default=600,
                        help='Size of the buffer to store the number of frames. The bigger this is the smoother '
                             'stream will be...')
    parser.add_argument('-t', '--target_folder', type=str, nargs='?',
                        help='Only used when saving screenshots. '
                             'Path to the folder to write. Default will be a date - time named folder')
    parser.add_argument('-q', '--quiet', dest='quiet', help='Suppress Output', action='store_true')
    parser.add_argument('-i', '--screenshot_interval_in_seconds', nargs='?', type=float, default=60.0,
                        help='Waits this many seconds until capturing another screenshot. Default: 60')
    parser.add_argument('-m', '--max_num_images', nargs='?', type=int, default=-1,
                        help='Stops after capturing this many images. If nothing is passed or -1 is passed, does not '
                             'stop.')

    args = parser.parse_args()

    # TODO: check valid URL
    vsc: VideoStreamCapture = VideoStreamCapture(
        stream_url=args.url[0], target_folder_path=args.target_folder,
        buffer_size=args.buffer_size, verbose=not args.quiet)

    # If it is a display only thing do not record anything.
    if args.display_only:
        vsc.show_live_stream_video()
    else:
        vsc.record_live_stream_to_folder(interval_in_seconds=args.screenshot_interval_in_seconds,
                                         max_num_images=args.max_num_images)
