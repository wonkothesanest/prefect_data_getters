class person:
    def __init__(self, first, last):
        self.first = first
        self.last = last
    def __str__(self):
        return f"{self.first} {self.last}"


HYPERION = [
    person("Adam", "Albaum"),
    person("Mauri","Agueda"),
    person("Suzannah", "Osekowsky"),
    person("Mike", "Beenen"),
    person("Chatis", "Santos"),
    person("Burt", "Bielicki"),
    person("Manasvi", "Patel"),
    person("Pablo", "Gallego"),
]

CLIENT_ENGAGEMENT = HYPERION[3:5]
DATA_ACQUISITION = HYPERION[0:3]
ONBOARDING = HYPERION[5:]