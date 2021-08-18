
import pint
import tyto

OM = "om-2.0"

UNIT_REGISTRY = pint.UnitRegistry()
Quantity = UNIT_REGISTRY.Quantity

def convert_quantity(value, from_unit, to_unit):
    return Quantity(value, from_unit).to(to_unit).magnitude

def om_convert(value, from_unit, to_unit):
    return convert_quantity(value, tyto.OM.get_term_by_uri(from_unit), tyto.OM.get_term_by_uri(to_unit))
