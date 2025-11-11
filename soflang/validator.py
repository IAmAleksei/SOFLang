from typing import Dict, List, Optional, Tuple, Union
from soflang.analyzer import (
    Function, Variable, Type,
    AnalysisError, UndefinedVariableError, UndefinedFunctionError,
    TypeMismatchError, ArgumentCountError,
    Statement, VariableDeclaration, Assignment,
    IfExpression, WhileExpression,
    Atom, GeneralExpr, UnaryExpr, IntegerLiteral, IdentifierExpr, FunctionCall, ArrayIndex
)


class MilliValidator:
    """Validates Function objects for correctness."""
    
    def __init__(self):
        self.functions: Dict[str, Function] = {}
        self.errors: List[AnalysisError] = []
    
    def validate(self, functions: List[Function]) -> List[AnalysisError]:
        """
        Validate a list of Function objects.
        
        Args:
            functions: List of Function objects from analyzer
            
        Returns:
            List of analysis errors (empty if no errors)
        """
        self.errors = []
        self.functions = {func.name: func for func in functions}
        
        # Analyze function bodies
        for func in functions:
            self._analyze_function_body(func)
        
        return self.errors
    
    def _analyze_function_body(self, func: Function):
        """Analyze a function body."""
        variables: Dict[str, Variable] = {}
        
        # Add parameters to variables
        for param in func.parameters:
            variables[param.name] = param
        
        # Add 'result' variable (automatically available with function's return type)
        result_var = Variable('result', func.return_type, func.return_array_size)
        variables['result'] = result_var
        
        # Process body statements
        body = func.body or []
        self._process_statements(body, variables, func)
    
    def _process_statements(self, statements: List[Statement], variables: Dict[str, Variable], func: Function):
        """Process a list of statements."""
        for stmt in statements:
            if isinstance(stmt, VariableDeclaration):
                var = stmt.variable
                # Check if trying to declare 'result' variable
                if var.name == 'result':
                    self.errors.append(TypeMismatchError(
                        "cannot declare", "result",
                        f"variable 'result' cannot be declared in function {func.name}"
                    ))
                else:
                    variables[var.name] = var
            elif isinstance(stmt, Assignment):
                self._analyze_assignment(stmt, variables, func)
            elif isinstance(stmt, IfExpression):
                self._analyze_if_expr(stmt, variables, func)
            elif isinstance(stmt, WhileExpression):
                self._analyze_while_expr(stmt, variables, func)
    
    def _analyze_assignment(self, assignment: Assignment, 
                           variables: Dict[str, Variable], func: Function):
        """Analyze an assignment statement."""
        target = assignment.target
        value = assignment.value
        
        if isinstance(target, str):
            self._analyze_simple_assignment(target, value, variables, func)
        elif isinstance(target, ArrayIndex):
            self._analyze_array_assignment(target, value, variables, func)
    
    def _analyze_simple_assignment(self, var_name: str, value: Union[Atom, GeneralExpr, UnaryExpr],
                                  variables: Dict[str, Variable], func: Function):
        """Analyze a simple assignment."""
        # Check if variable exists (except for 'result' which is always available)
        if var_name != 'result' and var_name not in variables:
            self.errors.append(UndefinedVariableError(var_name, f"in function {func.name}"))
            return
        
        var = variables.get(var_name)
        if var is None:
            return
        
        # Analyze the expression
        expr_type, _ = self._analyze_expression(value, variables, func.name)
        if expr_type is not None:
            if var.type != expr_type:
                self.errors.append(TypeMismatchError(
                    var.type.value, expr_type.value,
                    f"assignment to {var_name} in function {func.name}"
                ))
        
        # Check if this is an assignment to 'result' - verify type matches function return type
        if var_name == 'result':
            self._check_result_assignment_type(value, variables, func)
    
    def _analyze_array_assignment(self, target: ArrayIndex, value: Union[Atom, GeneralExpr, UnaryExpr],
                                  variables: Dict[str, Variable], func: Function):
        """Analyze an array assignment."""
        var_name = target.var_name
        
        if var_name not in variables:
            self.errors.append(UndefinedVariableError(var_name, f"in function {func.name}"))
            return
        
        var = variables[var_name]
        if var.type != Type.ARRAY:
            self.errors.append(TypeMismatchError(
                "array", var.type.value,
                f"array assignment to non-array variable {var_name} in function {func.name}"
            ))
            return
        
        # Analyze index
        self._analyze_index(target.index, var_name, variables, func.name)
        
        # Analyze value - array elements must be NUM
        value_type, _ = self._analyze_expression(value, variables, func.name)
        if value_type is not None and value_type != Type.NUM:
            self.errors.append(TypeMismatchError(
                "num", value_type.value if value_type else "unknown",
                f"array element assignment must be num type for {var_name} in function {func.name}"
            ))
    
    def _analyze_index(self, index: Union[int, str], var_name: str, 
                      variables: Dict[str, Variable], func_name: str):
        """Analyze array index."""
        if isinstance(index, int):
            if index < 0:
                self.errors.append(TypeMismatchError(
                    "num", "negative",
                    f"array index must be non-negative integer for {var_name} in function {func_name}"
                ))
        elif isinstance(index, str):
            if index not in variables:
                self.errors.append(UndefinedVariableError(index, f"as array index for {var_name} in function {func_name}"))
            else:
                index_var = variables[index]
                if index_var.type != Type.NUM:
                    self.errors.append(TypeMismatchError(
                        "num", index_var.type.value,
                        f"array index must be num variable, got {index_var.type.value} for {var_name} in function {func_name}"
                    ))
    
    def _analyze_if_expr(self, if_expr: IfExpression, variables: Dict[str, Variable], func: Function):
        """Analyze an if expression."""
        condition = if_expr.condition
        cond_type, _ = self._analyze_expression(condition, variables, func.name)
        if cond_type is not None and cond_type != Type.NUM:
            self.errors.append(TypeMismatchError(
                "num", cond_type.value,
                f"if condition in function {func.name}"
            ))
        
        body_vars = variables.copy()
        self._process_statements(if_expr.body, body_vars, func)
    
    def _analyze_while_expr(self, while_expr: WhileExpression, variables: Dict[str, Variable], func: Function):
        """Analyze a while expression."""
        condition = while_expr.condition
        cond_type, _ = self._analyze_expression(condition, variables, func.name)
        if cond_type is not None and cond_type != Type.NUM:
            self.errors.append(TypeMismatchError(
                "num", cond_type.value,
                f"while condition in function {func.name}"
            ))
        
        body_vars = variables.copy()
        self._process_statements(while_expr.body, body_vars, func)
    
    def _check_result_assignment_type(self, expr: Union[Atom, GeneralExpr, UnaryExpr], 
                                     variables: Dict[str, Variable], func: Function):
        """Check if assignment to result has correct type."""
        return_type, return_array_size = self._analyze_expression(expr, variables, func.name)
        
        if return_type is not None:
            if return_type != func.return_type:
                self.errors.append(TypeMismatchError(
                    func.return_type.value, return_type.value,
                    f"return type mismatch in function {func.name}"
                ))
            elif return_type == Type.ARRAY and return_array_size != func.return_array_size:
                self.errors.append(TypeMismatchError(
                    f"{func.return_type.value}*{func.return_array_size}", 
                    f"{return_type.value}*{return_array_size}",
                    f"return array size mismatch in function {func.name}"
                ))
    
    def _analyze_expression(self, expr: Union[Atom, GeneralExpr, UnaryExpr], 
                           variables: Dict[str, Variable], func_name: str) -> Tuple[Optional[Type], Optional[int]]:
        """Analyze an expression and return its type."""
        if isinstance(expr, GeneralExpr):
            # Binary operations always return NUM
            # Validate left and right are valid
            self._analyze_expression(expr.left, variables, func_name)
            self._analyze_expression(expr.right, variables, func_name)
            return Type.NUM, None
        elif isinstance(expr, UnaryExpr):
            operand_type, _ = self._analyze_expression(expr.operand, variables, func_name)
            if operand_type is not None and operand_type != Type.NUM:
                self.errors.append(TypeMismatchError(
                    "num", operand_type.value,
                    f"unary {expr.op} expression in function {func_name}"
                ))
            return Type.NUM, None
        
        # Otherwise it's an ATOM
        return self._analyze_atom(expr, variables, func_name)
    
    def _analyze_atom(self, atom: Atom, variables: Dict[str, Variable], 
                     func_name: str) -> Tuple[Optional[Type], Optional[int]]:
        """Analyze an ATOM and return its type."""
        value = atom.value
        
        if isinstance(value, IntegerLiteral):
            return Type.NUM, None
        
        elif isinstance(value, IdentifierExpr):
            var_name = value.name
            if var_name in variables:
                var = variables[var_name]
                return var.type, var.array_size
            # Check if it's a function name
            if var_name in self.functions:
                func = self.functions[var_name]
                return func.return_type, func.return_array_size
            self.errors.append(UndefinedVariableError(var_name, f"in function {func_name}"))
            return None, None
        
        elif isinstance(value, FunctionCall):
            return self._analyze_function_call(value, variables, func_name)
        
        elif isinstance(value, ArrayIndex):
            return self._analyze_array_index_expr(value, variables, func_name)
        
        return None, None
    
    def _analyze_function_call(self, func_call: FunctionCall, variables: Dict[str, Variable], 
                              func_name: str) -> Tuple[Optional[Type], Optional[int]]:
        """Analyze a function call."""
        call_name = func_call.name
        
        if call_name not in self.functions:
            self.errors.append(UndefinedFunctionError(call_name, f"in function {func_name}"))
            return None, None
        
        func_def = self.functions[call_name]
        
        # Check argument count
        param_count = len(func_call.parameters)
        if param_count != len(func_def.parameters):
            self.errors.append(ArgumentCountError(call_name, len(func_def.parameters), param_count))
        
        # Check that all parameters are valid variables
        for param_name in func_call.parameters:
            if param_name not in variables:
                self.errors.append(UndefinedVariableError(
                    param_name, f"as argument to {call_name} in function {func_name}"
                ))
        
        return func_def.return_type, func_def.return_array_size
    
    def _analyze_array_index_expr(self, array_index: ArrayIndex, variables: Dict[str, Variable], 
                                  func_name: str) -> Tuple[Optional[Type], Optional[int]]:
        """Analyze an array index expression."""
        var_name = array_index.var_name
        
        if var_name not in variables:
            self.errors.append(UndefinedVariableError(var_name, f"in function {func_name}"))
            return None, None
        
        var = variables[var_name]
        if var.type != Type.ARRAY:
            self.errors.append(TypeMismatchError(
                "array", var.type.value,
                f"array indexing on non-array variable {var_name} in function {func_name}"
            ))
            return None, None
        
        # Analyze index
        self._analyze_index(array_index.index, var_name, variables, func_name)
        
        # Array indexing returns NUM
        return Type.NUM, None
