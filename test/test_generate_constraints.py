from paml_check.activity_graph import ActivityGraph
from paml_check.schedule import Schedule
import os
import sbol3
import tempfile
import paml
import paml_check.paml_check as pc
import pytest

timed_targets = [
    'igem_ludox_time_draft.ttl',
    'igem_ludox_dual_time_draft.ttl'
]
untimed_targets = [
    'igem_ludox_draft.ttl',
    'igem_ludox_dual_draft.ttl'
]
all_targets = timed_targets + untimed_targets


def get_doc_from_file(paml_file):
    doc = sbol3.Document()
    sbol3.set_namespace('https://bbn.com/scratch/')
    doc.read(paml_file, 'turtle')
    return doc


def get_doc_for_target(target):
    paml_file = os.path.join(os.getcwd(), 'test/resources/paml', target)
    return get_doc_from_file(paml_file)


@pytest.mark.parametrize("target", timed_targets)
def test_minimize_duration(target):
    duration = pc.get_minimum_duration(get_doc_for_target(target))
    assert duration


@pytest.mark.parametrize("target", timed_targets)
def test_generate_timed_constraints(target):
    schedule, graph = pc.check_doc(get_doc_for_target(target))
    assert schedule
    schedule.plot(filename=f'{target}_schedule.pdf')
    dot = graph.to_dot()
    dot.render(f'{target}.gv')


@pytest.mark.parametrize("target", untimed_targets)
def test_generate_untimed_constraints(target):
    schedule, graph = pc.check_doc(get_doc_for_target(target))
    assert schedule


@pytest.mark.parametrize("target", all_targets)
def test_activity_graph(target):
    doc = get_doc_for_target(target)
    graph = ActivityGraph(doc)
    formula = graph.generate_constraints()
    result = pc.check(formula)
    graph.print_debug()
    graph.print_variables(result)
    assert result
