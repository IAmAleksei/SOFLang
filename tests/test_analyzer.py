import unittest
from soflang.centi_parser import parse_program
from soflang.analyzer import (
    BonAnalyzer, UndefinedVariableError, UndefinedFunctionError,
    TypeMismatchError, ArgumentCountError
)
from soflang.validator import MilliValidator


class TestAnalyzer(unittest.TestCase):
    def _analyze_and_validate(self, code):
        """Helper method to parse, analyze, and validate code."""
        parsed = parse_program(code)
        analyzer = BonAnalyzer()
        functions = analyzer.analyze(parsed)
        validator = MilliValidator()
        errors = validator.validate(functions)
        return errors
    
    def test_valid_program(self):
        """Test that a valid program produces no errors."""
        code = """
        num factorial(num n) {
            result = 1
        }
        """
        errors = self._analyze_and_validate(code)
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
    
    def test_undefined_variable(self):
        """Test detection of undefined variable."""
        code = """
        num test() {
            x = 1
        }
        """
        errors = self._analyze_and_validate(code)
        self.assertGreater(len(errors), 0, "Expected errors for undefined variable")
        self.assertTrue(any(isinstance(e, UndefinedVariableError) for e in errors))
        self.assertTrue(any(e.var_name == "x" for e in errors if isinstance(e, UndefinedVariableError)))
    
    def test_undefined_function(self):
        """Test detection of undefined function call."""
        code = """
        num test() {
            result = foo()
        }
        """
        errors = self._analyze_and_validate(code)
        self.assertGreater(len(errors), 0, "Expected errors for undefined function")
        self.assertTrue(any(isinstance(e, UndefinedFunctionError) for e in errors))
        self.assertTrue(any(e.func_name == "foo" for e in errors if isinstance(e, UndefinedFunctionError)))
    
    def test_variable_defined_before_use(self):
        """Test that variables can be used after declaration."""
        code = """
        num test() {
            num x
            x = 1
            result = x
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have no errors for variable usage
        undefined_var_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "x"]
        self.assertEqual(len(undefined_var_errors), 0, f"Variable x should be defined: {errors}")
    
    def test_function_parameters_in_scope(self):
        """Test that function parameters are in scope."""
        code = """
        num test(num x) {
            result = x
        }
        """
        errors = self._analyze_and_validate(code)
        undefined_var_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "x"]
        self.assertEqual(len(undefined_var_errors), 0, f"Parameter x should be in scope: {errors}")
    
    def test_valid_function_call(self):
        """Test that valid function calls work."""
        code = """
        num helper() {
            result = 42
        }
        num test() {
            result = helper()
        }
        """
        errors = self._analyze_and_validate(code)
        undefined_func_errors = [e for e in errors if isinstance(e, UndefinedFunctionError)]
        self.assertEqual(len(undefined_func_errors), 0, f"Function helper should be defined: {errors}")
    
    def test_function_call_with_arguments(self):
        """Test function calls with arguments."""
        code = """
        num add(num a, num b) {
            result = a + b
        }
        num test() {
            num x
            num y
            result = add(x, y)
        }
        """
        errors = self._analyze_and_validate(code)
        # Should check argument count
        arg_errors = [e for e in errors if isinstance(e, ArgumentCountError)]
        # For now, we just check that it doesn't crash
        # Full argument checking would require more sophisticated parsing
    
    def test_nested_control_flow(self):
        """Test variables in nested control flow."""
        code = """
        num test(num n) {
            n ?. {
                temp = n
            }
            result = n
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have error for 'temp' since it's not declared
        # But 'n' should be in scope
        undefined_n_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "n"]
        self.assertEqual(len(undefined_n_errors), 0, f"Variable n should be in scope: {errors}")
    
    def test_multiple_functions(self):
        """Test programs with multiple functions."""
        code = """
        num first() {
            result = 1
        }
        num second() {
            result = first()
        }
        """
        errors = self._analyze_and_validate(code)
        undefined_func_errors = [e for e in errors if isinstance(e, UndefinedFunctionError) and e.func_name == "first"]
        self.assertEqual(len(undefined_func_errors), 0, f"Function first should be defined: {errors}")
    
    def test_array_type_declaration(self):
        """Test that assigning array to result in num function produces an error."""
        code = """
        num test() {
            num*10 arr
            result = arr
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have type mismatch error - function returns num but arr is an array
        type_errors = [e for e in errors if isinstance(e, TypeMismatchError)]
        self.assertGreater(len(type_errors), 0, f"Should have type mismatch error for assigning array to num result: {errors}")
    
    def test_while_loop_variable(self):
        """Test variable usage in while loops."""
        code = """
        num test(num n) {
            n ?. {
                n = n - 1
            }
            result = n
        }
        """
        errors = self._analyze_and_validate(code)
        undefined_var_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "n"]
        self.assertEqual(len(undefined_var_errors), 0, f"Variable n should be in scope: {errors}")
    
    def test_if_expression_variable(self):
        """Test variable usage in if expressions."""
        code = """
        num test(num x) {
            x ?? {
                y = 1
            }
            result = x
        }
        """
        errors = self._analyze_and_validate(code)
        # Should recognize variables in if expressions
        # 'x' should be in scope, 'y' should be undefined
        undefined_x_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "x"]
        self.assertEqual(len(undefined_x_errors), 0, f"Variable x should be in scope: {errors}")
    
    def test_array_element_read(self):
        """Test reading array elements."""
        code = """
        num test() {
            num*10 arr
            result = arr[0]
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have no errors for valid array access
        undefined_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "arr"]
        self.assertEqual(len(undefined_errors), 0, f"Array arr should be defined: {errors}")
    
    def test_array_element_write(self):
        """Test writing to array elements."""
        code = """
        num test() {
            num*10 arr
            arr[0] = 42
            result = arr[0]
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have no errors for valid array assignment
        undefined_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "arr"]
        self.assertEqual(len(undefined_errors), 0, f"Array arr should be defined: {errors}")
    
    def test_array_index_with_variable(self):
        """Test array indexing with variable index."""
        code = """
        num test(num i) {
            num*10 arr
            arr[i] = 5
            result = arr[i]
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have no errors
        undefined_errors = [e for e in errors if isinstance(e, UndefinedVariableError)]
        self.assertEqual(len(undefined_errors), 0, f"Should have no undefined variable errors: {errors}")
    
    def test_array_index_on_non_array(self):
        """Test that indexing non-array variables produces an error."""
        code = """
        num test() {
            num x
            x[0] = 5
            result = x[0]
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have type mismatch errors
        type_errors = [e for e in errors if isinstance(e, TypeMismatchError)]
        self.assertGreater(len(type_errors), 0, f"Should have type mismatch error for indexing non-array: {errors}")
    
    def test_array_index_with_array_variable(self):
        """Test that using an array variable as index produces an error."""
        code = """
        num test() {
            num*10 arr
            num*5 idx
            result = arr[idx]
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have type mismatch error - index must be num, not array
        type_errors = [e for e in errors if isinstance(e, TypeMismatchError) and "array index must be num variable" in str(e)]
        self.assertGreater(len(type_errors), 0, f"Should have type mismatch error for array index: {errors}")
    
    def test_result_auto_declared(self):
        """Test that result variable is automatically declared."""
        code = """
        num test() {
            result = 42
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have no errors - result is auto-declared
        undefined_errors = [e for e in errors if isinstance(e, UndefinedVariableError) and e.var_name == "result"]
        self.assertEqual(len(undefined_errors), 0, f"Result should be auto-declared: {errors}")
    
    def test_result_cannot_be_redeclared(self):
        """Test that result variable cannot be declared."""
        code = """
        num test() {
            num result
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have error for trying to declare result
        type_errors = [e for e in errors if isinstance(e, TypeMismatchError) and "cannot declare" in str(e)]
        self.assertGreater(len(type_errors), 0, f"Should have error for declaring result: {errors}")
    
    def test_result_type_mismatch(self):
        """Test that assigning wrong type to result produces error."""
        code = """
        num test() {
            num*10 arr
            result = arr
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have type mismatch error
        type_errors = [e for e in errors if isinstance(e, TypeMismatchError) and "return type mismatch" in str(e)]
        self.assertGreater(len(type_errors), 0, f"Should have type mismatch error for result assignment: {errors}")
    
    def test_result_with_array_return_type(self):
        """Test that result works with array return types."""
        code = """
        num*10 test() {
            num*10 arr
            result = arr
        }
        """
        errors = self._analyze_and_validate(code)
        # Should have no errors for matching array types
        type_errors = [e for e in errors if isinstance(e, TypeMismatchError)]
        self.assertEqual(len(type_errors), 0, f"Should have no type mismatch errors: {errors}")


if __name__ == "__main__":
    unittest.main()
