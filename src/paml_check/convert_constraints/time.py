import paml_check.convert_constraints as pcc
import pysmt
import pysmt.shortcuts
import uml
from paml_check.constraints import unary_temporal_constaint

class TimeConstraintException(Exception):
    pass

def convert_time_constraint(converter: 'pcc.ConstraintConverter',
                            constraint: uml.TimeConstraint):
    """
    Convert a uml.TimeConstraint into the pysmt equivalent
    """
    tp = get_timepoint(converter, constraint)

    # collect min and max duration
    time_interval = constraint.specification
    min_duration = converter.time_measure_to_seconds(get_min_duration(time_interval))
    max_duration = converter.time_measure_to_seconds(get_max_duration(time_interval))

    clause = unary_temporal_constaint(
        pysmt.shortcuts.Symbol(tp.name, pysmt.shortcuts.REAL),
        [[min_duration, max_duration]])
    return clause

def get_min_duration(time_interval: uml.TimeInterval):
    """
    Extract the TimeMeasure object for the min duration of a TimeInterval
    """
    try:
        return time_interval.min.expr.expr
    except Exception as e:
        raise TimeConstraintException(f"Failed to read min duration from {time_interval.identity}: {e}")


def get_max_duration(time_interval: uml.TimeInterval):
    """
    Extract the TimeMeasure object for the max duration of a TimeInterval
    """
    try:
        return time_interval.max.expr.expr
    except Exception as e:
        raise TimeConstraintException(f"Failed to read max duration from {time_interval.identity}: {e}")



def get_timepoint(converter: 'pcc.ConstraintConverter', constraint: uml.TimeConstraint):
    ce = constraint.constrained_elements
    num_elements = len(ce)
    if 1 != num_elements:
        # TODO better error messaging
        raise TimeConstraintException("Expected a constrained_element count of 1")

    first = ce[0]
    first_vars = converter.time_constraints.identity_to_time_variables(first.property_value)

    start = first_vars.start if constraint.firstEvent else first_vars.end
    return start