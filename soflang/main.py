import json
from typing import List

from soflang import centi_parser
from soflang.analyzer import BonAnalyzer, Function
from soflang.asm import (
    parse_asm, translate,
)
from soflang.binarify import decode_binary_asm, encode_binary_asm
from soflang.debugger import run_debugger
from soflang.lvm import LionVM
from soflang.validator import MilliValidator


def parse(ifile: str):
    assert ifile.endswith('.sofl')
    ofile = ifile[:-5] + '.json'
    with open(ifile, 'r') as f:
        text = "".join(f.readlines())
    out = centi_parser.Parser().parse_program(text)
    with open(ofile, 'w') as f:
        json.dump(out, f, indent=1, default=str)


def analyze(ifile: str) -> List[Function]:
    a = BonAnalyzer()
    with open(ifile, 'r') as f:
        text = json.load(f)
    return a.analyze(text)


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
    instructions = translate(functions).asm_instructions
    with open(ofile, 'w') as f:
        for i in instructions:
            f.write(f"{i.__str__()}\n")


def binarify_asm(ifile: str):
    assert ifile.endswith('.sasm')
    ofile = ifile[:-5] + '.bsasm'
    with open(ifile, 'r') as f:
        instructions = parse_asm(f.readlines())
    bs = encode_binary_asm(instructions)
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
    with open(ifile, 'r') as f:
        text = "".join(f.readlines())
    parsed = centi_parser.Parser().parse_program(text)

    analyzed = BonAnalyzer().analyze(parsed)

    errors = MilliValidator().validate(analyzed)
    if errors:
        print("Found errors:")
        for err in errors:
            print("-", err)
        return

    asm_instructions = translate(analyzed, with_debug=False).asm_instructions

    LionVM().run(asm_instructions)


def compile_and_debug(ifile):
    with open(ifile, 'r') as f:
        lines = f.readlines()
    text = "".join(lines)
    parsed = centi_parser.Parser().parse_program(text)

    analyzed = BonAnalyzer().analyze(parsed)

    errors = MilliValidator().validate(analyzed)
    if errors:
        print("Found errors:")
        for err in errors:
            print("-", err)
        return

    enriched_result = translate(analyzed, with_debug=True)
    run_debugger(enriched_result, lines)


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
