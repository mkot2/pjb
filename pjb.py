import argparse
import os
import re
import sys
import time

copyloopMap = []
copyloopMulMap = []
setcellMap = []

def mulcpyLoopSearch(group: str) -> str:
    numOfCopies = 0
    offset = 0
    if group.count(">") - group.count("<") == 0:
        for x in re.findall(r"[<>]+\++", group):
            offset += -x.count("<")+x.count(">")
            copyloopMap.append(offset)
            copyloopMulMap.append(x.count("+"))
            numOfCopies += 1
        return f"{'M' * numOfCopies}C"
    else:
        return group

def setCell(group: str) -> str:
    setcellMap.append(group.count("+"))
    return "S"

def noopRemove(group: str, char1: str, char2: str) -> str:
    total: int = group.count(char1) - group.count(char2)
    return char1 * abs(total) if total > 0 else char2 * abs(total)

def main() -> None:
    parser = argparse.ArgumentParser(description="Brainfuck-to-C JIT")
    parser.add_argument("inputfile")
    parser.add_argument("-o", type=int, default=2, help="Number of optimization passes. Default is 2")
    parser.add_argument("-b", "--bytecode", action="store_true", help="Print generated optimized BF code before executing.")

    args = parser.parse_args()
    inputFile = args.inputfile
    optPasses = args.o

    with open(inputFile,"r") as foo:
        code = foo.read()

    code = re.sub(r"[^\+\-\>\<\.\,\]\[]", "", code) # Remove useless characters
    code = re.sub(r"[+-]{2,}", lambda m: noopRemove(m.group(), "+", "-"), code) # Remove noops
    code = re.sub(r"[><]{2,}", lambda m: noopRemove(m.group(), ">", "<"), code)
    for x in range(optPasses):
        code = re.sub(r"\[-(?:[<>]+\++)+[<>]+\]|\[(?:[<>]+\++)+[<>]+-\]", lambda m: mulcpyLoopSearch(m.group()), code) # Multiply-copyloop optimization
        code = re.sub(r"\[\>\]", "E", code) # Scanloop optimization
        code = re.sub(r"[CS+-]*(?:\[[+-]+\])+\.*", "C", code) # Clearloop optimization, also delete any modifications to cell that is being cleared
        code = re.sub(r"(?:[EC\]]+|\A)\[([^\]]*)]|\[\]", lambda m: "]" if m.group()[0] == "]" else "", code) # Remove dead loops
        code = re.sub(r"(?:[EC]+|^)\++", lambda m: setCell(m.group()), code) # Set cell if value is known 0
        code = re.sub(r"[+-CS]+,", ",", code) # Don't update cells if they are immediately overwritten by stdin

    if args.bytecode:
        print(code)

    f = open("bf.c","w")
    f.write("#include <stdio.h>\n#include <stdint.h>\n#include <string.h>\n\nuint8_t arr[30000] = {0};\nuint8_t* ptr = arr;\n\nint main()\n{\n    memset(arr, 0, 30000);\n")

    codeptr = 0
    copyloopCounter = 0
    setcellCounter = 0
    indent = 1
    while codeptr < len(code):
        command = code[codeptr]
        if command == ">":
            tempcodeptr = 0
            amount = 0
            while codeptr + tempcodeptr < len(code) and code[codeptr + tempcodeptr] == ">":
                amount += 1
                tempcodeptr += 1
            codeptr += amount - 1
            f.write(f"{'    ' * indent}ptr += {amount};\n")
        elif command == "<":
            tempcodeptr = 0
            amount = 0
            while codeptr + tempcodeptr < len(code) and code[codeptr + tempcodeptr] == "<":
                amount += 1
                tempcodeptr += 1
            codeptr += amount -1
            f.write(f"{'    ' * indent}ptr -= {amount};\n")
        elif command == "+":
            tempcodeptr = 0
            amount = 0
            while codeptr + tempcodeptr < len(code) and code[codeptr + tempcodeptr] == "+":
                amount += 1
                tempcodeptr += 1
            codeptr += amount -1
            f.write(f"{'    ' * indent}*ptr += {amount};\n")
        elif command == "-":
            tempcodeptr = 0
            amount = 0
            while codeptr + tempcodeptr < len(code) and code[codeptr + tempcodeptr] == "-":
                amount += 1
                tempcodeptr += 1
            codeptr += amount -1
            f.write(f"{'    ' * indent}*ptr -= {amount};\n")
        elif command == ".":
            f.write(f"{'    ' * indent}putchar(*ptr);\n")
        elif command == ",":
            f.write(f"{'    ' * indent}*ptr = getchar();\n")
        elif command == "[":
            f.write(f"{'    ' * indent}while (*ptr) {{\n")
            indent += 1
        elif command == "]":
            if indent > 1: indent -= 1
            f.write(f"{'    ' * indent}}}\n")
        elif command == "C":
            f.write(f"{'    ' * indent}*ptr = 0;\n")
        elif command == "M":
            f.write(f"{'    ' * indent}*(ptr + {copyloopMap[copyloopCounter]}) += *ptr{'' if copyloopMulMap[copyloopCounter] == 1 else f' * {copyloopMulMap[copyloopCounter]}'};\n")
            copyloopCounter += 1
        elif command == "E":
            f.write(f"{'    ' * indent}ptr = memchr(ptr, 0, 30000);\n")
        elif command == "S":
            f.write(f"{'    ' * indent}*ptr = {setcellMap[setcellCounter]};\n")
            setcellCounter += 1

        codeptr += 1
    f.write("    return 0;\n}")


if __name__ == "__main__":
    main()
    startTime = time.time()
    os.system("tcc -run bf.c")
    input(f"\nExecution time: {round(time.time()-startTime, 5)}s")