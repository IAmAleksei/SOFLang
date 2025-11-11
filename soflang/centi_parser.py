from pyparsing import *
import string

ParserElement.setDefaultWhitespaceChars(' \t')

LPAR, RPAR, LBRACK, RBRACK, LBRACE, RBRACE, SEMI, COMMA, LN, EQ = map(Suppress, "()[]{};,\n=")

NUM, IF, WHILE = map(Keyword, "num ?? ?.".split())

integer = Regex(r'[+-]?\d+')
identifier = Word(string.ascii_lowercase)


def make_identifier(tokens):
    return {'type': 'identifier', 'value': str(tokens[0])}


def make_integer(tokens):
    return {'type': 'integer', 'value': int(tokens[0])}


identifier.setParseAction(make_identifier)
integer.setParseAction(make_integer)


def enrich_array_type(tokens):
    size_val = tokens[0].get('size').get('value')
    return {
        'kind': {'dim': 'array', 'size': int(size_val)},
        'base': 'num'
    }


def enrich_simple_type(tokens):
    return {
        'kind': {'dim': 'simple'},
        'base': 'num'
    }


array_type = Group(NUM("base_type") + "*" + integer("size"))
array_type.setParseAction(enrich_array_type)

simple_type = NUM("base_type")
simple_type.setParseAction(enrich_simple_type)

TYPE = array_type | simple_type


def enrich_var_decl(tokens):
    inner = tokens[0]
    type_info = inner.get('type')[0]
    var_name = inner.get('var_name').get('value')

    return {
        'kind': type_info,
        'type': 'var_decl',
        'identifier': var_name
    }


var_decl = Group(TYPE("type") + identifier("var_name"))
var_decl.setParseAction(enrich_var_decl)

line_expr = Forward()
infunc_exprs = Forward()


def enrich_function_call(tokens):
    data = tokens[0]
    func_name = data.get('func_name').get('value')
    params = list(data.get('parameters', []))

    return {
        'type': 'func_call',
        'identifier': func_name,
        'parameters': params
    }

# TODO: allow consts and exprs as a parameters.
function_call = Group(identifier("func_name") + LPAR + Optional(delimitedList(identifier))("parameters") + RPAR)
function_call.setParseAction(enrich_function_call)


def enrich_array_index(tokens):
    data = tokens[0]
    var_name = data[0].get('value')
    index = data[1]

    return {
        'type': 'array_index',
        'var_name': var_name,
        'index': index
    }


array_index = Group(identifier + LBRACK + (integer | identifier) + RBRACK)
array_index.setParseAction(enrich_array_index)


def make_atom(tokens):
    return tokens[0]


# Allow this in function call
atom = integer | function_call | array_index | identifier
atom.setParseAction(make_atom)


def enrich_binary_expr(tokens):
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


expr = Group(atom + oneOf("* / + -") + atom)
expr.setParseAction(enrich_binary_expr)


def enrich_unary_expr(tokens):
    token_list = list(tokens[0])

    op = str(token_list[0])
    inner = token_list[1]

    return {
        'type': 'un_expr',
        'op': op,
        'inner': inner
    }


unary_expr = Group(oneOf("~") + atom)
unary_expr.setParseAction(enrich_unary_expr)

gen_expr = expr | unary_expr | atom


def enrich_assignment(tokens):
    data = tokens[0]
    left = data[0]
    right = data[1]
    return {
        'type': 'assignment',
        'dest': left,
        'value': right
    }


assignment = Group((array_index | identifier) + EQ + gen_expr)
assignment.setParseAction(enrich_assignment)


def enrich_if_expr(tokens):
    data = tokens[0]
    condition = data[0]
    body = [dt[0] for dt in data[2:]]

    return {
        'type': 'if_expr',
        'condition': condition,
        'body': body
    }


def enrich_while_expr(tokens):
    data = tokens[0]
    condition = data[0]
    body = [dt[0] for dt in data[2:]]

    return {
        'type': 'while_expr',
        'condition': condition,
        'body': body
    }


infunc_exprs <<= ZeroOrMore(Group(line_expr) + OneOrMore(LN))

if_expr = Group(gen_expr + IF + LBRACE + LN + infunc_exprs + RBRACE)
if_expr.setParseAction(enrich_if_expr)

while_expr = Group(gen_expr + WHILE + LBRACE + LN + infunc_exprs + RBRACE)
while_expr.setParseAction(enrich_while_expr)

line_expr <<= (assignment | if_expr | var_decl | while_expr)


def enrich_line_expr(tokens):
    return tokens[0]


line_expr.setParseAction(enrich_line_expr)


def enrich_func_decl(tokens):
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


func_decl = Group(TYPE("return_type") + identifier("func_name") + LPAR + Optional(delimitedList(var_decl))("parameters") + RPAR + LBRACE + LN + Group(ZeroOrMore(Group(line_expr) + LN))("statements") + RBRACE)
func_decl.setParseAction(enrich_func_decl)


def enrich_global_expr(tokens):
    funcs = [item for item in tokens]
    return funcs


global_expr = ZeroOrMore(LN) + ZeroOrMore(func_decl + OneOrMore(LN))
global_expr.setParseAction(enrich_global_expr)


def parse_program(text) -> list:
    return list(global_expr.parse_string(text, parse_all=True))


if __name__ == '__main__':
    result = parse_program("""
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

    result = parse_program("""
    num main() {
        result = 54
    }
    """)

    import json

    print(json.dumps(result, indent=2, default=str))
