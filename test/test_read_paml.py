import os
import sbol3
import labop


def test_read_labop():
    labop_file = os.path.join(
        os.getcwd(), "test/resources/labop", "igem_ludox_draft.ttl"
    )
    doc = sbol3.Document()
    doc.read(labop_file, "ttl")
    protocols = doc.find_all(lambda obj: isinstance(obj, labop.Protocol))
    assert protocols
