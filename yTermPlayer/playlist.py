import pafy


class Video:
    pass


class Playlist:
    def __init__(self, url):
        self.url = url
        self._playlist = pafy.get_playlist(url)

    def __bool__(self):
        return (self.queue_len != 0)

    @property
    def queue_len(self):
        return len(self._playlist.get("items", tuple()))

    @property
    def title(self):
        return self._playlist.get("title")
