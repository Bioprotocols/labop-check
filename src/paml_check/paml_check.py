import pysmt.shortcuts
from pysmt.smtlib.parser import SmtLibParser
from pysmt.smtlib.solver import SmtLibSolver
from pysmt import environment
from pysmt import logics

def check_smtlib(smtlib_file):
    parser = SmtLibParser()
    with open(smtlib_file, "r") as f:
        script = parser.get_script(f)
        solver = SmtLibSolver([], environment.get_env(), logics.QF_LIA)
        script.evaluate(solver=solver)

        solver.get_model(script)
    return True


def check(formula):
    return pysmt.shortcuts.get_model(formula)


