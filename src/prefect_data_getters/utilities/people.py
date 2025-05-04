class person:
    def __init__(self, first, last):
        self.first = first
        self.last = last
    def __str__(self):
        return f"{self.first} {self.last}"


HYPERION = [
    person("Adam", "Albaum"),
    person("Eynner","Herrera"),
    person("Suzannah", "Osekowsky"),
    person("Oscar", "Balandran"),
    person("Mike", "Beenen"),
    person("Chatis", "Santos"),
    person("Burt", "Bielicki"),
    person("Manasvi", "Patel"),
    person("Pablo", "Gallego"),
]

CLIENT_ENGAGEMENT = HYPERION[4:6]
DATA_ACQUISITION = HYPERION[0:4]
ONBOARDING = HYPERION[6:]