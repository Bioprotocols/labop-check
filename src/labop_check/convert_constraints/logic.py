import paml_check.convert_constraints as pcc
import paml_time as pamlt
import pysmt
import pysmt.shortcuts
import uml

def convert_and_constraint(converter: 'pcc.ConstraintConverter',
                           constraint: pamlt.AndConstraint):
    """
    Convert a paml_time.AndConstraint into the pysmt equivalent
    """
    elements = [ ce.property_value if isinstance(ce, uml.OrderedPropertyValue) else ce
                for ce in constraint.constrained_elements ]
    clauses = [ converter.convert_constraint(ce)
                for ce in elements ]
    return pysmt.shortcuts.And(clauses)

def convert_or_constraint(converter: 'pcc.ConstraintConverter',
                          constraint: pamlt.OrConstraint):
    """
    Convert a paml_time.OrConstraint into the pysmt equivalent
    """
    clauses = [ converter.convert_constraint(ce)
                for ce in constraint.constrained_elements ]
    return pysmt.shortcuts.Or(clauses)

def convert_xor_constraint(converter: 'pcc.ConstraintConverter',
                           constraint: pamlt.XorConstraint):
    """
    Convert a paml_time.XorConstraint into the pysmt equivalent
    """
    clauses = [ converter.convert_constraint(ce)
                for ce in constraint.constrained_elements ]
    return pysmt.shortcuts.ExactlyOne(clauses)

def convert_not_constraint(converter: 'pcc.ConstraintConverter',
                           constraint: pamlt.Not):
    """
    Convert a paml_time.NotConstraint into the pysmt equivalent
    """
    clause = converter.convert_constraint(constraint.constrained_elements)
    return pysmt.shortcuts.Not(clause)