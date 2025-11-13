### Scarcely Object-Oriented and Functional Language

Trivial programming language with its own syntax and issues.

Tools:

- [CentiParser](soflang/centi_parser.py) - parser, transforming `.sofl` file to parsed`.json` or Python-dict.
- [BonAnalyzer](soflang/analyzer.py) - loader of parser output with minor verification.
- [MilliValidator](soflang/validator.py) - pre-compile checker of the code correctness.
- [TinyTranslator](soflang/asm.py) - translator from the parsed `.sofl` to `.sasm` - SOFLang assembler.
- [LionVM](soflang/lvm.py) - runner for assembler.
- [Debugger](soflang/debugger.py) - interactive debugger for assembler, displaying source code and variables

How to run:

```bash
python3 soflang.main compile-and-run examples/for_fib.sofl
```

How to debug:

```bash
python3 soflang.main compile-and-debug examples/rec_fib.sofl
```
