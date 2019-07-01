import pafy


def structure_time(hours, minutes, seconds, *args):
    if hours == 0:
        formatter = "{:0>2d}:{:0>2d}"
        return formatter.format(minutes, seconds)
    else:
        formatter = "{:0>2d}:{:0>2d}:{:0>2d}"
        return formatter.format(hours, minutes, seconds)


class Video:
    def __init__(self, pafy_obj):
        self.title = pafy_obj.title
        self.author = pafy_obj.author
        time = str(pafy_obj.duration).split(":")
        self.duration = structure_time(*time)
        self.url = pafy_obj.getbestaudio().url


class Playlist:
    def __init__(self, url):
        self.url = url
        self._playlist = pafy.get_playlist(url)
        self.videos = [Video(pafy_obj) for pafy_obj in self._playlist["items"]]

    def __bool__(self):
        return (self.queue_len != 0)

    def __len__(self):
        return self.queue_len

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError("Playlist indices must be integers")
        if index > self.queue_len:
            raise IndexError("Playlist index out of range")
        return self.videos[index]

    @property
    def queue_len(self):
        return len(self._playlist.get("items", tuple()))

    @property
    def title(self):
        return self._playlist.get("title")
