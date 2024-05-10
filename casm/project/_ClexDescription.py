from .json_io import pretty_json


class ClexDescription:
    """Settings for a cluster expansion

    Attributes
    ----------

      name: str
        Cluster expansion name

      property: str
        Name of the property being cluster expanded

      calctype: str
        Calctype name

      ref: str
        Reference state name

      bset: str
        Basis set

      eci: str
        ECI set name

    """

    def __init__(
        self,
        name: str,
        property: str,
        calctype: str,
        ref: str,
        bset: str,
        eci: str,
    ):
        self.name = name
        self.property = property
        self.calctype = calctype
        self.ref = ref
        self.bset = bset
        self.eci = eci

    @staticmethod
    def from_dict(data):
        return ClexDescription(
            name=data.get("name"),
            property=data.get("property"),
            calctype=data.get("calctype"),
            ref=data.get("ref"),
            bset=data.get("bset"),
            eci=data.get("eci"),
        )

    def to_dict(self):
        return {
            "bset": self.bset,
            "calctype": self.calctype,
            "eci": self.eci,
            "name": self.name,
            "property": self.property,
            "ref": self.ref,
        }

    def __str__(self):
        return pretty_json(self.to_dict())
