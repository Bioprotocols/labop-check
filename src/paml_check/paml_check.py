"""
Check a protocol for various properties, such as consistency
"""
import pysmt.shortcuts

from paml_check.activity_graph import ActivityGraph

def check_doc(doc):
    """
    Check a paml document for temporal consistency
    :param doc:
    :return:
    """
    graph = ActivityGraph(doc)
    graph.print_debug()

    formula = graph.generate_constraints()
    result = check(formula)
    doc = graph.add_result(doc, result)
    doc = graph.compute_durations(doc)
    return doc

def check(formula):
    """
    Check whether a formula is satisfiable and return the model if so
    :param formula:
    :return:
    """
    return pysmt.shortcuts.get_model(formula)
