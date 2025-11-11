import json
from typing import List

from soflang import centi_parser
from soflang.analyzer import BonAnalyzer, Function
from soflang.asm import (
    TinyTranslator,
    parse_asm,
)
from soflang.lvm import LionVM
from soflang.validator import MilliValidator


def parse(ifile: str, ofile: str):
    with open(ifile, 'r') as f:
        text = "".join(f.readlines())
    out = centi_parser.parse_program(text)
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
    t = TinyTranslator()
    instructions = t.translate(functions)
    with open(ofile, 'w') as f:
        for i in instructions:
            f.write(f"{i.__str__()}\n")


def execute(ifile):
    with open(ifile, 'r') as f:
        instructions = parse_asm(f.readlines())
    l = LionVM()
    l.run(instructions)


def compile_and_run(ifile):
    with open(ifile, 'r') as f:
        text = "".join(f.readlines())
    parsed = centi_parser.parse_program(text)

    analyzed = BonAnalyzer().analyze(parsed)

    errors = MilliValidator().validate(analyzed)
    if errors:
        print("Found errors:")
        for err in errors:
            print("-", err)
        return

    asm_instructions = TinyTranslator().translate(analyzed)

    LionVM().run(asm_instructions)


def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="S0FLang toolchain")
    subparsers = arg_parser.add_subparsers(dest="command", required=True)

    parse_parser = subparsers.add_parser("parse", help="Parse source into JSON")
    parse_parser.add_argument("input", help="Input source file")
    parse_parser.add_argument("output", help="Output JSON file")

    analyze_parser = subparsers.add_parser(
        "analyze-validate-translate",
        help="Analyze parsed JSON, validate, and emit assembly instructions",
    )
    analyze_parser.add_argument("input", help="Input JSON file")
    analyze_parser.add_argument("output", help="Output assembly file")

    execute_parser = subparsers.add_parser(
        "execute", help="Execute assembly instructions with the LionVM"
    )
    execute_parser.add_argument("input", help="Input assembly file")

    execute_parser = subparsers.add_parser(
        "compile-and-run", help="Perform all steps - compile, analyze, translate, run"
    )
    execute_parser.add_argument("input", help="Input .sofl file")

    args = arg_parser.parse_args()

    if args.command == "parse":
        parse(args.input, args.output)
    elif args.command == "analyze-validate-translate":
        functions = analyze(args.input)
        success = validator(functions)
        if success:
            asm(functions, args.output)
    elif args.command == "execute":
        execute(args.input)
    elif args.command == "compile-and-run":
        compile_and_run(args.input)


if __name__ == '__main__':
    main()
