from circleguard.replay import Replay
class Result():
    def __init__(self, replay1: Replay, replay2: Replay, similarity: int, ischeat: bool, later_name: str):
        self.replay1: Replay = replay1
        self.replay2: Replay = replay2
        self.similiarity: int = similarity
        self.ischeat: bool = ischeat
        self.later_name: str = later_name
