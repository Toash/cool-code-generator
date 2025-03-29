from collections import namedtuple
from unittest import case

import TacGen
import sys

# https://kelloggm.github.io/martinjkellogg.com/teaching/cs485-sp25/crm/modern/Cool%20Assembly%20Language.html
ASM_Comment = namedtuple("ASM_Comment", "comment tabbed")
ASM_Label = namedtuple("ASM_Label", "label")

ASM_Li = namedtuple("ASM_Li", "reg imm") # li r1 <- 123
ASM_Mov = namedtuple("ASM_Mov", "dest src") # mov r1 <- r2

ASM_Add = namedtuple("ASM_Add", "dst left right")
ASM_Sub = namedtuple("ASM_Sub", "dst left right")
ASM_Mul = namedtuple("ASM_Mul", "dst left right")
ASM_Div = namedtuple("ASM_Div", "dst left right")

ASM_Jmp = namedtuple("ASM_Jmp", "label")
ASM_Bz = namedtuple("ASM_Bz", "reg label")
ASM_Bnz = namedtuple("ASM_Bnz", "reg label")
ASM_Beq = namedtuple("ASM_Beq", "left right label")
ASM_Blt = namedtuple("ASM_Blt", "left right label")
ASM_Ble = namedtuple("ASM_Ble", "left right label")

ASM_Call_Label = namedtuple("ASM_Call_Label", "label")
ASM_Call_Reg = namedtuple("ASM_Call_Reg", "reg")#jump to address stored in register
ASM_Return = namedtuple("ASM_Return", "") # go to address in ra register (we handle popping ourself)

ASM_Push = namedtuple("ASM_Push", "reg")
ASM_Pop = namedtuple("ASM_Pop", "reg")
ASM_Ld = namedtuple("ASM_Ld", "dest src offset")
ASM_St = namedtuple("ASM_St", "dest src offset")
ASM_La = namedtuple("ASM_La", "reg label") # load address in register

# alloc r1 r2 allocates memory by amount in r2 and stores pointer in r1.
ASM_Alloc = namedtuple("ASM_Alloc", "dest src")
ASM_Constant_integer = namedtuple("ASM_Constant_integer", "int")
ASM_Constant_raw_string = namedtuple("ASM_Constant_raw_string", "string")
ASM_Constant_label = namedtuple("ASM_Constant_label", "label")

ASM_Syscall = namedtuple("ASM_Syscall", "name")


"""
STACK MACHINE CONVENTION:
Cool-ASM has:
8 General registers
3 special ones
    stack pointer (sp)
    frame pointer (fp)
    return address

Address of next instruction is stored in ra
on x86, it will be stored on the stack by the call instruction.

On function call, push parameters on stack
caller set next instruction in ra. 

when in callee, set stack pointer to frame pointer
push ra (the next instruction from caller) onto stack.
"""
class CoolAsmGen:
    def __init__(self,file):
        try:
            self.file = file
            self.asm_instructions = []
            # asm_file = self.file.replace(".cl-type",".cl-asm")
            asm_file = "!MY_COOL_ASM.cl-asm"
            self.outfile = open(asm_file,"w")

            tac_gen = TacGen.TacGen(file)
            self.tac_instructions = tac_gen.get_instructions()
            self.class_map, self.imp_map, self.parent_map = tac_gen.get_class_imp_parent_map()

            # from pprint import pprint
            # print("CLASS MAP:")
            # pprint( self.class_map)
            # print("IMPLEMENTATION MAP:")
            # pprint( self.imp_map)
            # print("PARENT MAP:")
            # pprint( self.parent_map)

            self.emit_vtables()
            self.emit_constructors()
            self.emit_methods()


            # Starting point?
            # self.comment("START")
            # for instr in self.tac_instructions:
            #     # print(instr)
            #     self.emit(instr)

            self.flush_asm()

        finally:
            self.outfile.close()


    def add_asm(self,instr):
        self.asm_instructions.append(instr)

    # write to file
    def flush_asm(self):
        for instr in self.asm_instructions:
            self.outfile.write(self.format_asm(instr) + "\n")

    def format_asm(self,instr):
        if type(instr).__name__ != "ASM_Label" and type(instr).__name__ != "ASM_Comment":
            self.outfile.write("\t\t\t\t")
        if type(instr).__name__ == "ASM_Comment":
            if instr.tabbed:
                self.outfile.write("\t\t\t\t")

        match instr:
            case ASM_Comment(comment):
                return ";;\t" + comment
            case ASM_Label(label):
                return label + ":"
            case ASM_Li(reg, imm):
                return f"li {reg} <- {imm}"
            case ASM_Mov(dest, src):
                return f"mov {dest} <- {src}"
            case ASM_Add(dst, left, right):
                return f"add {dst} <- {left} {right}"
            case ASM_Alloc(dest,src):
                return f"alloc {dest} {src}"
            case ASM_Constant_label(label):
                return f"constant {label}"

            case _:
                print("Unhandled ASM instruction: ", instr)
                sys.exit(1)

    # Loop through classes in imp map for their methods
    def emit_vtables(self):
        self.comment("VIRTUAL TABLES")
        self.comment("constants will represent .quad in x86")
        self.comment("they will represent 8 byte delineations in memory.")
        self.comment("key insight for dynamic dispatch to work correctly: method ordering should be the same")
        for cls in self.class_map:
            # self.outfile.write( # label
            self.add_asm(ASM_Label(label = f"{cls}..vtable"))

            self.add_asm(ASM_Constant_label(label=f"{cls}..new"))
            # self.write(f"constant {cls}..new") # constructor

            #inhertied methods
            for (imp_cls,imp_method), imp in self.imp_map.items():
                exp = imp[-1][1] # skip over formals and line number
                # TODO: This is probably not handling inheritance for non internals.
                if type(exp).__name__ == "Internal":
                    if cls == imp_cls:
                        # body contaisn a string for the actual class and method called.
                        # self.write(f"constant {exp.Body}")
                        self.add_asm(ASM_Constant_label(label=f"{exp.Body}"))
                else:
                    if cls == imp_cls:
                        # self.write(f"constant {imp_cls}.{imp_method}")
                        self.add_asm(ASM_Constant_label(label=f"{imp_cls}.{imp_method}"))

    def emit_constructors(self):

        self_reg = "r0"
        acc_reg = "r1"

        self.comment("CONSTRUCTORS")
        for cls,attrs in self.class_map.items():
            self.add_asm(ASM_Constant_label(label=f"{cls}..new"))
            """
            1. allocate new space for new object
            2. set up the fields in the new object
                2a. set up the vtable pointer
                2b. set each field / attribute to hold a default value
                2c. execute all initializers (in this new context)
            3. return the new object
            """
            """
            size of an object:
            tag (not currently used)
            object size variables (used for clones?) 
            vtable pointer
            fields
            ....
            
            """

            # adding 1 for v table ptr.
            size = len(attrs) + 1
            # load immediate to alloc object layout.
            # emit first real cool asswmbly istrucionts.
            self.add_asm(ASM_Li(reg = self_reg, imm = size))
            self.add_asm(ASM_Alloc(dest = self_reg, src = size))

    def emit_methods(self):
        self.comment("METHODS")
        pass



    #convert TAC to ASM
    def emit(self,instr):
        # print(type(instr).__name__)
        match type(instr).__name__:
            case "TAC_Comment":
                self.comment(instr.Comment)
            case "TAC_Label":
                self.outfile.write(f"{instr.Label}: \n")
            case "TAC_Assign_Int":
                self.comment("new Int")
            case "TAC_Assign_Plus":
                """
                cgen(e1)
                push r1
                cgen(e2)
                pop t1
                add r1 <- t1 r1
                """
            case _:
                print("UNHANDLED: ",instr)
                sys.exit(1)

    def comment(self,comment,tabbed=False):
        self.asm_instructions.append(ASM_Comment(comment=comment,tabbed=tabbed))

if __name__ == "__main__":
    coolAsmGen = CoolAsmGen(sys.argv[1])
