import unittest
from pyparsing import ParseException

from soflang.centi_parser import Parser


class TestParser(unittest.TestCase):
    def test_valid_function_declaration(self):
        code = """
        Num factorial(Num n) {
            result = 1
            n ...? {
                result = result * n
                n = n - 1
            }
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function declaration failed to parse.")

    def test_nested_while_loop(self):
        code = """
        Num factorial(Num n) {
            result = 1
            n ...? {
                Num temp
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
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid nested while loop failed to parse.")

    def test_function_no_parameters(self):
        """Test function declaration with no parameters"""
        code = """
        Num getvalue() {
            Num x
            x = 42
            result = x
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with no parameters failed to parse.")

    def test_function_multiple_parameters(self):
        """Test function declaration with multiple parameters"""
        code = """
        Num add(Num a, Num b, Num c) {
            Num d
            d = a + b
            d = d + c
            result = d
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with multiple parameters failed to parse.")

    def test_function_no_return_value(self):
        """Test function with only statements, no return - return values are now optional"""
        code = """
        Num print(Num x) {
            Num temp
            temp = x
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with no return value failed to parse.")

    def test_function_only_return(self):
        """Test function with no statements (empty body)"""
        code = """
        Num getone() {
            result = 1
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid function with only return failed to parse.")

    def test_multiple_function_declarations(self):
        """Test multiple function declarations"""
        code = """
        Num first() {
            result = 1
        }
        Num second() {
            result = 2
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid multiple function declarations failed to parse.")

    def test_complex_function_with_all_features(self):
        """Test a complex function using all language features"""
        code = """
        Num complex(Num a, Num b) {
            Num temp
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
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid complex function with all features failed to parse.")

    def test_array_index_in_expression(self):
        """Test array indexing in expressions"""
        code = """
        Num test() {
            Num*10 arr
            arr[0] = 5
            result = arr[0] + 1
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array index in expression failed to parse.")
    
    def test_array_index_with_variable(self):
        """Test array indexing with variable index"""
        code = """
        Num test(Num i) {
            Num*10 arr
            arr[i] = 5
            result = arr[i]
        }
        """
        try:
            result = Parser().parse_program(code)
            self.assertTrue(result)
        except ParseException:
            self.fail("Valid array index with variable failed to parse.")
    

if __name__ == "__main__":
    unittest.main()
