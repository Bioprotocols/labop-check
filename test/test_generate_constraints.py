import os
import sbol3
import paml
import operator

from paml_check.activity_graph import ActivityGraph
import paml_check.paml_check as pc

paml_spec = "https://raw.githubusercontent.com/SD2E/paml/time/paml/paml.ttl"
        

# junk code to print out the results in a slightly easier to read output
def print_debug(result, graph):
    def make_entry(variable, activity, uri, value, prefix = ""):
        v = value
        if activity.start.identity == variable.identity:
            s = f"{prefix}S {activity.identity} : {value}"
        elif activity.end.identity == variable.identity:
            s = f"{prefix}E {activity.identity} : {value}"
        elif activity.duration.identity == variable.identity:
            s = f"{prefix}D {uri} : {value}"
        else:
            s = f"{prefix}ERR {uri} : {value}"
        return (v, s)
    nodes = []
    protcols = []
    for (node, value) in result:
        uri = node.symbol_name()
        v = (float)(value.constant_value())
        if uri in graph.nodes:
            variable = graph.nodes[uri]
            activity = variable.get_parent()
            nodes.append(make_entry(variable, activity, uri, v))
        else:
            variable = graph.doc.find(uri)
            activity = variable.get_parent()
            protcols.append(make_entry(variable, activity, uri, v, "PROTOCOL "))

    print("--- Nodes ---")
    for k in sorted(nodes, key=operator.itemgetter(0)):
        print(k[1])
    print("--- Protocol ---")
    for k in sorted(protcols, key=operator.itemgetter(0)):
        print(k[1])


def generate_and_test_constraints(paml_file):
    doc = sbol3.Document()
    doc.read(paml_file, 'ttl')
    graph = ActivityGraph(doc)

    formula = graph.generate_constraints()
    result = pc.check(formula)
    if result:
        graph.add_result(doc, result)
        graph.compute_durations(doc)
        graph.print_debug()
        print_debug(result, graph)
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