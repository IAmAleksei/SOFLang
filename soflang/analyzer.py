from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass


@dataclass
class Field:
    """Represents a field declaration in a class."""
    name: str
    class_type: Union[str, 'Class']  # Class name (e.g., 'Num', 'Point')
    array_size: Optional[int] = None  # None for simple types, int for arrays


@dataclass
class Class:
    """Represents a class declaration."""
    name: str
    fields: List[Field]


@dataclass
class Variable:
    """Represents a variable declaration."""
    name: str
    class_type: str  # Class name (e.g., 'Num', 'Point')
    array_size: Optional[int] = None  # None for simple types, int for arrays


# Expression classes
@dataclass
class IntegerLiteral:
    """Represents an integer literal."""
    value: int


@dataclass
class IdentifierExpr:
    """Represents an identifier expression."""
    name: str


@dataclass
class FunctionCall:
    """Represents a function call."""
    name: str
    parameters: List['Atom']  # List of atom values (can be identifiers, integers, function calls, etc.)


@dataclass
class ArrayIndex:
    """Represents an array index expression."""
    var_name: str
    index: Union[int, str]  # Either an integer or a variable name


@dataclass
class FieldAccess:
    """Represents a field access expression."""
    var_name: str
    field: str


@dataclass
class ConstructorCall:
    """Represents a constructor call."""
    class_name: str
    parameters: List[str]  # List of variable names


@dataclass
class Atom:
    """Represents an ATOM expression."""
    value: Union[IntegerLiteral, IdentifierExpr, FunctionCall, ArrayIndex, FieldAccess, ConstructorCall]


@dataclass
class GeneralExpr:
    """Represents a general expression (binary operation)."""
    left: Atom
    op: str  # "+", "-", "*", "/"
    right: Atom


@dataclass
class UnaryExpr:
    """Represents a unary expression."""
    op: str  # currently "~"
    operand: Union[Atom, GeneralExpr, 'UnaryExpr']


# Statement classes
@dataclass
class VariableDeclaration:
    """Represents a variable declaration statement."""
    variable: Variable
    line: Optional[int] = None


@dataclass
class VarDeclWithAssign:
    """Represents a merged variable declaration with assignment.
    If class_type is None, it means 'auto' and should be inferred from value."""
    name: str
    value: Union[Atom, GeneralExpr, UnaryExpr]
    class_type: Optional[str] = None
    array_size: Optional[int] = None
    line: Optional[int] = None


@dataclass
class Assignment:
    """Represents an assignment statement."""
    target: Union[str, ArrayIndex]
    value: Union[Atom, GeneralExpr, UnaryExpr]
    line: Optional[int] = None


@dataclass
class IfExpression:
    """Represents an if expression statement."""
    condition: Union[Atom, GeneralExpr, UnaryExpr]
    body: List['Statement']
    line: Optional[int] = None


@dataclass
class WhileExpression:
    """Represents a while expression statement."""
    condition: Union[Atom, GeneralExpr, UnaryExpr]
    body: List['Statement']
    line: Optional[int] = None


@dataclass
class Throwable:
    line: Optional[int] = None


# Type alias for Statement
Statement = Union[VariableDeclaration, VarDeclWithAssign, Assignment, IfExpression, WhileExpression | Throwable]


@dataclass
class Function:
    """Represents a function declaration."""
    name: str
    return_class_type: str  # Class name (e.g., 'Num', 'Point')
    return_array_size: Optional[int] = None  # None for simple types, int for arrays
    parameters: List[Variable] = None
    body: List[Statement] = None  # Parsed body statements
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.body is None:
            self.body = []


class AnalysisError(Exception):
    """Base class for analysis errors."""
    pass


class UndefinedVariableError(AnalysisError):
    """Raised when a variable is used but not defined."""
    def __init__(self, var_name: str, context: str = ""):
        self.var_name = var_name
        self.context = context
        super().__init__(f"Undefined variable: {var_name}" + (f" ({context})" if context else ""))


class UndefinedFunctionError(AnalysisError):
    """Raised when a function is called but not defined."""
    def __init__(self, func_name: str, context: str = ""):
        self.func_name = func_name
        self.context = context
        super().__init__(f"Undefined function: {func_name}" + (f" ({context})" if context else ""))


class TypeMismatchError(AnalysisError):
    """Raised when types don't match."""
    def __init__(self, expected: str, actual: str, context: str = ""):
        self.expected = expected
        self.actual = actual
        self.context = context
        super().__init__(f"Type mismatch: expected {expected}, got {actual}" + (f" ({context})" if context else ""))


class ArgumentCountError(AnalysisError):
    """Raised when function call has wrong number of arguments."""
    def __init__(self, func_name: str, expected: int, actual: int):
        self.func_name = func_name
        self.expected = expected
        self.actual = actual
        super().__init__(f"Function {func_name} expects {expected} arguments, got {actual}")


class BonAnalyzer:
    """Transforms raw parser output to Python classes."""
    
    def __init__(self):
        self.functions: Dict[str, Function] = {}
        self.classes: Dict[str, Class] = {}

    def get_functions(self):
        return list(self.functions.values())

    def analyze(self, parsed_program: List[Dict]):
        """
        Transform a parsed program into a list of Function objects.
        
        Args:
            parsed_program: List of function and class declarations (dict structure from parse_program)
            
        Returns:
            List of Function objects
        """
        self.functions = {}
        self.classes = {}
        
        # Num is a built-in class (no fields, represents primitive numbers)
        # It's always available
        self.classes['Num'] = Class('Num', [])
        
        # First pass: process all class declarations
        for decl in parsed_program:
            if isinstance(decl, dict) and decl.get('type') == 'clazz_decl':
                self._process_class_declaration(decl)

        # Second pass: process all function declarations
        for decl in parsed_program:
            if isinstance(decl, dict) and decl.get('type') == 'func_decl':
                self._process_function_declaration(decl)
        
        # Return list of functions for callers/tests expecting a return value
        return list(self.functions.values())

    def _process_function_declaration(self, func_decl: Dict):
        """Process a function declaration to extract its signature and body."""
        if func_decl.get('type') != 'func_decl':
            return
        
        # Extract return type
        kind = func_decl.get('kind')
        return_class_type, return_array_size = self._parse_type(kind)
        
        # Extract function name
        func_name_obj = func_decl.get('identifier')
        func_name = self._get_identifier_value(func_name_obj)
        
        if not func_name:
            return  # Skip if no valid function name
        
        parameters = []
        params_data = func_decl.get('parameters', [])
        for param_decl in params_data:
            if isinstance(param_decl, dict) and param_decl.get('type') == 'var_decl':
                var = self._parse_variable_decl(param_decl)
                if var:
                    parameters.append(var)
        
        # Extract and parse body
        body_raw = func_decl.get('body', [])
        body = self._parse_body(body_raw)
        
        func = Function(func_name, return_class_type, return_array_size, parameters, body)
        self.functions[func_name] = func
    
    def _parse_type(self, type_dict: Dict) -> Tuple[str, Optional[int]]:
        """Parse TYPE structure: {'kind': {'dim': 'simple'} or {'dim': 'array', 'size': int}, 'base': class_name}
        Returns: (class_type, array_size)
        All types are class types, including 'Num'.
        """
        if not isinstance(type_dict, dict):
            return 'Num', None
        
        base = type_dict.get('base')
        kind = type_dict.get('kind', {})
        
        if not isinstance(kind, dict):
            return 'Num', None
        
        dim = kind.get('dim')
        
        # Extract class name from base
        if isinstance(base, dict) and base.get('type') == 'identifier':
            class_name = base.get('value')
        elif isinstance(base, str):
            class_name = base
        else:
            return 'Num', None
        
        # Class name should already be uppercase (from parser) - no normalization needed
        if not class_name:
            return 'Num', None
        
        # Check if it's an array
        if dim == 'array':
            size = kind.get('size')
            try:
                size = int(size) if size is not None else None
                return class_name, size
            except (ValueError, TypeError):
                return class_name, None
        else:
            return class_name, None
    
    def _parse_variable_decl(self, var_decl: Dict) -> Optional[Variable]:
        """Parse VAR_DECL structure: {'kind': TYPE, 'type': 'var_decl', 'identifier': IDENTIFIER}"""
        if not isinstance(var_decl, dict) or var_decl.get('type') != 'var_decl':
            return None
        
        kind = var_decl.get('kind')
        identifier_obj = var_decl.get('identifier')
        
        var_name = self._get_identifier_value(identifier_obj)
        if not var_name:
            return None
        
        class_type, array_size = self._parse_type(kind)
        return Variable(var_name, class_type, array_size)
    
    def _get_identifier_value(self, identifier_obj: Dict) -> Optional[str]:
        """Extract value from IDENTIFIER structure: {'type': 'identifier', 'value': str}"""
        if isinstance(identifier_obj, dict):
            if identifier_obj.get('type') != 'identifier':
                return None
            value = identifier_obj.get('value')
        else:
            value = identifier_obj
        
        if isinstance(value, str) and self._is_identifier(value):
            return value
        return None
    
    def _is_identifier(self, token: str) -> bool:
        """Check if token is an identifier (lowercase letters only)."""
        return True
    
    def _parse_body(self, body_raw: List[Dict]) -> List[Statement]:
        """Parse function body from raw LINE_EXPR structures."""
        statements = []
        for line_expr in body_raw:
            if not isinstance(line_expr, dict):
                continue
            statement = self._parse_statement(line_expr)
            if statement:
                statements.append(statement)
        
        return statements
    
    def _parse_statement(self, stmt_dict: Dict) -> Optional[Statement]:
        """Parse a statement from dict structure."""
        stmt_type = stmt_dict.get('type')
        
        if stmt_type == 'var_decl':
            var = self._parse_variable_decl(stmt_dict)
            if var:
                return VariableDeclaration(var, stmt_dict.get('line'))
        elif stmt_type == 'var_decl_with_assign':
            # Build dedicated node
            var_name_obj = stmt_dict.get('identifier')
            kind = stmt_dict.get('kind')
            var_name = self._get_identifier_value(var_name_obj)
            if not var_name:
                return None
            value_obj = stmt_dict.get('value')
            expr = self._parse_expression(value_obj)
            if expr is None:
                return None
            declared_class_type: Optional[str] = None
            declared_array_size: Optional[int] = None
            # If kind is dict -> explicit type; if 'auto' or missing -> leave None for validator inference
            if isinstance(kind, dict):
                declared_class_type, declared_array_size = self._parse_type(kind)
            elif isinstance(kind, str) and kind.lower() != 'auto':
                declared_class_type = kind
                declared_array_size = None
            return VarDeclWithAssign(
                name=var_name,
                value=expr,
                class_type=declared_class_type,
                array_size=declared_array_size,
                line=stmt_dict.get('line')
            )
        elif stmt_type == 'assignment':
            assignment = self._parse_assignment(stmt_dict)
            if assignment:
                return assignment
        elif stmt_type == 'if_expr':
            return self._parse_if_expr(stmt_dict)
        elif stmt_type == 'while_expr':
            return self._parse_while_expr(stmt_dict)
        elif stmt_type == 'throw_error':
            return Throwable()

        return None
    
    def _parse_assignment(self, assignment_dict: Dict) -> Optional[Assignment]:
        """Parse ASSIGNMENT: {'type': 'assignment', 'dest': ARRAY_INDEX or IDENTIFIER, 'value': GENERAL_EXPR or ATOM}"""
        dest_obj = assignment_dict.get('dest')
        value_obj = assignment_dict.get('value')
        
        if not isinstance(dest_obj, dict) or not isinstance(value_obj, dict):
            return None
        
        expr = self._parse_expression(value_obj)
        if expr is None:
            return None
        
        dest_type = dest_obj.get('type')
        if dest_type == 'identifier':
            var_name = self._get_identifier_value(dest_obj)
            if not var_name:
                return None
            return Assignment(var_name, expr, assignment_dict.get('line'))
        elif dest_type == 'array_index':
            array_index = self._parse_array_index_expr(dest_obj)
            if not array_index:
                return None
            return Assignment(array_index, expr, assignment_dict.get('line'))
        
        return None
    
    def _parse_index(self, index_obj: Any) -> Optional[Union[int, str]]:
        """Parse array index: INTEGER or IDENTIFIER"""
        if isinstance(index_obj, dict):
            if index_obj.get('type') == 'integer':
                return index_obj.get('value')
            elif index_obj.get('type') == 'identifier':
                return index_obj.get('value')
        return None
    
    def _parse_if_expr(self, if_dict: Dict) -> Optional[IfExpression]:
        """Parse IF_EXPR structures with expression conditions."""
        condition_obj = if_dict.get('condition')
        condition = self._parse_expression(condition_obj)
        
        if condition is None:
            return None
        
        body_raw = if_dict.get('body', [])
        body = self._parse_body(body_raw)
        
        return IfExpression(condition, body, if_dict.get('line'))
    
    def _parse_while_expr(self, while_dict: Dict) -> Optional[WhileExpression]:
        """Parse WHILE_EXPR structures with expression conditions."""
        condition_obj = while_dict.get('condition')
        condition = self._parse_expression(condition_obj)
        
        if condition is None:
            return None
        
        body_raw = while_dict.get('body', [])
        body = self._parse_body(body_raw)
        
        return WhileExpression(condition, body, while_dict.get('line'))
    
    def _parse_expression(self, expr_dict: Any) -> Optional[Union[Atom, GeneralExpr, UnaryExpr]]:
        """Parse an expression: ATOM, GENERAL_EXPR, or UNARY_EXPR"""
        if not isinstance(expr_dict, dict):
            return None
        
        expr_type = expr_dict.get('type')

        if expr_type == 'un_expr':
            op = expr_dict.get('op')
            inner = expr_dict.get('inner')
            if not op or inner is None:
                return None
            operand = self._parse_expression(inner)
            if operand:
                return UnaryExpr(op, operand)
            return None

        # Check if it's a GENERAL_EXPR
        if expr_type == 'gen_expr':
            left = expr_dict.get('left')
            right = expr_dict.get('right')
            op = expr_dict.get('op')

            if not left or not right or not op:
                return None

            left_atom = self._parse_atom(left)
            right_atom = self._parse_atom(right)

            if left_atom and right_atom:
                return GeneralExpr(left_atom, op, right_atom)
        
        # Otherwise it's an ATOM
        atom = self._parse_atom(expr_dict)
        if atom:
            return atom
        
        return None
    
    def _parse_atom(self, atom_dict: Any) -> Optional[Atom]:
        """Parse an ATOM: INTEGER or FUNCTION_CALL or ARRAY_INDEX or IDENTIFIER"""
        if not isinstance(atom_dict, dict):
            return None
        
        token_type = atom_dict.get('type')
        
        if token_type == 'integer':
            int_value = atom_dict.get('value')
            if isinstance(int_value, int):
                return Atom(IntegerLiteral(int_value))
        elif token_type == 'identifier':
            var_name = atom_dict.get('value')
            if isinstance(var_name, str) and self._is_identifier(var_name):
                return Atom(IdentifierExpr(var_name))
        elif token_type == 'func_call':
            func_call = self._parse_function_call(atom_dict)
            if func_call:
                return Atom(func_call)
        elif token_type == 'array_index':
            array_index = self._parse_array_index_expr(atom_dict)
            if array_index:
                return Atom(array_index)
        elif token_type == 'field_access':
            field_access = self._parse_field_access(atom_dict)
            if field_access:
                return Atom(field_access)
        elif token_type == 'constructor_call':
            constructor_call = self._parse_constructor_call(atom_dict)
            if constructor_call:
                return Atom(constructor_call)
        
        return None
    
    def _parse_field_access(self, field_access_dict: Dict) -> Optional[FieldAccess]:
        """Parse FIELD_ACCESS: {'type': 'field_access', 'var_name': IDENTIFIER_STR, 'field': IDENTIFIER_STR}"""
        var_name_obj = field_access_dict.get('var_name')
        var_name = self._get_identifier_value(var_name_obj)
        
        if not var_name:
            return None
        
        field_obj = field_access_dict.get('field')
        field = self._get_identifier_value(field_obj)
        
        if not field:
            return None
        
        return FieldAccess(var_name, field)
    
    def _parse_constructor_call(self, constructor_call_dict: Dict) -> Optional[ConstructorCall]:
        """Parse CONSTRUCTOR_CALL: {'type': 'constructor_call', 'identifier': CLASS_NAME_STR, 'parameters': list of IDENTIFIERs}"""
        class_name_obj = constructor_call_dict.get('identifier')
        class_name = self._get_class_name(class_name_obj)
        
        if not class_name:
            return None
        
        parameters_raw = constructor_call_dict.get('parameters', [])
        parameters = []
        for param_obj in parameters_raw:
            param_name = self._get_identifier_value(param_obj)
            if param_name:
                parameters.append(param_name)
        
        return ConstructorCall(class_name, parameters)
    
    def _parse_function_call(self, func_call_dict: Dict) -> Optional[FunctionCall]:
        """Parse FUNCTION_CALL: {'type': 'func_call', 'identifier': IDENTIFIER_STR, 'parameters': list of ATOMs}"""
        func_name_obj = func_call_dict.get('identifier')
        func_name = self._get_identifier_value(func_name_obj)
        
        if not func_name:
            return None
        
        parameters_raw = func_call_dict.get('parameters', [])
        parameters = []
        for param_obj in parameters_raw:
            param_atom = self._parse_atom(param_obj)
            if param_atom:
                parameters.append(param_atom)
        
        return FunctionCall(func_name, parameters)
    
    def _parse_array_index_expr(self, array_index_dict: Dict) -> Optional[ArrayIndex]:
        """Parse ARRAY_INDEX: {'type': 'array_index', 'var_name': IDENTIFIER_STR, 'index': INTEGER or IDENTIFIER}"""
        var_name_obj = array_index_dict.get('var_name')
        var_name = self._get_identifier_value(var_name_obj)
        
        if not var_name:
            return None
        
        index_obj = array_index_dict.get('index')
        index = self._parse_index(index_obj)
        
        if index is None:
            return None
        
        return ArrayIndex(var_name, index)
    
    def _process_class_declaration(self, clazz_decl: Dict):
        """Process a class declaration to extract its name and fields."""
        if clazz_decl.get('type') != 'clazz_decl':
            return
        
        # Extract class name
        clazz_name_obj = clazz_decl.get('identifier')
        clazz_name = self._get_class_name(clazz_name_obj)
        
        if not clazz_name:
            return  # Skip if no valid class name
        
        # Extract fields
        fields = []
        types_data = clazz_decl.get('types', [])
        for field_decl in types_data:
            if isinstance(field_decl, dict) and field_decl.get('type') == 'field_decl':
                field = self._parse_field_decl(field_decl)
                if field:
                    fields.append(field)

        clazz = Class(clazz_name, fields)
        self.classes[clazz_name] = clazz

    def _get_class_name(self, identifier_obj: Any) -> Optional[str]:
        """Extract class name from identifier (uppercase)."""
        if isinstance(identifier_obj, dict):
            if identifier_obj.get('type') == 'identifier':
                value = identifier_obj.get('value')
                if isinstance(value, str) and value and value[0].isupper():
                    return value
        elif isinstance(identifier_obj, str) and identifier_obj and identifier_obj[0].isupper():
            return identifier_obj
        return None
    
    def _parse_field_decl(self, field_decl: Dict) -> Optional[Field]:
        """Parse FIELD_DECL structure: {'type': 'field_decl', 'identifier': IDENTIFIER, 'kind': TYPE}"""
        if not isinstance(field_decl, dict) or field_decl.get('type') != 'field_decl':
            return None
        
        identifier_obj = field_decl.get('identifier')
        field_name = self._get_identifier_value(identifier_obj)
        
        if not field_name:
            return None
        
        kind = field_decl.get('kind')
        class_type, array_size = self._parse_type(kind)

        return Field(field_name, class_type, array_size)
