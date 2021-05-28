import os
import sbol3

from paml_check.activity_graph import ActivityGraph
import paml_check.paml_check as pc

def test_generate_constraints():
    paml_file = os.path.join(os.getcwd(), 'resources/paml', 'igem_ludox_draft.ttl')
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
