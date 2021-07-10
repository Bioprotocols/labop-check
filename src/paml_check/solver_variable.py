_SOLVER_VARIABLES_PROP = 'solver_variables'

class SolverVariableConstants:
    DURATION_VARIABLE = 'duration'
    START_TIME_VARIABLE = 'start'
    END_TIME_VARIABLE = 'end'

class SolverVariable:
    def __init__(self, prefix, ref):
        self.ref = ref
        self.prefix = prefix
        self.name = f"{prefix}:{ref.identity}"
        self.value = None
        
class SolverVariableDictionary(dict):
    @property
    def start(self):
        return self[SolverVariableConstants.START_TIME_VARIABLE]

    @property
    def end(self):
        return self[SolverVariableConstants.END_TIME_VARIABLE]

    @property
    def duration(self):
        return self[SolverVariableConstants.DURATION_VARIABLE]

def ensure_solver_variables(obj):
    if not hasattr(obj, _SOLVER_VARIABLES_PROP):
        setattr(obj, _SOLVER_VARIABLES_PROP, SolverVariableDictionary())

def get_solver_variables(obj):
    return getattr(obj, _SOLVER_VARIABLES_PROP)

def define_solver_variable(name, obj):
    ensure_solver_variables(obj)
    variables = get_solver_variables(obj)
    var = SolverVariable(name, obj)
    variables[name] = var
    return var


def debug_solver_variables(obj):
    print(f"  {obj.identity}")
    vs = get_solver_variables(obj)
    for key, value in vs.items():
        print(f"    {key} = {value.value}")