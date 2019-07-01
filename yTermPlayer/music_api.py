#!/usr/bin/env python3
'''
yTermPlayer music api by TimeTraveller
(https://github.com/TimeTraveller-San/yTermPlayer)
Special thanks for these libraries and their contributors:
- urwid
- pafy
- mpv
'''
import mpv
import pickle
import os
import time
import threading
from random import randint
import math
from .settings import PL_DIR
import locale
from .playlist import Playlist


def structure_time(hours, minutes, seconds, *args):
    if hours == 0:
        formatter = "{:0>2d}:{:0>2d}"
        return formatter.format(minutes, seconds)
    else:
        formatter = "{:0>2d}:{:0>2d}:{:0>2d}"
        return formatter.format(hours, minutes, seconds)


def structure_time_len(seconds, minutes, *args):
    formatter = "{:0>2d}:{:0>2d}"
    return formatter.format(minutes, seconds)


class YoutubePlayer:
    def __init__(self):
        # URL of list
        self.url = ""
        # Player volume
        self._volume = 100
        # Set unlock on continous_player
        self._lock = False
        # Semaphore for the shared _lock variable
        self._lock_mutex = threading.Semaphore()
        # Open the paylists dict from pickle here
        self.saved_lists = []
        # Currently playing song name
        self._current_song = "None"
        # Current song index
        self.index = 0
        # #New playlist?
        self._new = True
        # Define queue length
        self.queue_len = 0
        # Define repeat mode 1:Repeat off | 2:Repeat current song | 3:Repeat list.
        # Default mode is 1
        self.repeat_mode = 1
        # Define random 0:Random off | 1:Random on
        self.random = 0
        # This lock is for locking in case music is paused intentionlly
        self._togglerLock = False
        # Semaphore for the shared _togglerLock variable
        self._togglerLock_mutex = threading.Semaphore()
        # Make time details dict
        self.time_details = {}
        # Random on or off?
        self._random = False
        # This is changed to true by the continous player and then back to
        # false by an event handler
        self._song_changed = False
        self.path = os.path.split(os.path.abspath(__file__))[0]
        for every_file in os.listdir(PL_DIR):
            self.saved_lists.append(every_file)
        # Initialize MPV player
        locale.setlocale(locale.LC_NUMERIC, "C")
        self.player = mpv.MPV()

    def set_repeat_mode(self, mode):
        # If invalid, set return mode to no repeat
        if(int(mode) not in [1, 2, 3]):
            self.repeat_mode = 1
        else:
            self.repeat_mode = int(mode)

    def play_random(self):
        if(self._random):
            self._random = False
        else:
            self._random = True

    def get_repeat_mode(self):
        return self.repeat_mode

    def init_playlist(self, url):
        self.playlist = Playlist(url)

    def save_current_list(self):
        try:
            filename = PL_DIR + "/" + self.playlist.title
        except Exception:  # TODO: Define proper exception type I suppose it's a KeyError
            return False
        self.saved_lists.append(filename)
        with open(filename, 'wb') as handler:
            pickle.dump({
                        'url': self.playlist.url,
                        'name': self.playlist.title
                        },
                        handler, pickle.HIGHEST_PROTOCOL)
        return True

    def load_saved_playlist(self, list_name):
        if list_name not in self.saved_lists:
            return False
        # Load list pickle object
        filename = PL_DIR + "/" + list_name
        with open(filename, 'rb') as handler:
            url = pickle.load(handler)['url']
        self.playlist = Playlist(url)
        return True

    def get_saved_lists(self):
        return self.saved_lists

    def get_next_index(self):
        try:
            assert isinstance(self.index, int), "invalid index"
        except AssertionError:
            self.index = 0
        if(self._random):
            self.next_index = randint(1, int(self.queue_len) - 1)
            return int(self.next_index)
        self.index = int(self.index)
        # repeat playlist
        if(self.repeat_mode == 3):
            if(self.index == self.queue_len - 1):
                self.next_index = 0
            else:
                self.next_index = self.index + 1
        # repeat single song
        elif(self.repeat_mode == 2):
            self.next_index = self.index
        # no repeat mode
        else:
            if(self.index == self.queue_len - 1):
                self.next_index = math.nan
            else:
                self.next_index = self.index + 1
        return self.next_index

    def get_prev_index(self):
        try:
            assert isinstance(self.index, int), "invalid index"
        except AssertionError:
            self.index = 0
        if(self.index <= 0):
            self.prev_index = math.nan
        else:
            self.prev_index = self.index - 1
        return self.prev_index

    def check_lock(self):
        self._lock_mutex.acquire()
        value = self._lock
        self._lock_mutex.release()
        return value

    @property
    def is_playing(self):
        if self.player.path:
            return True
        return False

    def toggle_lock(self, value):
        self._lock_mutex.acquire()
        self._lock = value
        self._lock_mutex.release()

    def play_at_index(self, index):
        self._song_changed = True
        self._new = False
        self.toggle_lock(True)
        self.index = index
        if math.isnan(self.index):
            pass
        # Play current index
        video = self.playlist[index]
        url = video.url
        self.current_song = video.title
        if (url is False):
            return False
        self.player.play(url)
        # Remove lock on continous_player
        while (not self.is_playing):
            self.toggle_lock(True)
        self.toggle_lock(False)
        return True

    def stop(self):
        # This maybe removed in future, isn't really needed
        self.toggle_lock(True)
        # self.player.stop()

    def get_playlist_name(self):
        return self.playlist['title']

    def get_time_details(self):
        if self.player.duration:
            total_seconds = round(self.player.duration)
        else:
            total_seconds = 0
        minutes = int(total_seconds / 60)
        seconds = total_seconds % 60
        self.time_details['total_time'] = structure_time_len(seconds, minutes)
        if self.player.playback_time:
            cur_seconds = round(self.player.playback_time)
        else:
            cur_seconds = 0
        minutes = int(cur_seconds / 60)
        seconds = cur_seconds % 60
        self.time_details['cur_time'] = structure_time_len(seconds, minutes)

        if(total_seconds != 0):
            self.time_details['percentage'] = (cur_seconds / total_seconds) * 100
        else:
            self.time_details['percentage'] = 0
        return self.time_details

    def start_playing(self):
        thread = threading.Thread(target=self.continous_player, args={})
        thread.daemon = True
        thread.start()

    def continous_player(self):
        while(True):
            time.sleep(2)
            if(self.check_togglerLock()):
                continue
            if (not self.is_playing and not self.check_lock()):
                self.toggle_lock(True)
                if(self._new):
                    self._new = False
                    self.index = 0
                    self.play_at_index(0)
                else:
                    _next = self.get_next_index()
                    if(math.isnan(_next)):
                        self.stop()
                    else:
                        self.play_at_index(int(_next))
                self._song_changed = True

    def play_next(self):
        self.stop()
        _next_index = self.get_next_index()
        if(not _next_index):
            return False
        self.play_at_index(_next_index)

    def play_prev(self):
        self.stop()
        _prev_index = self.get_prev_index()
        if(math.isnan(_prev_index)):
            # print("nothing previous here")
            return False
        self.play_at_index(_prev_index)

    @property
    def current_song(self):
        return self._current_song

    @current_song.setter
    def current_song(self, value):
        self._current_song = value

    def check_togglerLock(self):
        self._lock_mutex.acquire()
        value = self._togglerLock
        self._lock_mutex.release()
        return value

    def toggle_togglerLock(self, value):
        self._lock_mutex.acquire()
        self._togglerLock = value
        self._lock_mutex.release()

    def toggle_playing(self):
        if (self.player.pause):
            self.toggle_togglerLock(False)
            self.player.pause = False
        else:
            self.toggle_togglerLock(True)
            self.player.pause = True

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, volume):
        volume = max(min(volume, 100), 0)
        self._volume = volume
        self.player['volume'] = volume

    def volume_up(self, amount=10):
        volume = self.volume + amount
        self.volume = volume
        return True

    def volume_down(self, amount=10):
        volume = self.volume - amount
        self.volume = volume
        return True
