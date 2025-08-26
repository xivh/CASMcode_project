from typing import Optional

from casm.tools.shared.json_io import pretty_json


class ClexDescription:
    """Settings for a cluster expansion

    This holds identifiers for data used in a cluster expansion, as a shortcut for
    collecting and saving data.
    """

    def __init__(
        self,
        name: str,
        property: str,
        calctype: Optional[str] = None,
        ref: Optional[str] = None,
        bset: Optional[str] = None,
        fit_id: Optional[str] = None,
        fit_index: Optional[int] = None,
        eci: Optional[str] = None,
    ):
        self.name = name
        """str: Cluster expansion name"""

        self.property = property
        """str: Cluster expansion name"""

        self.calctype = calctype
        """Optional[str]: Calctype name"""

        self.ref = ref
        """Optional[str]: Reference state name"""

        self.bset = bset
        """Optional[str]: Basis set id"""

        self.fit_id = fit_id
        """Optional[str]: Fit id"""

        self.fit_index = fit_index
        """Optional[int]: Fit index, if applicable.
        
        Use for fitting methods that result in multiple sets of coefficients, such as
        a distribution. 
        """

        self.eci = eci
        """Optional[str]: ECI set name
        
        .. deprecated:: 2.0a2
        
            Use :attr:`fit_id` and :attr:`fit_index` instead.
        
        """

    @staticmethod
    def from_dict(data):
        return ClexDescription(
            name=data.get("name"),
            property=data.get("property"),
            calctype=data.get("calctype"),
            ref=data.get("ref"),
            bset=data.get("bset"),
            fit_id=data.get("fit_id"),
            fit_index=data.get("fit_index"),
            eci=data.get("eci"),
        )

    def to_dict(self):
        return {
            "bset": self.bset,
            "calctype": self.calctype,
            "eci": self.eci,
            "fit_id": self.fit_id,
            "fit_index": self.fit_index,
            "name": self.name,
            "property": self.property,
            "ref": self.ref,
        }

    def __str__(self):
        return pretty_json(self.to_dict())
