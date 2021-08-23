import os

import paml_check.paml_check as pc
import sbol3
from paml_check.activity_graph import ActivityGraph
import tempfile
from paml_check.schedule import Schedule


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
    schedule, graph = pc.check_doc(get_doc_from_file(paml_file))
    assert schedule
    #schedule.plot(filename='igem_ludox_time_draft_schedule.pdf')
    #dot = graph.to_dot()
    #dot.render('igem_ludox_time_draft.gv')


def test_generate_untimed_constraints():
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', 'igem_ludox_draft.ttl')
    schedule, graph = pc.check_doc(get_doc_from_file(paml_file))
    assert schedule

def test_activity_graph():
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', 'igem_ludox_time_draft.ttl')
    doc = get_doc_from_file(paml_file)
    graph = ActivityGraph(doc)
    formula = graph.generate_constraints()
    result = pc.check(formula)
    graph.print_debug()
    graph.print_variables(result)
    assert result