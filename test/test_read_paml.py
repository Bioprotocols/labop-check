import os
import sbol3
import paml

def test_read_paml():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_draft.ttl')
    doc = sbol3.Document()
    doc.read(paml_file, 'ttl')
    protocols = doc.find_all(lambda obj: isinstance(obj, paml.Protocol))
    for protocol in protocols:
        for activity in protocol.activities:
            print(f"Found activity {activity}")
    assert(protocols)
