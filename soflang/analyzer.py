from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum


class Type(Enum):
    """Type enumeration for SoLang types."""
    NUM = "num"
    ARRAY = "array"


@dataclass
class Variable:
    """Represents a variable declaration."""
    name: str
    type: Type
    array_size: Optional[int] = None


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
    parameters: List[str]  # List of variable names


@dataclass
class ArrayIndex:
    """Represents an array index expression."""
    var_name: str
    index: Union[int, str]  # Either an integer or a variable name


@dataclass
class Atom:
    """Represents an ATOM expression."""
    value: Union[IntegerLiteral, IdentifierExpr, FunctionCall, ArrayIndex]


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


@dataclass
class Assignment:
    """Represents an assignment statement."""
    target: Union[str, ArrayIndex]
    value: Union[Atom, GeneralExpr, UnaryExpr]


@dataclass
class IfExpression:
    """Represents an if expression statement."""
    condition: Union[Atom, GeneralExpr, UnaryExpr]
    body: List['Statement']


@dataclass
class WhileExpression:
    """Represents a while expression statement."""
    condition: Union[Atom, GeneralExpr, UnaryExpr]
    body: List['Statement']


# Type alias for Statement
Statement = Union[VariableDeclaration, Assignment, IfExpression, WhileExpression]


@dataclass
class Function:
    """Represents a function declaration."""
    name: str
    return_type: Type
    return_array_size: Optional[int] = None
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
    
    def analyze(self, parsed_program: List[Dict]) -> List[Function]:
        """
        Transform a parsed program into a list of Function objects.
        
        Args:
            parsed_program: List of function declarations (dict structure from parse_program)
            
        Returns:
            List of Function objects
        """
        self.functions = {}
        
        # Process all function declarations
        for func_decl in parsed_program:
            if isinstance(func_decl, dict) and func_decl.get('type') == 'func_decl':
                self._process_function_declaration(func_decl)
        
        return list(self.functions.values())
    
    def _process_function_declaration(self, func_decl: Dict):
        """Process a function declaration to extract its signature and body."""
        if func_decl.get('type') != 'func_decl':
            return
        
        # Extract return type
        kind = func_decl.get('kind')
        return_type, return_array_size = self._parse_type(kind)
        
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
        
        func = Function(func_name, return_type, return_array_size, parameters, body)
        self.functions[func_name] = func
    
    def _parse_type(self, type_dict: Dict) -> Tuple[Type, Optional[int]]:
        """Parse TYPE structure: {'kind': {'dim': 'simple'} or {'dim': 'array', 'size': int}, 'base': 'num'}"""
        if not isinstance(type_dict, dict):
            return Type.NUM, None
        
        base = type_dict.get('base', 'num')
        kind = type_dict.get('kind', {})
        
        if not isinstance(kind, dict):
            return Type.NUM, None
        
        dim = kind.get('dim')
        if dim == 'array':
            size = kind.get('size')
            try:
                size = int(size) if size is not None else None
                return Type.ARRAY, size
            except (ValueError, TypeError):
                return Type.ARRAY, None
        elif dim == 'simple':
            return Type.NUM, None
        
        return Type.NUM, None
    
    def _parse_variable_decl(self, var_decl: Dict) -> Optional[Variable]:
        """Parse VAR_DECL structure: {'kind': TYPE, 'type': 'var_decl', 'identifier': IDENTIFIER}"""
        if not isinstance(var_decl, dict) or var_decl.get('type') != 'var_decl':
            return None
        
        kind = var_decl.get('kind')
        identifier_obj = var_decl.get('identifier')
        
        var_name = self._get_identifier_value(identifier_obj)
        if not var_name:
            return None
        
        var_type, array_size = self._parse_type(kind)
        return Variable(var_name, var_type, array_size)
    
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
        return isinstance(token, str) and token.isalpha() and token.islower()
    
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
                return VariableDeclaration(var)
        elif stmt_type == 'assignment':
            assignment = self._parse_assignment(stmt_dict)
            if assignment:
                return assignment
        elif stmt_type == 'if_expr':
            return self._parse_if_expr(stmt_dict)
        elif stmt_type == 'while_expr':
            return self._parse_while_expr(stmt_dict)
        
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
            return Assignment(var_name, expr)
        elif dest_type == 'array_index':
            array_index = self._parse_array_index_expr(dest_obj)
            if not array_index:
                return None
            return Assignment(array_index, expr)
        
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
        
        return IfExpression(condition, body)
    
    def _parse_while_expr(self, while_dict: Dict) -> Optional[WhileExpression]:
        """Parse WHILE_EXPR structures with expression conditions."""
        condition_obj = while_dict.get('condition')
        condition = self._parse_expression(condition_obj)
        
        if condition is None:
            return None
        
        body_raw = while_dict.get('body', [])
        body = self._parse_body(body_raw)
        
        return WhileExpression(condition, body)
    
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
        
        return None
    
    def _parse_function_call(self, func_call_dict: Dict) -> Optional[FunctionCall]:
        """Parse FUNCTION_CALL: {'type': 'func_call', 'identifier': IDENTIFIER_STR, 'parameters': list of IDENTIFIERs}"""
        func_name_obj = func_call_dict.get('identifier')
        func_name = self._get_identifier_value(func_name_obj)
        
        if not func_name:
            return None
        
        parameters_raw = func_call_dict.get('parameters', [])
        parameters = []
        for param_obj in parameters_raw:
            param_name = self._get_identifier_value(param_obj)
            if param_name:
                parameters.append(param_name)
        
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
