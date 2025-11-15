from typing import Dict, List, Optional, Tuple, Union
from soflang.analyzer import (
    Function, Variable, Class,
    AnalysisError, UndefinedVariableError, UndefinedFunctionError,
    TypeMismatchError, ArgumentCountError,
    Statement, VariableDeclaration, Assignment,
    IfExpression, WhileExpression,
    Atom, GeneralExpr, UnaryExpr, IntegerLiteral, IdentifierExpr, FunctionCall, ArrayIndex,
    FieldAccess, ConstructorCall, Throwable
)


class MilliValidator:
    """Validates Function objects for correctness."""
    
    def __init__(self):
        self.functions: Dict[str, Function] = {}
        self.classes: Dict[str, Class] = {}
        self.errors: List[AnalysisError] = []
    
    def validate(self, functions: List[Function], classes: Optional[Dict[str, Class]] = None) -> List[AnalysisError]:
        """
        Validate a list of Function objects.
        
        Args:
            functions: List of Function objects from analyzer
            classes: Optional dict of Class objects from analyzer
            
        Returns:
            List of analysis errors (empty if no errors)
        """
        self.errors = []
        self.functions = {func.name: func for func in functions}
        self.classes = classes or {}
        
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
        result_var = Variable('result', func.return_class_type, func.return_array_size)
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
            elif isinstance(stmt, Throwable):
                pass
    
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
        expr_class_type, expr_array_size = self._analyze_expression(value, variables, func.name)
        
        if expr_class_type is not None:
            # Check class type compatibility
            if var.class_type != expr_class_type:
                self.errors.append(TypeMismatchError(
                    var.class_type, expr_class_type,
                    f"class type mismatch in assignment to {var_name} in function {func.name}"
                ))
            # Check array size compatibility
            if var.array_size != expr_array_size:
                if var.array_size is not None or expr_array_size is not None:
                    self.errors.append(TypeMismatchError(
                        f"{var.class_type}{'*' + str(var.array_size) if var.array_size else ''}",
                        f"{expr_class_type}{'*' + str(expr_array_size) if expr_array_size else ''}",
                        f"array size mismatch in assignment to {var_name} in function {func.name}"
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
        if var.array_size is None:
            self.errors.append(TypeMismatchError(
                "array", var.class_type,
                f"array assignment to non-array variable {var_name} in function {func.name}"
            ))
            return
        
        # Analyze index
        self._analyze_index(target.index, var_name, variables, func.name)
        
        # Analyze value - array elements must match the array's element type
        value_class_type, value_array_size = self._analyze_expression(value, variables, func.name)
        if value_class_type is not None:
            # For now, we'll check that it's not an array (arrays can't be array elements)
            if value_array_size is not None:
                self.errors.append(TypeMismatchError(
                    var.class_type, f"{value_class_type}*{value_array_size}",
                    f"array element assignment cannot be an array for {var_name} in function {func.name}"
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
                if index_var.class_type != 'Num' or index_var.array_size is not None:
                    self.errors.append(TypeMismatchError(
                        "Num", f"{index_var.class_type}{'*' + str(index_var.array_size) if index_var.array_size else ''}",
                        f"array index must be Num variable, got {index_var.class_type} for {var_name} in function {func_name}"
                    ))
    
    def _analyze_if_expr(self, if_expr: IfExpression, variables: Dict[str, Variable], func: Function):
        """Analyze an if expression."""
        condition = if_expr.condition
        cond_class_type, cond_array_size = self._analyze_expression(condition, variables, func.name)
        if cond_class_type is not None and (cond_class_type != 'Num' or cond_array_size is not None):
            self.errors.append(TypeMismatchError(
                "Num", f"{cond_class_type}{'*' + str(cond_array_size) if cond_array_size else ''}",
                f"if condition must be Num in function {func.name}"
            ))
        
        body_vars = variables.copy()
        self._process_statements(if_expr.body, body_vars, func)
    
    def _analyze_while_expr(self, while_expr: WhileExpression, variables: Dict[str, Variable], func: Function):
        """Analyze a while expression."""
        condition = while_expr.condition
        cond_class_type, cond_array_size = self._analyze_expression(condition, variables, func.name)
        if cond_class_type is not None and (cond_class_type != 'Num' or cond_array_size is not None):
            self.errors.append(TypeMismatchError(
                "Num", f"{cond_class_type}{'*' + str(cond_array_size) if cond_array_size else ''}",
                f"while condition must be Num in function {func.name}"
            ))
        
        body_vars = variables.copy()
        self._process_statements(while_expr.body, body_vars, func)
    
    def _check_result_assignment_type(self, expr: Union[Atom, GeneralExpr, UnaryExpr], 
                                     variables: Dict[str, Variable], func: Function):
        """Check if assignment to result has correct type."""
        expr_class_type, expr_array_size = self._analyze_expression(expr, variables, func.name)
        
        if expr_class_type is not None:
            # Check class type compatibility
            if func.return_class_type != expr_class_type:
                self.errors.append(TypeMismatchError(
                    func.return_class_type, expr_class_type,
                    f"return class type mismatch in function {func.name}"
                ))
            # Check array size compatibility
            if func.return_array_size != expr_array_size:
                self.errors.append(TypeMismatchError(
                    f"{func.return_class_type}{'*' + str(func.return_array_size) if func.return_array_size else ''}",
                    f"{expr_class_type}{'*' + str(expr_array_size) if expr_array_size else ''}",
                    f"return array size mismatch in function {func.name}"
                ))
    
    def _analyze_expression(self, expr: Union[Atom, GeneralExpr, UnaryExpr], 
                           variables: Dict[str, Variable], func_name: str) -> Tuple[Optional[str], Optional[int]]:
        """Analyze an expression and return its type: (class_type, array_size)."""
        if isinstance(expr, GeneralExpr):
            # Binary operations always return Num
            # Validate left and right are valid
            self._analyze_expression(expr.left, variables, func_name)
            self._analyze_expression(expr.right, variables, func_name)
            return 'Num', None
        elif isinstance(expr, UnaryExpr):
            operand_class_type, operand_array_size = self._analyze_expression(expr.operand, variables, func_name)
            if operand_class_type is not None and (operand_class_type != 'Num' or operand_array_size is not None):
                self.errors.append(TypeMismatchError(
                    "Num", f"{operand_class_type}{'*' + str(operand_array_size) if operand_array_size else ''}",
                    f"unary {expr.op} expression must be Num in function {func_name}"
                ))
            return 'Num', None
        
        # Otherwise it's an ATOM
        return self._analyze_atom(expr, variables, func_name)
    
    def _analyze_atom(self, atom: Atom, variables: Dict[str, Variable], 
                     func_name: str) -> Tuple[Optional[str], Optional[int]]:
        """Analyze an ATOM and return its type: (class_type, array_size)."""
        value = atom.value
        
        if isinstance(value, IntegerLiteral):
            # Integer literals are of type Num
            return 'Num', None
        
        elif isinstance(value, IdentifierExpr):
            var_name = value.name
            if var_name in variables:
                var = variables[var_name]
                return var.class_type, var.array_size
            # Check if it's a function name
            if var_name in self.functions:
                func = self.functions[var_name]
                return func.return_class_type, func.return_array_size
            self.errors.append(UndefinedVariableError(var_name, f"in function {func_name}"))
            return None, None
        
        elif isinstance(value, FunctionCall):
            return self._analyze_function_call(value, variables, func_name)
        
        elif isinstance(value, ArrayIndex):
            return self._analyze_array_index_expr(value, variables, func_name)
        
        elif isinstance(value, FieldAccess):
            return self._analyze_field_access(value, variables, func_name)
        
        elif isinstance(value, ConstructorCall):
            return self._analyze_constructor_call(value, variables, func_name)
        
        return None, None
    
    def _analyze_function_call(self, func_call: FunctionCall, variables: Dict[str, Variable], 
                              func_name: str) -> Tuple[Optional[str], Optional[int]]:
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
        
        return func_def.return_class_type, func_def.return_array_size
    
    def _analyze_array_index_expr(self, array_index: ArrayIndex, variables: Dict[str, Variable], 
                                  func_name: str) -> Tuple[Optional[str], Optional[int]]:
        """Analyze an array index expression."""
        var_name = array_index.var_name
        
        if var_name not in variables:
            self.errors.append(UndefinedVariableError(var_name, f"in function {func_name}"))
            return None, None
        
        var = variables[var_name]
        if var.array_size is None:
            self.errors.append(TypeMismatchError(
                "array", var.class_type,
                f"array indexing on non-array variable {var_name} in function {func_name}"
            ))
            return None, None
        
        # Analyze index
        self._analyze_index(array_index.index, var_name, variables, func_name)
        
        # Array indexing returns the element type (same class_type, but not an array)
        return var.class_type, None
    
    def _analyze_field_access(self, field_access: FieldAccess, variables: Dict[str, Variable], 
                             func_name: str) -> Tuple[Optional[str], Optional[int]]:
        """Analyze a field access expression."""
        var_name = field_access.var_name
        field_name = field_access.field
        
        if var_name not in variables:
            self.errors.append(UndefinedVariableError(var_name, f"in function {func_name}"))
            return None, None
        
        var = variables[var_name]
        
        # Check if class exists
        if var.class_type not in self.classes:
            self.errors.append(UndefinedVariableError(
                var.class_type, f"class {var.class_type} not found for field access in function {func_name}"
            ))
            return None, None
        
        clazz = self.classes[var.class_type]
        
        # Find the field
        field = None
        for f in clazz.fields:
            if f.name == field_name:
                field = f
                break
        
        if field is None:
            self.errors.append(UndefinedVariableError(
                field_name, f"field {field_name} not found in class {var.class_type} in function {func_name}"
            ))
            return None, None
        
        # Return the field's type
        return field.class_type, field.array_size
    
    def _analyze_constructor_call(self, constructor_call: ConstructorCall, variables: Dict[str, Variable], 
                                 func_name: str) -> Tuple[Optional[str], Optional[int]]:
        """Analyze a constructor call."""
        class_name = constructor_call.class_name
        
        # Check if class exists
        if class_name not in self.classes:
            self.errors.append(UndefinedFunctionError(
                class_name, f"class {class_name} not found for constructor call in function {func_name}"
            ))
            return None, None
        
        clazz = self.classes[class_name]
        
        # Check that all parameters are valid variables
        for param_name in constructor_call.parameters:
            if param_name not in variables:
                self.errors.append(UndefinedVariableError(
                    param_name, f"as argument to {class_name} constructor in function {func_name}"
                ))
        
        # Constructor returns an instance of the class (not an array)
        return class_name, None
    
