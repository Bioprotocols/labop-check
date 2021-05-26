"""
Check a protocol for various properties, such as consistency
"""
import pysmt.shortcuts


def check(formula):
    """
    Check whether a formula is satisfiable and return the model if so
    :param formula:
    :return:
    """
    return pysmt.shortcuts.get_model(formula)
