from pyparsing import *
import string

ParserElement.setDefaultWhitespaceChars(' \t')

LPAR, RPAR, LBRACK, RBRACK, LBRACE, RBRACE, SEMI, COMMA, LN, EQ = map(Suppress, "()[]{};,\n=")

NUM, IF, WHILE = map(Keyword, "num ?? ?.".split())


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
        size_val = tokens[0].get('size').get('value')
        return {'kind': {'dim': 'array', 'size': int(size_val)}, 'base': 'num'}

    def enrich_simple_type(self, tokens):
        return {'kind': {'dim': 'simple'}, 'base': 'num'}

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

    def enrich_array_index(self, tokens):
        data = tokens[0]
        var_name = data[0].get('value')
        index = data[1]

        return {
            'type': 'array_index',
            'var_name': var_name,
            'index': index
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

    def enrich_global_expr(self, tokens):
        funcs = [item for item in tokens]
        return funcs

    def parse_program(self, text) -> list:
        integer = Regex(r'[+-]?\d+')
        identifier = Word(string.ascii_lowercase)
        identifier.setParseAction(self.make_identifier)
        integer.setParseAction(self.make_integer)
        array_type = Group(NUM("base_type") + "*" + integer("size"))
        array_type.setParseAction(self.enrich_array_type)
        simple_type = NUM("base_type")
        simple_type.setParseAction(self.enrich_simple_type)
        TYPE = array_type | simple_type
        var_decl = locatedExpr(Group(TYPE("type") + identifier("var_name")))
        var_decl.setParseAction(self.enrich_var_decl)
        line_expr = Forward()
        infunc_exprs = Forward()
        # TODO: allow consts and exprs as a parameters.
        function_call = Group(identifier("func_name") + LPAR + Optional(delimitedList(identifier))("parameters") + RPAR)
        function_call.setParseAction(self.enrich_function_call)
        array_index = Group(identifier + LBRACK + (integer | identifier) + RBRACK)
        array_index.setParseAction(self.enrich_array_index)
        # Allow this in function call
        atom = integer | function_call | array_index | identifier
        atom.setParseAction(self.make_atom)
        expr = Group(atom + oneOf("* / + -") + atom)
        expr.setParseAction(self.enrich_binary_expr)
        unary_expr = Group(oneOf("~") + atom)
        unary_expr.setParseAction(self.enrich_unary_expr)
        gen_expr = expr | unary_expr | atom
        assignment = locatedExpr(Group((array_index | identifier) + EQ + gen_expr))
        assignment.setParseAction(self.enrich_assignment)
        infunc_exprs <<= ZeroOrMore(Group(line_expr) + OneOrMore(LN))
        if_expr = locatedExpr(Group(gen_expr + IF + LBRACE + LN + infunc_exprs + RBRACE))
        if_expr.setParseAction(self.enrich_if_expr)
        while_expr = locatedExpr(Group(gen_expr + WHILE + LBRACE + LN + infunc_exprs + RBRACE))
        while_expr.setParseAction(self.enrich_while_expr)
        line_expr <<= (assignment | if_expr | var_decl | while_expr)
        line_expr.setParseAction(self.enrich_line_expr)
        func_decl = Group(TYPE("return_type") + identifier("func_name") + LPAR + Optional(delimitedList(var_decl))("parameters") + RPAR + LBRACE + LN + Group(ZeroOrMore(Group(line_expr) + LN))("statements") + RBRACE)
        func_decl.setParseAction(self.enrich_func_decl)
        global_expr = ZeroOrMore(LN) + ZeroOrMore(func_decl + OneOrMore(LN))
        global_expr.setParseAction(self.enrich_global_expr)
        self.text = text
        return list(global_expr.parse_string(self.text, parse_all=True))


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
