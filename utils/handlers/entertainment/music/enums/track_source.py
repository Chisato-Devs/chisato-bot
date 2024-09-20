from enum import Enum


class TrackSource(Enum):
    Spotify = "spsearch:"
    YandexMusic = "ymsearch:"
    VkMusic = "vksearch:"
    SoundCloud = "scsearch:"
    AppleMusic = "amsearch:"
    Deezer = "dzsearch:"
