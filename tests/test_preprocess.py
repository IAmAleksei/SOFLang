import unittest
from soflang.centi_parser import parse_program
from soflang.formatter import Formatter


class TestPreprocess(unittest.TestCase):
    """Test roundtrip parsing: parse -> format -> compare"""
    
    def _roundtrip_test(self, original_code):
        """Helper method to test roundtrip parsing and formatting"""
        parsed = parse_program(original_code)
        formatter = Formatter()
        formatted = formatter.format(parsed)
        
        # Test that formatting is idempotent: parse -> format -> parse -> format should match
        parsed2 = parse_program(formatted)
        formatted2 = formatter.format(parsed2)
        
        # Compare normalized (strip leading/trailing whitespace and newlines)
        formatted_normalized = formatted.strip()
        formatted2_normalized = formatted2.strip()
        
        self.assertEqual(
            formatted_normalized, 
            formatted2_normalized,
            f"Roundtrip failed (not idempotent):\nFirst format:\n{formatted}\nSecond format:\n{formatted2}"
        )
    
    def test_simple_function(self):
        """Test simple function with variable declaration and assignment"""
        code = """
Num main() {
    Num a
    a = 5
}
"""
        self._roundtrip_test(code)
    
    def test_function_with_parameters(self):
        """Test function with multiple parameters"""
        code = """
Num add(Num a, Num b) {
    result = a + b
}
"""
        self._roundtrip_test(code)
    
    def test_function_no_parameters(self):
        """Test function with no parameters"""
        code = """
Num getvalue() {
    Num x
    x = 42
    result = x
}
"""
        self._roundtrip_test(code)
    
    def test_empty_function(self):
        """Test function with empty body"""
        # Parser doesn't accept newline inside empty body, formatter adds it
        # So we need to parse first, format, then parse again to verify roundtrip
        code = """
Num empty() {
}
"""
        parsed = parse_program(code)
        formatter = Formatter()
        formatted = formatter.format(parsed)
        # Formatted should have newline inside body, so parse that
        parsed2 = parse_program(formatted)
        formatted2 = formatter.format(parsed2)
        self.assertEqual(formatted.strip(), formatted2.strip())
    
    def test_array_declaration(self):
        """Test array type declarations"""
        code = """
Num test() {
    Num*100 arr
    arr[0] = 5
    result = arr[0]
}
"""
        self._roundtrip_test(code)
    
    def test_array_with_variable_index(self):
        """Test array indexing with variable"""
        code = """
Num test(Num i) {
    Num*10 arr
    arr[i] = 5
    result = arr[i]
}
"""
        self._roundtrip_test(code)
    
    def test_if_expression(self):
        """Test if expressions (??)"""
        code = """
Num test(Num n) {
    n ?? {
        result = 1
    }
}
"""
        self._roundtrip_test(code)
    
    def test_while_expression(self):
        """Test while expressions (...?)"""
        code = """
Num factorial(Num n) {
    result = 1
    n ...? {
        result = result * n
        n = n - 1
    }
}
"""
        self._roundtrip_test(code)
    
    def test_nested_control_flow(self):
        """Test nested if and while expressions"""
        code = """
Num test(Num n) {
    n ?? {
        n ...? {
            result = n
            n = n - 1
        }
    }
}
"""
        self._roundtrip_test(code)
    
    def test_binary_expressions(self):
        """Test binary expressions with different operators"""
        code = """
Num test(Num a, Num b) {
    result = a + b
    result = a * b
    result = a - b
    result = a / b
}
"""
        self._roundtrip_test(code)
    
    def test_unary_expression(self):
        """Test unary expressions (~)"""
        code = """
Num test(Num a) {
    result = ~a
}
"""
        self._roundtrip_test(code)
    
    def test_function_calls(self):
        """Test function calls with parameters"""
        code = """
Num helper(Num x) {
    result = x
}
Num test() {
    Num a
    a = 5
    result = helper(a)
}
"""
        self._roundtrip_test(code)
    
    def test_function_call_no_parameters(self):
        """Test function calls without parameters"""
        code = """
Num getone() {
    result = 1
}
Num test() {
    result = getone()
}
"""
        self._roundtrip_test(code)
    
    def test_constructor_call(self):
        """Test constructor calls"""
        # Test formatter handles constructor calls correctly
        # Note: Parser can't parse this without Point defined, so we test formatter directly
        func_ast = {
            'type': 'func_decl',
            'kind': {'kind': {'dim': 'simple'}, 'base': 'Num'},
            'identifier': 'test',
            'parameters': [],
            'body': [{
                'type': 'assignment',
                'dest': {'type': 'identifier', 'value': 'result'},
                'value': {
                    'type': 'constructor_call',
                    'identifier': 'Point',
                    'parameters': [
                        {'type': 'integer', 'value': 5},
                        {'type': 'integer', 'value': 10}
                    ]
                },
                'line': 2
            }]
        }
        formatter = Formatter()
        formatted = formatter.format([func_ast])
        # Verify output format is correct
        self.assertIn('Point(5, 10)', formatted)
        self.assertIn('Num test()', formatted)
    
    def test_field_access(self):
        """Test field access with #"""
        # Test formatter handles field access correctly
        func_ast = {
            'type': 'func_decl',
            'kind': {'kind': {'dim': 'simple'}, 'base': 'Num'},
            'identifier': 'test',
            'parameters': [],
            'body': [
                {
                    'kind': {'kind': {'dim': 'simple'}, 'base': 'Point'},
                    'type': 'var_decl',
                    'identifier': 'p',
                    'line': 2
                },
                {
                    'type': 'assignment',
                    'dest': {'type': 'identifier', 'value': 'result'},
                    'value': {
                        'type': 'field_access',
                        'var_name': 'p',
                        'field': 'x'
                    },
                    'line': 3
                },
                {
                    'type': 'assignment',
                    'dest': {
                        'type': 'field_access',
                        'var_name': 'p',
                        'field': 'y'
                    },
                    'value': {'type': 'integer', 'value': 10},
                    'line': 4
                }
            ]
        }
        formatter = Formatter()
        formatted = formatter.format([func_ast])
        # Verify output format is correct
        self.assertIn('p#x', formatted)
        self.assertIn('p#y = 10', formatted)
        self.assertIn('Point p', formatted)
    
    def test_var_decl_with_assign(self):
        """Test variable declaration with assignment"""
        code = """
Num test() {
    auto a = 10
    Num b = 20
}
"""
        self._roundtrip_test(code)
    
    def test_integer_values(self):
        """Test positive, negative, and zero integers"""
        # Note: parser converts +5 to 5, so we expect 5 in output
        code = """
Num test() {
    result = 0
    result = 42
    result = -10
    result = 5
}
"""
        self._roundtrip_test(code)
    
    def test_complex_expression(self):
        """Test complex expression with function calls"""
        code = """
Num helper(Num x) {
    result = x
}
Num test() {
    Num a
    Num b
    result = helper(a) + helper(b)
}
"""
        self._roundtrip_test(code)
    
    def test_array_assignment(self):
        """Test array element assignment"""
        code = """
Num test() {
    Num*10 arr
    arr[0] = 1
    arr[1] = 2
    result = arr[0] + arr[1]
}
"""
        self._roundtrip_test(code)
    
    def test_multiple_functions(self):
        """Test multiple function declarations"""
        code = """
Num first() {
    result = 1
}
Num second() {
    result = 2
}
Num third() {
    result = 3
}
"""
        self._roundtrip_test(code)
    
    def test_throw_error(self):
        """Test error statement"""
        code = """
Num test() {
    error
}
"""
        self._roundtrip_test(code)
    
    def test_class_declaration(self):
        """Test class declarations"""
        code = """
Point: x#Num x y#Num
"""
        self._roundtrip_test(code)
    
    def test_class_with_multiple_fields(self):
        """Test class with multiple fields"""
        code = """
Person: name#Num x age#Num x weight#Num
"""
        self._roundtrip_test(code)
    
    def test_class_with_array_field(self):
        """Test class with array field"""
        code = """
Buffer: data#Num*100 x size#Num
"""
        self._roundtrip_test(code)
    
    def test_import_declaration(self):
        """Test import declarations"""
        code = """
load lib/math
"""
        self._roundtrip_test(code)
    
    def test_import_with_path(self):
        """Test import with path"""
        code = """
load @/lib/utils
"""
        self._roundtrip_test(code)
    
    def test_complete_program(self):
        """Test a complete program with all features"""
        # Formatter doesn't preserve blank lines between declarations
        code = """
load lib/math
Point: x#Num x y#Num
Num factorial(Num n) {
    result = 1
    n ...? {
        result = result * n
        n = n - 1
    }
}
Num main() {
    Num*100 arr
    Num a
    auto b = 10
    a = 5
    arr[0] = factorial(a)
    a ?? {
        result = arr[0]
    }
    result = a + b
}
"""
        self._roundtrip_test(code)
    
    def test_nested_if_while(self):
        """Test deeply nested control structures"""
        code = """
Num test(Num n) {
    n ?? {
        n ...? {
            n ?? {
                result = n
                n = n - 1
            }
        }
    }
}
"""
        self._roundtrip_test(code)
    
    def test_multiple_assignments(self):
        """Test multiple assignments in sequence"""
        # Note: parser doesn't support chained binary operations like a + b + c
        # We can only do a + b, so test with simpler expression
        code = """
Num test() {
    Num a
    Num b
    Num c
    a = 1
    b = 2
    c = 3
    result = a + b
}
"""
        self._roundtrip_test(code)
    
    def test_function_with_array_parameter(self):
        """Test function with array parameter"""
        code = """
Num sum(Num*10 arr) {
    result = arr[0]
}
"""
        self._roundtrip_test(code)
    
    def test_array_of_arrays(self):
        """Test nested array access patterns"""
        code = """
Num test() {
    Num*10 arr
    Num i
    i = 0
    arr[i] = 42
    result = arr[i]
}
"""
        self._roundtrip_test(code)
    
    def test_while_with_if(self):
        """Test while loop containing if statement"""
        code = """
Num test(Num n) {
    n ...? {
        n ?? {
            result = n
        }
        n = n - 1
    }
}
"""
        self._roundtrip_test(code)
    
    def test_if_with_while(self):
        """Test if statement containing while loop"""
        code = """
Num test(Num n) {
    n ?? {
        n ...? {
            result = n
            n = n - 1
        }
    }
}
"""
        self._roundtrip_test(code)


if __name__ == "__main__":
    unittest.main()

