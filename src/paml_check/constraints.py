import pysmt

def binary_temporal_constraint(t1, disjunctive_distance, t2):
    difference = pysmt.shortcuts.Minus(t2, t1)
    constraint = pysmt.shortcuts.Or([
        pysmt.shortcuts.And(pysmt.shortcuts.GE(difference, pysmt.shortcuts.Real(dd[0])),
                            pysmt.shortcuts.LE(difference, pysmt.shortcuts.Real(dd[1])))
        for dd in disjunctive_distance
        ])
    return constraint

def unary_temporal_constaint(t, disjunctive_distance):
    constraint = pysmt.shortcuts.Or([
        pysmt.shortcuts.And(pysmt.shortcuts.GE(t, pysmt.shortcuts.Real(dd[0])),
                            pysmt.shortcuts.LE(t, pysmt.shortcuts.Real(dd[1])))
        for dd in disjunctive_distance
        ])
    return constraint


def join_constraint(t_join, joined_times):
    constraint = pysmt.shortcuts.Or([
        pysmt.shortcuts.Equals(t_join, t_j)
        for t_j in joined_times
    ])
    return constraint

def time_points_happen_once_constraint(timepoint_vars, happenings):
    """
    Each time point is equal to at least one happening
    :param timepoint_vars:
    :param happenings:
    :return: constraint
    """
    constraint = pysmt.shortcuts.And([
        pysmt.shortcuts.Or([
            pysmt.shortcuts.Equals(t, h)
            for h in happenings
        ])
        for _, t in timepoint_vars.items()
    ])
    return constraint