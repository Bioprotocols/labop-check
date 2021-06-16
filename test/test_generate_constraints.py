import os
import sbol3

import paml_check.paml_check as pc

paml_spec = "https://raw.githubusercontent.com/SD2E/paml/time/paml/paml.ttl"

def get_doc_from_file(paml_file):
    doc = sbol3.Document()
    doc.read(paml_file, 'ttl')
    return doc


def test_minimize_duration():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_time_draft.ttl')
    duration = pc.get_minimum_duration(get_doc_from_file(paml_file))
    assert duration


def test_generate_timed_constraints():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_time_draft.ttl')
    result = pc.check_doc(get_doc_from_file(paml_file))
    assert result


def test_generate_untimed_constraints():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_draft.ttl')
    result = pc.check_doc(get_doc_from_file(paml_file))
    assert result