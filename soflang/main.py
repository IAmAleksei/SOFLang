import json
from typing import List

from soflang import centi_parser, preprocess
from soflang.analyzer import BonAnalyzer, Function
from soflang.asm import (
    parse_asm, translate,
)
from soflang.binarify import decode_binary_asm, encode_binary_asm
from soflang.debugger import run_debugger, DebuggerWithCPU
from soflang.lvm import LionVM
from soflang.preprocess import recursive_parse
from soflang.validator import MilliValidator


def resolve(ifile):
    assert ifile.endswith('.sofl')
    ofile = ifile[:-5] + '_pp.sofl'
    _, text = preprocess.parse_with_imports_resolution(ifile)
    with open(ofile, 'w') as f:
        f.write(text)


def parse(ifile: str):
    assert ifile.endswith('.sofl')
    ofile = ifile[:-5] + '.json'
    with open(ifile, 'r') as f:
        text = "".join(f.readlines())
    out = centi_parser.Parser().parse_program(text, after_template_resolution=True)
    with open(ofile, 'w') as f:
        json.dump(out, f, indent=1, default=str)


def analyze(ifile: str) -> List[Function]:
    a = BonAnalyzer()
    with open(ifile, 'r') as f:
        text = json.load(f)
    a.analyze(text)
    return a.get_functions()


def validator(functions: List[Function]) -> bool:
    v = MilliValidator()
    errors = v.validate(functions)
    if errors:
        print("Found errors:")
        for err in errors:
            print("-", err)
        return False
    return True


def asm(functions: List[Function], ofile: str):
    instructions = translate(functions, {}).asm_instructions
    with open(ofile, 'w') as f:
        for i in instructions:
            f.write(f"{i.__str__()}\n")


def binarify_asm(ifile: str):
    assert ifile.endswith('.sasm')
    ofile = ifile[:-5] + '.bsasm'
    with open(ifile, 'r') as f:
        instructions = parse_asm(f.readlines())
    bs, _ = encode_binary_asm(instructions)
    with open(ofile, 'wb') as f:
        f.write(bs)


def execute(ifile: str):
    if ifile.endswith('.sasm'):
        with open(ifile, 'r') as f:
            instructions = parse_asm(f.readlines())
        LionVM().run(instructions)
    elif ifile.endswith('.bsasm'):
        with open(ifile, 'rb') as f:
            bcode = f.read()
        LionVM().run_binary(bcode)


def compile_and_run(ifile):
    parsed, _ = preprocess.parse_with_imports_resolution(ifile)

    analyzer = BonAnalyzer()
    analyzer.analyze(parsed)

    errors = MilliValidator().validate(analyzer.get_functions(), analyzer.classes)
    if errors:
        print("Found errors:")
        for err in errors:
            print("-", err)
        return

    asm_instructions = translate(analyzer.get_functions(), analyzer.classes, with_debug=False).asm_instructions
    bs, _ = encode_binary_asm(asm_instructions)
    LionVM().run_with_cpu_simulation(bs)


def compile_and_debug(ifile):
    parsed, text = preprocess.parse_with_imports_resolution(ifile)

    analyzer = BonAnalyzer()
    analyzer.analyze(parsed)

    errors = MilliValidator().validate(analyzer.get_functions(), analyzer.classes)
    if errors:
        print("Found errors:")
        for err in errors:
            print("-", err)
        return

    enriched_result = translate(analyzer.get_functions(), analyzer.classes, with_debug=True)

    debugger = DebuggerWithCPU(enriched_result, text.split('\n'))
    run_debugger(debugger)


def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="S0FLang toolchain")
    subparsers = arg_parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser("parse", help="Parse source into JSON")
    parse_parser.add_argument("input", help="Input source file")

    analyze_parser = subparsers.add_parser(
        "analyze-validate-translate",
        help="Analyze parsed JSON, validate, and emit assembly instructions",
    )
    analyze_parser.add_argument("input", help="Input JSON file")

    execute_parser = subparsers.add_parser(
        "execute", help="Execute assembly instructions with the LionVM"
    )
    execute_parser.add_argument("input", help="Input assembly file")

    execute_parser = subparsers.add_parser(
        "binarify", help="Compacts input text assembler file to binary assembler"
    )
    execute_parser.add_argument("input", help="Input assembly file")

    execute_parser = subparsers.add_parser(
        "compile-and-run", help="Perform all steps - compile, analyze, translate, run"
    )
    execute_parser.add_argument("input", help="Input .sofl file")

    execute_parser = subparsers.add_parser(
        "compile-and-debug", help="Perform all steps - compile, analyze, translate, debug"
    )
    execute_parser.add_argument("input", help="Input .sofl file")

    args = arg_parser.parse_args()

    if args.command == "parse":
        parse(args.input)
    elif args.command == "analyze-validate-translate":
        assert args.input.endswith('.json')
        ofile = args.input[:-5] + '.sasm'
        functions = analyze(args.input)
        success = validator(functions)
        if success:
            asm(functions, ofile)
    elif args.command == "execute":
        execute(args.input)
    elif args.command == "binarify":
        binarify_asm(args.input)
    elif args.command == "compile-and-run":
        compile_and_run(args.input)
    elif args.command == "compile-and-debug":
        compile_and_debug(args.input)


if __name__ == '__main__':
    main()
