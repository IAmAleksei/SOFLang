import unittest
from pyparsing import ParseException
from soflang.centi_parser import (
    global_expr, var_decl, assignment, expr, function_call,
    if_expr, while_expr, func_decl, integer, identifier, TYPE
)


class TestParser(unittest.TestCase):
    def test_valid_function_declaration(self):
        code = """
        num factorial(num n) {
            result = 1
            n ...? {
                result = result * n
                n = n - 1
            }
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function declaration failed to parse.")

    def test_valid_variable_declaration(self):
        code = "num x"
        try:
            result = var_decl.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid variable declaration failed to parse.")

    def test_valid_assignment(self):
        code = "x = 42"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid assignment failed to parse.")

    def test_valid_binary_expression(self):
        code = "x = x + 1"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid binary expression failed to parse.")

    # def test_invalid_syntax(self):
    #     code = "num x ="
    #     with self.assertRaises(ParseException):
    #         global_expr.parse_string(code, parse_all=True)

    def test_nested_while_loop(self):
        code = """
        num factorial(num n) {
            result = 1
            n ...? {
                num temp
                temp = n
                temp ...? {
                    result = result * temp
                    temp = temp - 1
                }
                n = n - 1
            }
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid nested while loop failed to parse.")

    def test_array_type_declaration(self):
        """Test array type variable declarations like num*5 x"""
        code = "num*10 arr"
        try:
            result = var_decl.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array type declaration failed to parse.")

    def test_function_call_no_parameters(self):
        """Test function calls without parameters"""
        code = "foo()"
        try:
            result = function_call.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function call without parameters failed to parse.")

    def test_function_call_with_parameters(self):
        """Test function calls with parameters"""
        code = "foo(x, y, z)"
        try:
            result = function_call.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function call with parameters failed to parse.")

    def test_function_call_single_parameter(self):
        """Test function calls with a single parameter"""
        code = "bar(x)"
        try:
            result = function_call.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function call with single parameter failed to parse.")

    def test_if_expression(self):
        """Test if expressions (??)"""
        code = """x ?? {
    y = 1
}"""
        try:
            result = if_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid if expression failed to parse.")

    def test_while_loop_standalone(self):
        """Test standalone while loops"""
        code = """x ...? {
    y = y + 1
}"""
        try:
            result = while_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid while loop failed to parse.")

    def test_nested_if_expression(self):
        """Test nested if expressions"""
        code = """x ?? {
    y ?? {
        z = 1
    }
}"""
        try:
            result = if_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid nested if expression failed to parse.")

    def test_function_no_parameters(self):
        """Test function declaration with no parameters"""
        code = """
        num getvalue() {
            num x
            x = 42
            result = x
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with no parameters failed to parse.")

    def test_function_multiple_parameters(self):
        """Test function declaration with multiple parameters"""
        code = """
        num add(num a, num b, num c) {
            num d
            d = a + b
            d = d + c
            result = d
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with multiple parameters failed to parse.")

    def test_function_no_return_value(self):
        """Test function with only statements, no return - return values are now optional"""
        code = """
        num print(num x) {
            num temp
            temp = x
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with no return value failed to parse.")

    def test_function_only_return(self):
        """Test function with no statements (empty body)"""
        code = """
        num getone() {
            result = 1
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with only return failed to parse.")

    def test_operator_precedence(self):
        """Test that single binary expressions work (precedence not applicable for single operations)"""
        # Per spec: expr only accepts single binary expressions (atom op atom)
        # Chained operations like "2 + 3 * 4" are not allowed
        code = "x = 2 + 3"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid single binary expression failed to parse.")

    def test_complex_binary_expression(self):
        """Test that single binary expressions work (chained operations not allowed per spec)"""
        # Per spec: expr only accepts single binary expressions (atom op atom)
        # Chained operations are not allowed
        code = "x = a + b"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid single binary expression failed to parse.")

    def test_negative_integer(self):
        """Test negative integers"""
        code = "x = -42"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid negative integer failed to parse.")

    def test_positive_integer_explicit(self):
        """Test explicitly positive integers"""
        code = "x = +100"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid positive integer with + sign failed to parse.")

    def test_function_call_in_expression(self):
        """Test function calls as part of expressions"""
        code = "x = foo() + bar(y)"
        try:
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function call in expression failed to parse.")

    def test_multiple_function_declarations(self):
        """Test multiple function declarations"""
        code = """
        num first() {
            result = 1
        }
        num second() {
            result = 2
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid multiple function declarations failed to parse.")

    def test_integer_parsing(self):
        """Test integer parsing"""
        test_cases = ["0", "42", "-10", "+5", "123456"]
        for code in test_cases:
            with self.subTest(code=code):
                try:
                    result = integer.parse_string(code, parse_all=True)
                    self.assertTrue(result)
                except ParseException:
                    self.fail(f"Valid integer '{code}' failed to parse.")

    def test_identifier_parsing(self):
        """Test identifier parsing (only lowercase letters)"""
        test_cases = ["x", "abc", "foo", "bar"]
        for code in test_cases:
            with self.subTest(code=code):
                try:
                    result = identifier.parse_string(code, parse_all=True)
                    self.assertTrue(result)
                except ParseException:
                    self.fail(f"Valid identifier '{code}' failed to parse.")

    def test_type_parsing(self):
        """Test type parsing (num and array types)"""
        test_cases = ["num", "num*5", "num*100"]
        for code in test_cases:
            with self.subTest(code=code):
                try:
                    result = TYPE.parse_string(code, parse_all=True)
                    self.assertTrue(result)
                except ParseException:
                    self.fail(f"Valid type '{code}' failed to parse.")

    def test_expression_parsing(self):
        """Test expression parsing - only single binary expressions allowed per spec"""
        # Per spec: expr only accepts binary expressions (atom op atom)
        # Atoms and chained operations are not allowed in expr
        test_cases = [
            "x + y",
            "a * b",
            "5 - 3",
            "10 / 2",
            "foo() + bar()",
            "x * y"
        ]
        for code in test_cases:
            with self.subTest(code=code):
                try:
                    result = expr.parse_string(code, parse_all=True)
                    self.assertTrue(result)
                except ParseException:
                    self.fail(f"Valid binary expression '{code}' failed to parse.")

    def test_complex_function_with_all_features(self):
        """Test a complex function using all language features"""
        code = """
        num complex(num a, num b) {
            num temp
            result = 0
            temp = a
            temp ?? {
                result = result + temp
                temp = temp - 1
            }
            temp ...? {
                result = result * b
                b = b - 1
            }
            result = result + foo(x, y)
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid complex function with all features failed to parse.")


    def test_array_index_access(self):
        """Test array element access syntax arr[index]"""
        code = "arr[5]"
        try:
            from soflang.centi_parser import array_index
            result = array_index.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array index access failed to parse.")
    
    def test_array_index_assignment(self):
        """Test array element assignment syntax arr[index] = value"""
        code = "arr[0] = 10"
        try:
            from soflang.centi_parser import assignment
            result = assignment.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array index assignment failed to parse.")
    
    def test_array_index_in_expression(self):
        """Test array indexing in expressions"""
        code = """
        num test() {
            num*10 arr
            arr[0] = 5
            result = arr[0] + 1
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array index in expression failed to parse.")
    
    def test_array_index_with_variable(self):
        """Test array indexing with variable index"""
        code = """
        num test(num i) {
            num*10 arr
            arr[i] = 5
            result = arr[i]
        }
        """
        try:
            result = global_expr.parse_string(code, parse_all=True)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array index with variable failed to parse.")
    
    def test_array_index_complex_expression_rejected(self):
        """Test that complex expressions in array indices are rejected"""
        code = "arr[i + 1]"
        with self.assertRaises(ParseException):
            from soflang.centi_parser import array_index
            array_index.parse_string(code, parse_all=True)

    def test_atom(self):
        """Test that complex expressions in array indices are rejected"""
        code = "factorial(i)"
        from soflang.centi_parser import atom
        result = atom.parse_string(code, parse_all=True)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
