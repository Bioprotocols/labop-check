"""
Test a hand-coded temporal problem
"""
import pysmt.shortcuts
import paml_check.paml_check as pc
from paml_check.constraints import binary_temporal_constraint, join_constraint, \
    unary_temporal_constaint


def test_ludox_check_direct():
    """
    Hand coded temporal problem that is satisfiable
    :return:
    """
    timepoints = [
        "t_0",
        "t_F",
        "t_P1_s",
        "t_P2_s",
        "t_P1_e",
        "t_P2_e",
        "t_M",
        "t_MA_s",
        "t_MA_e",
        "t_N"
    ]
    t_inf = 10000.0
    t_epsilon = 0.0001
    # num_happenings = 10

    timepoint_vars = {t: pysmt.shortcuts.Symbol(t, pysmt.shortcuts.REAL)
                      for t in timepoints}

    timepoint_var_domains = [pysmt.shortcuts.And(pysmt.shortcuts.GE(t, pysmt.shortcuts.Real(0.0)),
                                                 pysmt.shortcuts.LE(t, pysmt.shortcuts.Real(t_inf)))
                             for _, t in timepoint_vars.items()]

    time_constraints = [
        binary_temporal_constraint(timepoint_vars["t_0"], [
                                   [0, 0]], timepoint_vars["t_F"]),
        binary_temporal_constraint(timepoint_vars["t_F"], [
                                   [0, t_inf]], timepoint_vars["t_P1_s"]),
        binary_temporal_constraint(timepoint_vars["t_F"], [
                                   [0, t_inf]], timepoint_vars["t_P2_s"]),
        binary_temporal_constraint(timepoint_vars["t_P1_s"], [
                                   [t_epsilon, t_inf]], timepoint_vars["t_P1_e"]),
        binary_temporal_constraint(timepoint_vars["t_P2_s"], [
                                   [t_epsilon, t_inf]], timepoint_vars["t_P2_e"]),
        binary_temporal_constraint(timepoint_vars["t_P1_e"], [
                                   [0, t_inf]], timepoint_vars["t_M"]),
        binary_temporal_constraint(timepoint_vars["t_P2_e"], [
                                   [0, t_inf]], timepoint_vars["t_M"]),
        binary_temporal_constraint(timepoint_vars["t_M"], [
                                   [t_epsilon, t_inf]], timepoint_vars["t_MA_s"]),
        binary_temporal_constraint(timepoint_vars["t_MA_s"], [
                                   [t_epsilon, t_inf]], timepoint_vars["t_MA_e"]),
        binary_temporal_constraint(timepoint_vars["t_MA_e"], [
                                   [0, 0]], timepoint_vars["t_N"]),
    ]

    join_constraints = [
        join_constraint(timepoint_vars["t_M"],
                        [
                            timepoint_vars["t_P2_e"],
                            timepoint_vars["t_P1_e"]
        ])
    ]

    durations = [
        binary_temporal_constraint(timepoint_vars["t_P1_s"], [
                                   [3, 3]], timepoint_vars["t_P1_e"]),
        binary_temporal_constraint(timepoint_vars["t_P2_s"], [
                                   [3, 3]], timepoint_vars["t_P2_e"]),
        binary_temporal_constraint(timepoint_vars["t_MA_s"], [
                                   [10, 10]], timepoint_vars["t_MA_e"]),
        binary_temporal_constraint(timepoint_vars["t_0"], [
                                   [0, 100]], timepoint_vars["t_N"])
    ]

    events = [
        unary_temporal_constaint(timepoint_vars["t_0"], [[1, 3]]),
        unary_temporal_constaint(timepoint_vars["t_N"], [[15, 16]])
    ]

    # happenings = [pysmt.shortcuts.Symbol(
    #    f"h_{i}", pysmt.shortcuts.REAL) for i in range(num_happenings)]

    # happening_timepoint_mappings = time_points_happen_once_constraint(
    #    timepoint_vars, happenings)

    given_constraints = pysmt.shortcuts.And(
        timepoint_var_domains + time_constraints + join_constraints)
    hand_coded_constraints = pysmt.shortcuts.And(durations + events)
    formula = pysmt.shortcuts.And(
        given_constraints,
        hand_coded_constraints,
    #    happening_timepoint_mappings
    )
    result = pc.check(formula)
    if result:
        #timeline = Timeline(result, timepoint_vars, happenings)
        # print(timeline)
        print("SAT")
    else:
        print("UNSAT")

    assert result
