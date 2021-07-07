import paml_check.convert_constraints as pcc
import pysmt
import pysmt.shortcuts
import uml

def convert_time_constraint(converter: 'pcc.ConstraintConverter',
                            constraint: uml.TimeConstraint):
    """
    Convert a uml.TimeConstraint into the pysmt equivalent
    """
    # TODO
    return pysmt.shortcuts.TRUE()