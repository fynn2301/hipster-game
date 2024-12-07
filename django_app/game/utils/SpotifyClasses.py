class Song:
    def __init__(self, id, title, artists, year) -> None:
        self.id = id
        self.title = title
        self.artists = artists
        self.year = year
    id: str
    title: str
    artists: list[str]
    year: str
