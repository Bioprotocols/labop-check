import os
import sbol3
import paml

import paml_check.paml_check as pc
from paml_check.activity_graph import ActivityGraph

def get_doc_from_file(paml_file):
    doc = sbol3.Document()
    sbol3.set_namespace('https://bbn.com/scratch/')
    doc.read(paml_file, 'turtle')
    return doc


def test_minimize_duration():
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', 'igem_ludox_time_draft.ttl')
    duration = pc.get_minimum_duration(get_doc_from_file(paml_file))
    assert duration


def test_generate_timed_constraints():
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', 'igem_ludox_time_draft.ttl')
    result = pc.check_doc(get_doc_from_file(paml_file))
    assert result


def test_generate_untimed_constraints():
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', 'igem_ludox_draft.ttl')
    result = pc.check_doc(get_doc_from_file(paml_file))
    assert result

def test_activity_graph():
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', 'igem_ludox_time_draft.ttl')
    doc = get_doc_from_file(paml_file)
    graph = ActivityGraph(doc)
    formula = graph.generate_constraints()
    result = pc.check(formula)
    graph.print_debug()
    graph.print_variables(result)
    assert result