from datetime import datetime, timedelta, timezone
import numpy as np


class Time:

    def __init__(self) -> None:
        pass

    def copy(self) -> 'Time':
        return Time().from_datetime(self.time) # deep copy

    def from_str(self, time: str, format: str = "%Y-%m-%d %H:%M:%S") -> 'Time':
        self.time = datetime.strptime(time, format)
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self

    def to_str(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        if self.time.microsecond != 0:
            format += ".%f"
        return self.time.strftime(format)

    def from_datetime(self, time: datetime) -> 'Time':
        self.time = time
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self
    
    def from_unix(self, unix: float) -> 'Time':
        self.time = datetime.utcfromtimestamp(unix)
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self
    
    def to_unix(self) -> float:
        assert self.time.tzinfo == timezone.utc, "Time object is not in UTC"
        return self.time.timestamp()
    
    def difference_in_seconds(time1: 'Time' , time2: 'Time') -> float:
        return (time1.time - time2.time).total_seconds()

    def to_datetime(self) -> datetime:
        self.time = self.time.replace(tzinfo=timezone.utc)
        return self.time

    def add_seconds(self, second: float) -> 'Time':
        self.time = self.time + timedelta(seconds=second)
        return self

    def round_to_nearest_second(self) -> 'Time':
        if self.time.microsecond >= 500000:
            self.time = self.time.replace(microsecond=0) + timedelta(seconds=1)
        else:
            self.time = self.time.replace(microsecond=0)
        return self

    ##Operators:
    def __lt__(self, other):
        return (self.time < other.time)

    def __le__(self, other):
        return(self.time <= other.time)

    def __gt__(self, other):
        return(self.time > other.time)

    def __ge__(self, other):
        return(self.time >= other.time)

    def __eq__(self, other):
        return (self.time == other.time)

    def __ne__(self, other):
        return not(self.__eq__(self, other))

    def __str__(self) -> str:
        return self.to_str()
    
    def __repr__(self) -> str:
        return self.to_str()
    
    def __hash__(self) -> int:
        return hash(self.time)


def utc_to_local(utc, longitude):
    offset = int((longitude + 180) / 15) - 12
    return (utc + offset) % 24


def distance(nodeA, nodeB):
    xA = nodeA.state.x
    yA = nodeA.state.y
    zA = nodeA.state.z
    xB = nodeB.state.x
    yB = nodeB.state.y
    zB = nodeB.state.z

    return np.sqrt((xA - xB) ** 2 + (yA - yB) ** 2 + (zA - zB) ** 2)
