class Timeline():
    def __init__(self, model, timepoint_vars, happenings):
        self.happening_timepoints = {}
        self.time_variables = {}

        for var, value in result:
            if value.is_real_constant():
                if str(value) in self.time_variables:
                    if var in happenings:
                        self.time_variables[str(value)]["happenings"] = { "time" : value.constant_value(), "timepoints" : []}
        for var, value in result:
            if value.is_real_constant():
                if str(var) in timepoint_vars:
                    self.happening_timepoints["var"] = { "time" : value.constant_value(), "timepoints" : []}