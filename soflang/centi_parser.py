from pyparsing import *
import string

ParserElement.setDefaultWhitespaceChars(' \t')

TRL, TRR, LPAR, RPAR, LBRACK, RBRACK, LBRACE, RBRACE, COLON, SEMI, COMMA, LN, EQ, SHARP = map(Suppress, "<>()[]{}:;,\n=#")

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
        simple_type = tokens[0].get('simple_type')
        base = simple_type.get('base')
        template_params = simple_type.get('template_params', [])
        size_val = tokens[0].get('size')[0]
        if size_val['type'] == 'integer':
            size_val = int(size_val['value'])
        elif size_val['type'] == 'placeholder':
            pass
        return {'kind': {'dim': 'array', 'size': size_val}, 'base': base, 'type': 'type', 'template_params': template_params}

    def enrich_simple_type(self, tokens):
        base = tokens[0].get('base_type')[0]
        template_params = tokens[0].get('template', {}).get('value', [])
        return {'kind': {'dim': 'simple'}, 'base': base, 'type': 'type', 'template_params': template_params}

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

    def enrich_template(self, tokens):
        params = list(tokens[0])
        return {'value': params}

    def enrich_function_call(self, tokens):
        data = tokens[0]
        func_name = data.get('func_name').get('value')
        params = list(data.get('parameters', []))
        template_params = data.get('template')
        if template_params:
            template_params = template_params[0].get('value', [])

        return {
            'type': 'func_call',
            'identifier': func_name,
            'parameters': params,
            'template_params': template_params
        }

    def enrich_constructor_call(self, tokens):
        data = tokens[0]
        func_name = data.get('clazz_name').get('value')
        params = list(data.get('parameters', []))
        template_params = data.get('template')
        if template_params:
            template_params = template_params[0].get('value', [])

        return {
            'type': 'constructor_call',
            'identifier': func_name,
            'parameters': params,
            'template_params': template_params
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
        template_params = inner.get('template')
        if template_params:
            template_params = template_params[0].get('value', [])

        return {
            'type': 'func_decl',
            'kind': return_type,
            'identifier': func_name,
            'body': body,
            'parameters': parameters,
            'template_params': template_params
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
        template_params = inner.get('template')
        if template_params:
            template_params = template_params[0].get('value', [])

        return {
            'type': 'clazz_decl',
            'identifier': clazz_name,
            'types': types,
            'template_params': template_params
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

    def enrich_value_placeholder(self, tokens):
        return {'type': 'placeholder', 'value': tokens[0]}

    def parse_program(self, text, after_template_resolution: bool = False) -> list:
        library_name = Regex(r'(@/)?[a-z0-9]+(/[a-z0-9]+)*')
        integer = Regex(r'[+-]?\d+')
        if after_template_resolution:
            clazz = Word(string.ascii_uppercase, string.ascii_uppercase + string.ascii_lowercase + string.digits + '_', min=2)
        else:
            clazz = Word(string.ascii_uppercase, string.ascii_uppercase + string.ascii_lowercase + string.digits, min=2)
        clazz.setParseAction(self.make_identifier)
        tplaceholder = Word(string.ascii_uppercase)
        tplaceholder.setParseAction(self.enrich_value_placeholder)
        stemplate = Group(TRL + tplaceholder + TRR)
        stemplate.setParseAction(lambda x: x[0][0])
        if after_template_resolution:
            identifier = Word(string.ascii_lowercase, string.ascii_uppercase + string.ascii_lowercase + string.digits + '_')
        else:
            identifier = Word(string.ascii_lowercase, string.ascii_lowercase + string.digits + '_')
        identifier.setParseAction(self.make_identifier)
        integer.setParseAction(self.make_integer)
        template = Forward()
        simple_type = Group((clazz | stemplate)("base_type") + Optional(template)("template"))
        simple_type.setParseAction(self.enrich_simple_type)
        array_type = Group(simple_type("simple_type") + "*" + (integer | stemplate)("size"))
        array_type.setParseAction(self.enrich_array_type)
        TYPE = array_type | simple_type
        var_decl = locatedExpr(Group(TYPE("type") + identifier("var_name")))
        var_decl.setParseAction(self.enrich_var_decl)
        template <<= Group(TRL + delimitedList((integer | simple_type | tplaceholder))("params") + TRR)
        template.setParseAction(self.enrich_template)
        ptemplate = Group(TRL + delimitedList(tplaceholder)("params") + TRR)
        ptemplate.setParseAction(self.enrich_template)
        line_expr = Forward()
        # TODO: allow consts and exprs as a parameters.
        function_call = Forward()
        constructor_call = Group(clazz("clazz_name") + Optional(template)("template") + LPAR + Optional(delimitedList(identifier))("parameters") + RPAR)
        constructor_call.setParseAction(self.enrich_constructor_call)
        array_index = Group(identifier + LBRACK + (integer | identifier) + RBRACK)
        array_index.setParseAction(self.enrich_array_index)
        field_access = Group(identifier + SHARP + identifier)
        field_access.setParseAction(self.enrich_field_access)
        # Allow this in function call
        atom = integer | function_call | constructor_call | array_index | field_access | identifier | stemplate
        atom.setParseAction(self.make_atom)
        function_call <<= Group(identifier("func_name") + Optional(template)("template") + LPAR + Optional(delimitedList(atom))("parameters") + RPAR)
        function_call.setParseAction(self.enrich_function_call)
        expr = Group(atom + oneOf("* / + - ~ <") + atom)
        expr.setParseAction(self.enrich_binary_expr)
        # unary_expr = Group(oneOf("~") + atom)
        # unary_expr.setParseAction(self.enrich_unary_expr)
        gen_expr = expr | atom
        assignment = locatedExpr(Group((array_index | identifier) + EQ + gen_expr))
        assignment.setParseAction(self.enrich_assignment)
        var_decl_with_assign = locatedExpr(
            Group((TYPE | AUTO)("type") + identifier("var_name") + EQ + gen_expr('value')))
        var_decl_with_assign.setParseAction(self.enrich_var_decl_with_assign)
        comment_expr = Suppress(Regex("//[^\n]*"))
        infunc_exprs = ZeroOrMore(Group(line_expr) + OneOrMore(LN))
        if_expr = locatedExpr(Group(gen_expr + IF + LBRACE + LN + infunc_exprs + RBRACE))
        if_expr.setParseAction(self.enrich_if_expr)
        while_expr = locatedExpr(Group(gen_expr + WHILE + LBRACE + LN + infunc_exprs + RBRACE))
        while_expr.setParseAction(self.enrich_while_expr)
        error_expr = locatedExpr(Group(Keyword("error")))
        error_expr.setParseAction(lambda x: {'type': 'throw_error', 'line': self.get_line(x[0].locn_start)})
        line_expr <<= (assignment | if_expr | var_decl_with_assign | var_decl | while_expr | error_expr | comment_expr)
        line_expr.setParseAction(self.enrich_line_expr)
        func_decl = Group(TYPE("return_type") + identifier("func_name") + Optional(ptemplate)("template") + LPAR + Optional(delimitedList(var_decl))(
            "parameters") + RPAR + LBRACE + LN + Group(ZeroOrMore(Group(line_expr) + LN))("statements") + RBRACE)
        func_decl.setParseAction(self.enrich_func_decl)
        field_decl = Group(identifier("field_name") + SHARP + TYPE("type"))
        field_decl.setParseAction(self.enrich_field_decl)
        clazz_decl = Group(clazz("clazz_name") + Optional(ptemplate)("template") + COLON + delimitedList(field_decl, delim='x')("types"))
        clazz_decl.setParseAction(self.enrich_clazz_decl)
        import_decl = Group(LOAD + library_name("library_name"))
        import_decl.setParseAction(self.enrich_import_decl)
        global_expr = ZeroOrMore(LN) + ZeroOrMore((import_decl | func_decl | clazz_decl | comment_expr) + OneOrMore(LN))
        global_expr.setParseAction(self.enrich_global_expr)
        self.text = text
        return list(global_expr.parse_string(self.text, parse_all=True))


# TODO: arrays with variable size.
# TODO: support templates.


def parse_program(text: str) -> list:
    """Convenience function to parse a program."""
    return Parser().parse_program(text)


if __name__ == '__main__':
    result = Parser().parse_program("""
    Num factorial(Num n, Num i) {
        Num*100 tmp
        n ?? {
            n = n + 0
        }
        tmp[0] = tmp[1]
        result = 1
        n ...? {
            result = result * n
            n = n - 1
        }
    }
    Num main() {
        Num a
        a = 5
        result = factorial(a, b)
    }
    """)

    result = Parser().parse_program("""
    Num main() {
        result = 54
    }
    """)

    import json

    print(json.dumps(result, indent=2, default=str))
