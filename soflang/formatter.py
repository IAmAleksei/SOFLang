class Formatter:
    def __init__(self, indent_size=4):
        self.indent_size = indent_size
    
    def format_type(self, type_info):
        """Format a type (simple or array) or 'auto' keyword"""
        # Handle 'auto' keyword (string) vs type dict
        if isinstance(type_info, str):
            return type_info  # It's the 'auto' keyword
        elif isinstance(type_info, dict):
            if type_info['kind']['dim'] == 'array':
                base = type_info['base']
                if isinstance(base, dict):
                    base = self.format_expression(base)
                size = type_info['kind']['size']
                return f"{base}*{size}"
            else:  # simple
                base = type_info['base']
                if isinstance(base, dict):
                    base = self.format_expression(base)
                return base
        else:
            raise ValueError(f"Unknown type_info format: {type_info}")
    
    def format_expression(self, expr):
        """Format an expression (identifier, integer, function call, etc.)"""
        expr_type = expr['type']
        
        if expr_type == 'identifier':
            return expr['value']
        elif expr_type == 'integer':
            return str(expr['value'])
        elif expr_type == 'func_call':
            func_name = expr['identifier']
            params = [self.format_expression(p) for p in expr['parameters']]
            return f"{func_name}({', '.join(params)})"
        elif expr_type == 'constructor_call':
            clazz_name = expr['identifier']
            params = [self.format_expression(p) for p in expr['parameters']]
            return f"{clazz_name}({', '.join(params)})"
        elif expr_type == 'array_index':
            var_name = expr['var_name']
            index = self.format_expression(expr['index'])
            return f"{var_name}[{index}]"
        elif expr_type == 'field_access':
            var_name = expr['var_name']
            field = expr['field']
            return f"{var_name}#{field}"
        elif expr_type == 'gen_expr':
            left = self.format_expression(expr['left'])
            op = expr['op']
            right = self.format_expression(expr['right'])
            return f"{left} {op} {right}"
        elif expr_type == 'un_expr':
            op = expr['op']
            inner = self.format_expression(expr['inner'])
            return f"{op}{inner}"
        else:
            raise ValueError(f"Unknown expression type: {expr_type}")
    
    def format_statement(self, stmt, indent_level=0):
        """Format a statement (var_decl, assignment, if_expr, etc.)"""
        indent = ' ' * (indent_level * self.indent_size)
        stmt_type = stmt['type']
        
        if stmt_type == 'var_decl':
            type_str = self.format_type(stmt['kind'])
            var_name = stmt['identifier']
            return f"{indent}{type_str} {var_name}"
        elif stmt_type == 'var_decl_with_assign':
            type_str = self.format_type(stmt['kind'])
            var_name = stmt['identifier']
            value = self.format_expression(stmt['value'])
            return f"{indent}{type_str} {var_name} = {value}"
        elif stmt_type == 'assignment':
            dest = self.format_expression(stmt['dest'])
            value = self.format_expression(stmt['value'])
            return f"{indent}{dest} = {value}"
        elif stmt_type == 'if_expr':
            condition = self.format_expression(stmt['condition'])
            body = stmt['body']
            body_str = '\n'.join([self.format_statement(s, indent_level + 1) for s in body])
            return f"{indent}{condition} ?? {{\n{body_str}\n{indent}}}"
        elif stmt_type == 'while_expr':
            condition = self.format_expression(stmt['condition'])
            body = stmt['body']
            body_str = '\n'.join([self.format_statement(s, indent_level + 1) for s in body])
            return f"{indent}{condition} ...? {{\n{body_str}\n{indent}}}"
        elif stmt_type == 'throw_error':
            return f"{indent}error"
        else:
            raise ValueError(f"Unknown statement type: {stmt_type}")
    
    def format_import_decl(self, decl):
        """Format an import declaration"""
        lib_name = decl['identifier']
        return f"load {lib_name}"
    
    def format_func_decl(self, decl):
        """Format a function declaration"""
        return_type = self.format_type(decl['kind'])
        func_name = decl['identifier']
        
        # Format parameters
        params = []
        for param in decl['parameters']:
            type_str = self.format_type(param['kind'])
            param_name = param['identifier']
            params.append(f"{type_str} {param_name}")
        params_str = ', '.join(params)
        
        # Format body
        body = decl['body']
        body_str = '\n'.join([self.format_statement(s, 1) for s in body])
        if body_str:
            return f"{return_type} {func_name}({params_str}) {{\n{body_str}\n}}"
        else:
            return f"{return_type} {func_name}({params_str}) {{\n}}"
    
    def format_clazz_decl(self, decl):
        """Format a class declaration"""
        clazz_name = decl['identifier']
        
        # Format fields
        fields = []
        for field in decl['types']:
            field_name = field['identifier']
            type_str = self.format_type(field['kind'])
            fields.append(f"{field_name}#{type_str}")
        fields_str = ' x '.join(fields)
        
        return f"{clazz_name}: {fields_str}"
    
    def format(self, parsed_text: list) -> str:
        """Format a list of parsed top-level declarations"""
        if not parsed_text:
            return ""
        
        result = []
        for item in parsed_text:
            item_type = item['type']
            
            if item_type == 'import_decl':
                result.append(self.format_import_decl(item))
            elif item_type == 'func_decl':
                result.append(self.format_func_decl(item))
            elif item_type == 'clazz_decl':
                result.append(self.format_clazz_decl(item))
            else:
                raise ValueError(f"Unknown declaration type: {item_type}")
        
        # Parser expects: ZeroOrMore(LN) + ZeroOrMore((decl) + OneOrMore(LN))
        # So we need a leading newline and trailing newlines after each declaration
        # Join declarations with newlines, add leading newline, and ensure trailing newline
        formatted = '\n' + '\n'.join(result)
        if formatted and not formatted.endswith('\n'):
            formatted += '\n'
        return formatted
