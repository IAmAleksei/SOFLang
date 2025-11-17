from pyparsing import *
import string

ParserElement.setDefaultWhitespaceChars(' \t')

LPAR, RPAR, LBRACK, RBRACK, LBRACE, RBRACE, COLON, SEMI, COMMA, LN, EQ, SHARP = map(Suppress, "()[]{}:;,\n=#")

IF, WHILE, AUTO, LOAD = map(Keyword, "?? ...? auto load".split())


class Parser:
    def __init__(self):
        self.text = ""

    def get_line(self, pos) -> int:
        return self.text.count('\n', 0, pos)

    def make_identifier(self, tokens):
        return {'type': 'identifier', 'value': str(tokens[0])}

    def make_integer(self, tokens):
        return {'type': 'integer', 'value': int(tokens[0])}

    def enrich_array_type(self, tokens):
        data = tokens[0]
        base = data.get('base_type').get('value')
        size_val = data.get('size').get('value')
        return {'kind': {'dim': 'array', 'size': int(size_val)}, 'base': base}

    def enrich_simple_type(self, tokens):
        base = tokens[0]
        return {'kind': {'dim': 'simple'}, 'base': base}

    def enrich_var_decl(self, tokens):
        start_symbol = tokens[0].locn_start
        inner = tokens[0].get('value')
        type_info = inner.get('type')[0]
        var_name = inner.get('var_name').get('value')

        return {
            'kind': type_info,
            'type': 'var_decl',
            'identifier': var_name,
            'line': self.get_line(start_symbol)
        }

    def enrich_function_call(self, tokens):
        data = tokens[0]
        func_name = data.get('func_name').get('value')
        params = list(data.get('parameters', []))

        return {
            'type': 'func_call',
            'identifier': func_name,
            'parameters': params
        }

    def enrich_constructor_call(self, tokens):
        data = tokens[0]
        func_name = data.get('clazz_name').get('value')
        params = list(data.get('parameters', []))

        return {
            'type': 'constructor_call',
            'identifier': func_name,
            'parameters': params
        }

    def enrich_array_index(self, tokens):
        data = tokens[0]
        var_name = data[0].get('value')
        index = data[1]

        return {
            'type': 'array_index',
            'var_name': var_name,
            'index': index
        }

    def enrich_field_access(self, tokens):
        data = tokens[0]
        var_name = data[0].get('value')
        field = data[1].get('value')

        return {
            'type': 'field_access',
            'var_name': var_name,
            'field': field
        }

    def make_atom(self, tokens):
        return tokens[0]

    def enrich_binary_expr(self, tokens):
        token_list = list(tokens[0])

        left = token_list[0]
        op = str(token_list[1])
        right = token_list[2]

        return {
            'type': 'gen_expr',
            'left': left,
            'op': op,
            'right': right
        }

    def enrich_unary_expr(self, tokens):
        token_list = list(tokens[0])

        op = str(token_list[0])
        inner = token_list[1]

        return {
            'type': 'un_expr',
            'op': op,
            'inner': inner
        }

    def enrich_assignment(self, tokens):
        start_symbol = tokens[0].locn_start
        data = tokens[0].get('value')
        left = data[0]
        right = data[1]
        return {
            'type': 'assignment',
            'dest': left,
            'value': right,
            'line': self.get_line(start_symbol)
        }

    def enrich_var_decl_with_assign(self, tokens):
        start_symbol = tokens[0].locn_start
        data = tokens[0].get('value')
        right = data.get('value')[0]
        type_info = data.get('type')[0]
        var_name = data.get('var_name').get('value')

        return {
            'kind': type_info,
            'type': 'var_decl_with_assign',
            'identifier': var_name,
            'value': right,
            'line': self.get_line(start_symbol)
        }

    def enrich_if_expr(self, tokens):
        start_symbol = tokens[0].locn_start
        data = tokens[0].get('value')
        condition = data[0]
        body = [dt[0] for dt in data[2:]]

        return {
            'type': 'if_expr',
            'condition': condition,
            'body': body,
            'line': self.get_line(start_symbol)
        }

    def enrich_while_expr(self, tokens):
        start_symbol = tokens[0].locn_start
        data = tokens[0].get('value')
        condition = data[0]
        body = [dt[0] for dt in data[2:]]

        return {
            'type': 'while_expr',
            'condition': condition,
            'body': body,
            'line': self.get_line(start_symbol)
        }

    def enrich_line_expr(self, tokens):
        return tokens[0]

    def enrich_func_decl(self, tokens):
        inner = tokens[0]
        return_type = inner.get('return_type')[0]
        func_name = inner.get('func_name').get('value')
        statements = inner.get('statements', [])
        parameters = inner.get('parameters', [])

        body = [item[0] for item in statements]

        parameters = [param for param in parameters]

        return {
            'type': 'func_decl',
            'kind': return_type,
            'identifier': func_name,
            'body': body,
            'parameters': parameters
        }

    def enrich_field_decl(self, tokens):
        inner = tokens[0]

        field_name = inner.get('field_name').get('value')
        type = inner.get('type')[0]

        return {
            'type': 'field_decl',
            'identifier': field_name,
            'kind': type
        }

    def enrich_clazz_decl(self, tokens):
        inner = tokens[0]

        clazz_name = inner.get('clazz_name').get('value')
        types = inner.get('types')
        types = [t for t in types]

        return {
            'type': 'clazz_decl',
            'identifier': clazz_name,
            'types': types
        }

    def enrich_import_decl(self, tokens):
        inner = tokens[0]

        library_name = inner.get('library_name')

        return {
            'type': 'import_decl',
            'identifier': library_name
        }

    def enrich_global_expr(self, tokens):
        funcs_and_clazzes = [item for item in tokens]
        return funcs_and_clazzes

    def parse_program(self, text) -> list:
        library_name = Regex(r'(@/)?[a-z0-9]+(/[a-z0-9]+)*')
        integer = Regex(r'[+-]?\d+')
        clazz = Word(string.ascii_uppercase, string.ascii_lowercase)
        clazz.setParseAction(self.make_identifier)
        identifier = Word(string.ascii_lowercase, string.ascii_lowercase + string.digits + '_')
        identifier.setParseAction(self.make_identifier)
        integer.setParseAction(self.make_integer)
        array_type = Group(clazz("base_type") + "*" + integer("size"))
        array_type.setParseAction(self.enrich_array_type)
        simple_type = clazz("base_type")
        simple_type.setParseAction(self.enrich_simple_type)
        TYPE = array_type | simple_type
        var_decl = locatedExpr(Group(TYPE("type") + identifier("var_name")))
        var_decl.setParseAction(self.enrich_var_decl)
        line_expr = Forward()
        # TODO: allow consts and exprs as a parameters.
        function_call = Group(identifier("func_name") + LPAR + Optional(delimitedList(identifier))("parameters") + RPAR)
        function_call.setParseAction(self.enrich_function_call)
        constructor_call = Group(clazz("clazz_name") + LPAR + Optional(delimitedList(identifier))("parameters") + RPAR)
        constructor_call.setParseAction(self.enrich_constructor_call)
        array_index = Group(identifier + LBRACK + (integer | identifier) + RBRACK)
        array_index.setParseAction(self.enrich_array_index)
        field_access = Group(identifier + SHARP + identifier)
        field_access.setParseAction(self.enrich_field_access)
        # Allow this in function call
        atom = integer | function_call | constructor_call | array_index | field_access | identifier
        atom.setParseAction(self.make_atom)
        expr = Group(atom + oneOf("* / + -") + atom)
        expr.setParseAction(self.enrich_binary_expr)
        unary_expr = Group(oneOf("~") + atom)
        unary_expr.setParseAction(self.enrich_unary_expr)
        gen_expr = expr | unary_expr | atom
        assignment = locatedExpr(Group((array_index | identifier) + EQ + gen_expr))
        assignment.setParseAction(self.enrich_assignment)
        var_decl_with_assign = locatedExpr(
            Group((TYPE | AUTO)("type") + identifier("var_name") + EQ + gen_expr('value')))
        var_decl_with_assign.setParseAction(self.enrich_var_decl_with_assign)
        infunc_exprs = ZeroOrMore(Group(line_expr) + OneOrMore(LN))
        if_expr = locatedExpr(Group(gen_expr + IF + LBRACE + LN + infunc_exprs + RBRACE))
        if_expr.setParseAction(self.enrich_if_expr)
        while_expr = locatedExpr(Group(gen_expr + WHILE + LBRACE + LN + infunc_exprs + RBRACE))
        while_expr.setParseAction(self.enrich_while_expr)
        error_expr = locatedExpr(Group(Keyword("error")))
        error_expr.setParseAction(lambda x: {'type': 'throw_error', 'line': self.get_line(x[0].locn_start)})
        line_expr <<= (assignment | if_expr | var_decl_with_assign | var_decl | while_expr | error_expr)
        line_expr.setParseAction(self.enrich_line_expr)
        func_decl = Group(TYPE("return_type") + identifier("func_name") + LPAR + Optional(delimitedList(var_decl))(
            "parameters") + RPAR + LBRACE + LN + Group(ZeroOrMore(Group(line_expr) + LN))("statements") + RBRACE)
        func_decl.setParseAction(self.enrich_func_decl)
        field_decl = Group(identifier("field_name") + SHARP + TYPE("type"))
        field_decl.setParseAction(self.enrich_field_decl)
        clazz_decl = Group(clazz("clazz_name") + COLON + delimitedList(field_decl, delim='x')("types"))
        clazz_decl.setParseAction(self.enrich_clazz_decl)
        import_decl = Group(LOAD + library_name("library_name"))
        import_decl.setParseAction(self.enrich_import_decl)
        global_expr = ZeroOrMore(LN) + ZeroOrMore((import_decl | func_decl | clazz_decl) + OneOrMore(LN))
        global_expr.setParseAction(self.enrich_global_expr)
        self.text = text
        return list(global_expr.parse_string(self.text, parse_all=True))


# TODO: arrays with variable size.
# TODO: support templates.
# TODO: support comments


def parse_program(text: str) -> list:
    """Convenience function to parse a program."""
    return Parser().parse_program(text)


if __name__ == '__main__':
    result = Parser().parse_program("""
    num factorial(num n, num i) {
        num*100 tmp
        n ?? {
            n = n + 0
        }
        tmp[0] = tmp[1]
        result = 1
        n ?. {
            result = result * n
            n = n - 1
        }
    }
    num main() {
        num a
        a = 5
        result = factorial(a, b)
    }
    """)

    result = Parser().parse_program("""
    num main() {
        result = 54
    }
    """)

    import json

    print(json.dumps(result, indent=2, default=str))
