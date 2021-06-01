import os
import sbol3
import paml

from paml_check.activity_graph import ActivityGraph
import paml_check.paml_check as pc

paml_spec = "https://raw.githubusercontent.com/SD2E/paml/time/paml/paml.ttl"

def generate_and_test_constraints(paml_file):
    doc = sbol3.Document()
    doc.read(paml_file, 'ttl')
    graph = ActivityGraph(doc)
    graph.print_debug()

    formula = graph.generate_constraints()
    result = pc.check(formula)
    if result:
        print(result)
        print("SAT")
    else:
        print("UNSAT")
    assert result


def test_generate_timed_constraints():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_time_draft.ttl')
    generate_and_test_constraints(paml_file)


def test_generate_untimed_constraints():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_draft.ttl')
    generate_and_test_constraints(paml_file)