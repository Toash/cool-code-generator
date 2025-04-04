from collections import namedtuple
from annotated_ast_reader import AnnotatedAstReader
from asm_registers import *
from ast_nodes import *
from asm_instructions import *
from asm_helpers import *
from asm_constants import *
import sys
from pprint import pprint



# where variables can live
Register = namedtuple("Register","reg")
Offset = namedtuple("Offset","reg offset")

"""
COOL ASM STACK MACHINE CONVENTION:

Calling convention - on function exit, sp is same as it was on entry.
Need return address (ra)
pointer to start of current activation (fp)

Note: in cool-asm, stack pointers to unused memory sp[1] is the top of the stack.
Stack should be the same before and after a method call.

Next address stored in ra
- pop when calling function
- after function ends (stack has to be the same), 

On function call, 
- push parameters on stack
- push receiver object. 

Note: return jumps to ra.
so after function ends (and stack is the same before call, pop ra then return.)
"""
class CoolAsmGen:
    """
    file - cl-type file name for Parser
    outfile - file stream for cl-asm, for flushing cl-asm. should be provided if flushing.
    x86 - generates output that does not work for cool_asm, but is for x86 convention.
    """
    def __init__(self, file, x86=False):
        self.x86=x86
        self.asm_instructions = [] # cool assembly emitted here.

        # maps variable to member locations.
        # variable could live in register
        # or offset ( fp[4] )
        self.symbol_stack = [{}]

        # store index with <type, mname>
        # to lookup when emitting code for dispatch
        self.vtable_method_indexes = {}

        # keep track of current_class for self_dispatch.
        # because we need the type to call the constructor.
        self.current_class = None

        self.branch_counter = 0

        # parse .cl-type, get information
        parser = AnnotatedAstReader(file)
        self.class_map, self.imp_map, self.parent_map,self.direct_methods = parser.parse()

        # Internal attributes 
        self.class_map["Int"].append(Attribute("val","Unboxed_Int",("0",Integer("0","Int"))))
        # bool also holds a raw int like the Int object.
        self.class_map["Bool"].append(Attribute("val","Unboxed_Int",("0",Integer("0","Int"))))

        self.emit_vtables()
        self.emit_constructors()
        self.emit_methods()
        self.cond_then_label = ""
        self.cond_else_label = ""
        self.cond_end_label = ""

        emit_comparison_handler("eq", self.asm_instructions,x86)
        emit_comparison_false("eq", self.asm_instructions,x86)
        emit_comparison_true("eq", self.asm_instructions,x86)
        emit_comparison_bool("eq", self.asm_instructions,x86)
        emit_comparison_int("eq", self.asm_instructions,x86)
        emit_comparison_end("eq", self.asm_instructions,x86)

        emit_comparison_handler("le", self.asm_instructions,x86)
        emit_comparison_false("le", self.asm_instructions,x86)
        emit_comparison_true("le", self.asm_instructions,x86)
        emit_comparison_bool("le", self.asm_instructions,x86)
        emit_comparison_int("le", self.asm_instructions,x86)
        emit_comparison_end("le", self.asm_instructions,x86)

        emit_comparison_handler("lt", self.asm_instructions,x86)
        emit_comparison_false("lt", self.asm_instructions,x86)
        emit_comparison_true("lt", self.asm_instructions,x86)
        emit_comparison_bool("lt", self.asm_instructions,x86)
        emit_comparison_int("lt", self.asm_instructions,x86)
        emit_comparison_end("lt", self.asm_instructions,x86)


        self.emit_start()


    def get_asm(self,include_comments = False) -> list[namedtuple]:
        asm_instructions_no_comments = []

        # lol
        if not include_comments:
            for asm_instr in self.asm_instructions:
                if(not isinstance(asm_instr,ASM_Comment)):
                    asm_instructions_no_comments.append(asm_instr)

        if not include_comments:
            return asm_instructions_no_comments
        else:
            return self.asm_instructions

    def append_asm(self,instr: namedtuple) -> None:
        self.asm_instructions.append(instr)


    def flush_asm(self,outfile) -> None:
        for instr in self.asm_instructions:
            outfile.write(self.format_asm(instr,outfile) + "\n")

    def format_asm(self,instr:namedtuple,outfile) -> str:
        tabs="\t\t"


        if type(instr).__name__ != "ASM_Label" and type(instr).__name__ != "ASM_Comment":
            outfile.write(tabs)

        match instr:
            case ASM_Comment(comment,not_tabbed):
                import re

                result = re.sub(r"^(\s*)", r"\1;;\t", comment)

                #lol
                if not not_tabbed:
                    return tabs+result
                else:
                    return result

            case ASM_Label(label):
                return label + ":"
            case ASM_Li(reg, imm):
                return f"li {reg} <- {imm.value}"
            case ASM_Mov(dest, src):
                return f"mov {dest} <- {src}"
            
            case ASM_Add(left, right):
                return f"add {right} <- {right} {left}"
            case ASM_Sub(left, right):
                return f"sub {right} <- {right} {left}"
            case ASM_Mul(left, right):
                return f"mul {right} <- {right} {left}"
            case ASM_Div(left, right):
                return f"div {right} <- {right} {left}"

            case ASM_Jmp(label):
                return f"jmp {label}"
            case ASM_Bnz(reg,label):
                return f"bnz {reg} {label}"
            case ASM_Beq(left,right,label):
                return f"beq {left} {right} {label}"
            # https://en.wikipedia.org/wiki/BLT
            case ASM_Blt(left,right,label):
                return f"blt {left} {right} {label}"
            case ASM_Ble(left,right,label):
                return f"ble {left} {right} {label}"

            case ASM_Call_Label(label):
                return f"call {label}"
            case ASM_Call_Reg(reg):
                return f"call {reg}"

            case ASM_Return():
                return "return"

            case ASM_Push(reg):
                return f"push {reg}"
            case ASM_Pop(reg):
                return f"pop {reg}"


            case ASM_Ld(dest,src,offset):
                return f"ld {dest} <- {src}[{offset}]"
            case ASM_St(dest,src,offset):
                return f"st {dest}[{offset}] <- {src}"

            case ASM_La(reg, label):
                return f"la {reg} <- {label}"
            case ASM_Alloc(dest,src):
                return f"alloc {dest} {src}"
            case ASM_Constant_label(label):
                return f"constant {label}"

            case ASM_Syscall(name):
                return f"syscall {name}"

            case _:
                print("Unhandled ASM instruction: ", instr)
                sys.exit(1)


    def emit_function_prologue(self) -> None:
        # the cool way
        if not self.x86:
            self.comment("FUNCTION START")
            self.append_asm(ASM_Mov("fp","sp"))
            self.comment("Presumably, caller has pushed arguments,then receiver object on stack.")
            self.comment("Load receiver object into r0 (receiver object is on top of stack).")
            self.append_asm(ASM_Ld(self_reg,"sp",1))
            self.append_asm(ASM_Push("ra"))
        else:
            # the x86 way
            self.comment("IN X86 - RETURN ADDRESS HAD BETTER BE BEFORE THIS FRAME POINTER OR ELSE BAD THINGS WILL HAPPEN")
            self.append_asm(ASM_Push("fp"))
            self.append_asm(ASM_Mov(dest="fp",src="sp"))
            # load stack pointer
            # +1 for return address
            # +1 for the actual self object
            self.append_asm(ASM_Ld(self_reg,"sp",2))


            # alignment padding
            self.comment("16 byte alignment padding")
            self.append_asm(ASM_Li(temp_reg,ASM_Word(1)))
            self.append_asm(ASM_Sub(temp_reg,"sp"))
            
            

    def emit_function_epilogue(self,z) -> None:
        self.comment("FUNCTION CLEANUP")
        if not self.x86:
            # the cool way
            # stack layout- 
            #   arg1 .. n
            #   receiver_object
            #   return address
            self.append_asm(ASM_Ld(dest="ra",src="sp",offset=1)) # return address on top
            self.append_asm(ASM_Li(temp_reg,ASM_Word(z)))
            self.append_asm(ASM_Add(temp_reg,"sp"))
            self.pop_scope()
            self.append_asm(ASM_Return())
        else:
            # the x86 way
            # stack layout-
            #   return address
            #   arg1 .. n
            #   receiver_object
            self.append_asm(ASM_Mov(dest="sp", src="fp"))
            self.append_asm(ASM_Pop("fp"))
            self.append_asm(ASM_Return())



    # Loop through classes in imp map for their methods
    def emit_vtables(self) -> None:
        self.comment("VIRTUAL TABLES",not_tabbed=True)
        self.comment("constants will represent .quad in x86",not_tabbed=True)
        self.comment("they will represent 8 byte delineations in memory.",not_tabbed=True)
        self.comment("key insight for dynamic dispatch to work correctly: method ordering should be the same",not_tabbed=True)
        for cls in self.class_map:
            index = 0
            self.append_asm(ASM_Label(label = f"{cls}..vtable"))

            constant_constructor = f"{cls}..new"
            self.append_asm(ASM_Constant_label(label= constant_constructor))
            self.vtable_method_indexes[(cls, "new")] = index
            index += 1

            # inherited methods
            for (class_name,method_name), imp in self.imp_map.items():

                exp = imp[-1][1] # skip over formals and line number
                # FIXME: This is probably not handling inheritance for non internals.
                if type(exp).__name__ == "Internal":
                    if cls == class_name:
                        # body contaisn a string for the actual class and method called.
                        self.append_asm(ASM_Constant_label(label=f"{exp.Body}"))
                        self.vtable_method_indexes[(class_name, (exp.Body).split(".")[1] )] = index
                        index += 1
                else:
                    if cls == class_name:
                        self.append_asm(ASM_Constant_label(label=f"{class_name}.{method_name}"))
                        # self.vtable_method_indexes[(class_name, method_name)] = index
                        self.vtable_method_indexes[(class_name, method_name)] = index
                        index+=1

    def emit_constructors(self) -> None:
        self.comment("CONSTRUCTORS",not_tabbed=True)
        self.comment("These will allocate memory (based on object layout gone over in class),",not_tabbed=True)
        self.comment("object will be in accumulator.",not_tabbed=True)
        for cls,attrs in self.class_map.items():
            self.append_asm(ASM_Label(label=f"{cls}..new"))
            """
            1. allocate new space for new object
            2. set up the fields in the new object
                2a. set up the vtable pointer
                2b. set each field / attribute to hold a default value
                2c. execute all initializers (in this new context)
            3. return the new object
            """
            """
            Object layout:
            tag                     (not currently used)
            object size variable    (not currently used)
            vtable pointer
            attributes
            ....
            """
            self.comment("setup stuff")
            if self.x86:
                self.append_asm(ASM_Push("fp")) # we will set stack pointer to this later
            self.append_asm(ASM_Mov("fp","sp"))

            if not self.x86:
                self.append_asm(ASM_Push("ra"))
           

            if self.x86:
                self.comment("stack offset for 16 byte alignment")
                self.append_asm(ASM_Li(temp_reg,ASM_Word(1)))
                self.append_asm(ASM_Sub(temp_reg,"sp"))

            # adding 1 for type tag.
            # adding 1 for size.
            # adding 1 for v table ptr.
            # indexes are in asm_constants.py
            size = len(attrs) + 3

            self.comment(f"allocating {size} words of memory for object layout for class {cls}.")
            self.append_asm(ASM_Li(reg = self_reg, imm = ASM_Value(size)))
            self.append_asm(ASM_Alloc(dest = self_reg, src = self_reg))

            match(cls):
                case "Bool":
                    tag=Bool_tag
                case "Int":
                    tag=Int_tag
                case _:
                    # FIXME: handle arbitrary amount of type tags.
                    tag=1000

            self.comment(f"Store type tag ({tag} for {cls}) at index {type_tag_index}")
            self.append_asm(ASM_Li(temp_reg,ASM_Value(tag))) 
            self.append_asm(ASM_St(self_reg, temp_reg, type_tag_index))

            # TODO: implement object size
            self.comment(f"Store object size at index {object_size_index}")
            self.append_asm(ASM_Li(temp_reg,ASM_Value(3 + len(attrs))))
            self.append_asm(ASM_St(self_reg, temp_reg, object_size_index))

            self.comment(f"Store vtable pointer at index {vtable_index}")
            self.append_asm(ASM_La(temp_reg, f"{cls}..vtable"))
            self.append_asm(ASM_St(self_reg, temp_reg, vtable_index))

            # default initializers
            if attrs:
                self.comment("Attributes - default allocation")
            for actual_attr_index,attr in enumerate(attrs, start=attributes_start_index):

                # we are in Int Class.
                # we need to store the raw int value in an attribute.
                if attr.Type == "Unboxed_Int":
                    self.comment(f"Store raw int {0} for attribute in Int.")
                    self.append_asm(ASM_Li(acc_reg,ASM_Value(0)))
                else:
                    self.comment(f"Create new object for {attr.Type}")
                    self.cgen(New(Type=attr.Type))
                # store attribute in allocated self object.
                self.append_asm(ASM_St(dest = self_reg,src = acc_reg,offset = actual_attr_index))


            # explicit initializers.
            if attrs:
                self.comment("Initializers- overwriting attributes where initializers are defined.")
            for actual_attr_index,attr in enumerate(attrs, start=attributes_start_index):
                if attr.Type == "Unboxed_Int":
                    continue # already initialized this to 0.

                exp = attr.Initializer[1]
                # generate code for the initializer and put it in r1 (accumulator)
                self.cgen(exp)
                # store the result of cgen in an attribute slot.
                self.comment(f"Initialized {attr}")
                self.append_asm(ASM_St(dest = self_reg,src = acc_reg,offset = actual_attr_index))


            self.comment("As promised, store the new object into the accumulator.")
            self.append_asm(ASM_Mov(acc_reg,self_reg))


            self.comment("cleanup stuff")
            if self.x86:
                self.append_asm(ASM_Mov("sp","fp"))
                self.append_asm(ASM_Pop("fp"))
            if not self.x86:
                self.append_asm(ASM_Pop("ra"))
            self.append_asm(ASM_Return())


    def emit_methods(self)->None:
        self.comment("METHODS",not_tabbed=True)

        for (cname,mname), imp in self.direct_methods.items():
            self.current_class = cname
            num_args = len(imp)-1
            exp = imp[-1][1]
            self.append_asm(ASM_Label(f"{cname}.{mname}"))

            # ---------------------- PROLOGUE ---------------------
            
            self.emit_function_prologue()

            # -------------------- END OF PROLOGUE-----------------------------


            # when we call Point.setX(newX : Integer)
            # there are a few variables in scope
            # first, all of Point's fields (x,y,Color)
            #   -- live at offsets from receiver object
            # second, and overriding all of setX's formals
            #   -- live at offsets from the frame pointer

            self.push_scope()

            # step 1 - fields / attr in scope
            for index,attr in enumerate(self.class_map[cname],start=1):
                if index==1:
                    self.comment("Setting up addresses for attributes (based off offsets from self reg)")
                # FIXME - X86
                self.comment(f"Setting up attribute, it lives in {self_reg}[{stack_cleanup_size}]")
                self.insert_symbol(attr.Name , Offset(self_reg, index))

            # step 2 - formals in scope
            for index,arg in enumerate(imp[:-1],start=1):
                if index == 1:
                    self.comment("Getting args.")

                # + 1 because of self object
                # leftmost arguments are closer to the frame pointer.
                # the self object is right next to the frame pointer.
                fp_offset=num_args+1-index + 1

                # these formals live at at offset of the frame pointer.
                self.comment(f"Add argument {arg} to symbol table, it lives in fp[{fp_offset}]")
                self.insert_symbol(arg, Offset("fp", fp_offset))

            # we need to actually load these args in .

            self.append_asm(ASM_Comment("start code-genning method body"))
            self.cgen(exp)
            self.append_asm(ASM_Comment("done code-genning method body"))

            # ------------ EPILOGUE -----------------

            # args 
            # +1 for self ( we never actually pop r0 on method start
            #                    unlike the reference compiler.)
            # +1 for return  ( we dont pop it, we just read it from top.)
            stack_cleanup_size=num_args+2
            self.emit_function_epilogue(stack_cleanup_size)


    def emit_start(self)->None:
        # the special start method.
        self.comment("\n\n-=-=-=-=-=-=-=-=-  PROGRAM STARTS HERE  -=-=-=-=-=-=-=-=-",not_tabbed=True)
        self.append_asm(ASM_Label("start"))
        # push frame pointer for ret in Main..new
        self.append_asm(ASM_Call_Label("Main..new"))
        self.append_asm(ASM_Comment("Push receiver (in accumulator, from Main..new) on stack."))
        self.append_asm(ASM_Push(acc_reg))
        self.append_asm(ASM_Call_Label("Main.main"))
        self.append_asm(ASM_Syscall("exit"))

    """
    generate code for e, put on accumulator register.
    (append instuctions to our asm list)
    leave stack the way we found it 
    """
    def cgen(self, exp)->None:
        self.comment(f"cgen+: {type(exp).__name__}")

        # locs = []
        # for var, loc in self.symbol_stack[-1].items():
        #     match loc:
        #         case Register(reg):
        #             locs.append(f"{var}={reg}")
        #         case Offset(reg,loc):
        #             locs.append(f"{var}={reg}[{loc}]")

        # self.comment(f"\t\t\tsymbol_table in current scope: {locs}")

        match exp:

            # Dispatch
            case Dynamic_Dispatch(Exp,Method,Args):
                self.gen_dispatch_helper(Exp=Exp, Method=Method, Args=Args)
            case Self_Dispatch(Method,Args):
                self.gen_dispatch_helper(Exp=None, Method=Method, Args=Args)

            case If(Predicate, Then, Else):
                self.cond_then_label = "true_" + self.get_branch_label()
                self.cond_else_label = "false_" + self.get_branch_label()
                self.cond_end_label = "end_" + self.get_branch_label()

                # predicate
                match Predicate[1]:
                    case Lt(Left,Right):
                        self.cgen(Lt(Left,Right,StaticType="Bool"))                        
                    case Le(Left,Right):
                        self.cgen(Le(Left,Right,StaticType="Bool"))                        
                    case Eq(Left,Right):
                        self.cgen(Eq(Left,Right,StaticType="Bool"))                        
                    case true(Value):
                        self.cgen(true(Value,StaticType="Bool"))
                    case false(Value):
                        self.cgen(false(Value,StaticType="Bool"))
                    case _:
                       print("Unhandled predicate:", Predicate) 

                # else
                self.comment("ELSE (False branch)",not_tabbed=True)
                self.append_asm(ASM_Label(self.cond_else_label))
                self.cgen(Else[1])
                self.append_asm(ASM_Jmp(self.cond_end_label))

                # then
                self.comment("THEN (True branch)",not_tabbed=True)
                self.append_asm(ASM_Label(self.cond_then_label))
                self.cgen(Then[1])

                # end
                self.comment("END of if conditional")
                self.append_asm(ASM_Label(self.cond_end_label))

                # Accumulater will contain the result of either the then or else.


            case Block(Body):
                for exp in Body:
                    exp = exp[1]
                    self.cgen(exp)
            # acc will contain the last result of the entire block.

            case New(Type):
                self.append_asm(ASM_Push("fp"))
                self.append_asm(ASM_Push(self_reg))
                # going to put result in ra register.
                # constructor has no arguments and no self object.
                self.append_asm(ASM_Call_Label(f"{Type}..new"))
                self.append_asm(ASM_Pop(self_reg))
                self.append_asm(ASM_Pop("fp"))
                # New object now in accumulator.

            case Plus(Left,Right):
                self.cgen(Left[1])
                self.append_asm(ASM_Push(acc_reg))
                self.cgen(Right[1])
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Load unboxed integers.")
                self.append_asm(ASM_Ld(
                    dest = acc_reg,
                    src = acc_reg,
                    offset = attributes_start_index))
                self.append_asm(ASM_Ld(temp_reg,temp_reg,attributes_start_index))

                self.comment("Add unboxed integers.")
                self.append_asm(ASM_Add(acc_reg,temp_reg))

                self.comment("Push result of adding on the stack.")
                self.append_asm(ASM_Push(temp_reg))

                self.comment("Create new Int Object.")
                self.cgen(New(Type="Int", StaticType="Int"))
                self.comment("Pop previously saved addition result off of stack.")
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Store unboxed int inside new Int Object.")
                self.append_asm(ASM_St(
                    dest = acc_reg,
                    src = temp_reg,
                    offset = attributes_start_index))

                # Addition result now in accumulator.
                
            case Minus(Left,Right):
                self.cgen(Left[1])
                self.append_asm(ASM_Push(acc_reg))
                self.cgen(Right[1])
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Load unboxed integers.")
                self.append_asm(ASM_Ld(
                    dest = acc_reg,
                    src = acc_reg,
                    offset = attributes_start_index))
                self.append_asm(ASM_Ld(temp_reg,temp_reg,attributes_start_index))

                self.comment("Subtract unboxed integers.")
                self.append_asm(ASM_Sub(acc_reg,temp_reg))


                self.comment("Push result of subtracting on the stack.")
                self.append_asm(ASM_Push(temp_reg))

                self.comment("Create new Int Object.")
                self.cgen(New(Type="Int", StaticType="Int"))
                self.comment("Pop previously saved subtraction result off of stack.")
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Store unboxed int inside new Int Object.")
                self.append_asm(ASM_St(
                    dest = acc_reg,
                    src = temp_reg,
                    offset = attributes_start_index))

                # Subtraction result now in accumulator.

            case Times(Left,Right):
                self.cgen(Left[1])
                self.append_asm(ASM_Push(acc_reg))
                self.cgen(Right[1])
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Load unboxed integers.")
                self.append_asm(ASM_Ld(
                    dest = acc_reg,
                    src = acc_reg,
                    offset = attributes_start_index))
                self.append_asm(ASM_Ld(temp_reg,temp_reg,attributes_start_index))

                self.comment("Multiply unboxed integers.")
                self.append_asm(ASM_Mul(acc_reg,temp_reg))

                self.comment("Push result of multiplying on the stack.")
                self.append_asm(ASM_Push(temp_reg))

                self.comment("Create new Int Object.")
                self.cgen(New(Type="Int", StaticType="Int"))
                self.comment("Pop previously saved multiplication result off of stack.")
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Store unboxed int inside new Int Object.")
                self.append_asm(ASM_St(
                    dest = acc_reg,
                    src = temp_reg,
                    offset = attributes_start_index))
                # Multiplication result now in accumulator.

            case Divide(Left,Right):
                self.cgen(Left[1])
                self.append_asm(ASM_Push(acc_reg))
                self.cgen(Right[1])
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Load unboxed integers.")
                self.append_asm(ASM_Ld(
                    dest = acc_reg,
                    src = acc_reg,
                    offset = attributes_start_index))
                self.append_asm(ASM_Ld(temp_reg,temp_reg,attributes_start_index))

                self.comment("Divide unboxed integers.")
                self.append_asm(ASM_Div(acc_reg,temp_reg))

                self.comment("Push result of dividing on the stack.")
                self.append_asm(ASM_Push(temp_reg))

                self.comment("Create new Int Object.")
                self.cgen(New(Type="Int", StaticType="Int"))
                self.comment("Pop previously saved division result off of stack.")
                self.append_asm(ASM_Pop(temp_reg))

                self.comment("Store unboxed int inside new Int Object.")
                self.append_asm(ASM_St(
                    dest = acc_reg,
                    src = temp_reg,
                    offset = attributes_start_index))
                # Division result now in accumulator.


            case Lt(Left,Right) | Le(Left,Right) | Eq(Left, Right):
                self.append_asm(ASM_Push(self_reg))
                self.append_asm(ASM_Push("fp"))

                left_type =  Left[1].StaticType
                self.cgen(New(Type= left_type,StaticType=left_type))
                # load the actual values
                if(isinstance(Left[1],Integer)):
                    self.append_asm(ASM_Li(temp_reg,ASM_Value(Left[1].Integer)))    
                    self.append_asm(ASM_St(acc_reg,temp_reg,attributes_start_index))
                else:
                    raise Exception("unhandled operands in bool comparison")
                self.append_asm(ASM_Push(acc_reg))

                right_type =  Right[1].StaticType
                self.cgen(New(Type=right_type, StaticType=right_type))
                # load the actual values
                if(isinstance(Right[1],Integer)):
                    self.append_asm(ASM_Li(temp_reg,ASM_Value(Right[1].Integer)))    
                    self.append_asm(ASM_St(acc_reg,temp_reg,attributes_start_index))
                else:
                    raise Exception("unhandled operands in bool comparison")
                self.append_asm(ASM_Push(acc_reg))
                self.append_asm(ASM_Push(self_reg))
                # stack:
                # left
                # right
                # self object
                match type(exp).__name__:
                    case "Lt":
                        self.append_asm(ASM_Call_Label("lt_handler"))
                    case "Le":
                        self.append_asm(ASM_Call_Label("le_handler"))
                    case "Eq":
                        self.append_asm(ASM_Call_Label("eq_handler"))
                    case _:
                        raise Exception("Unknown conditional expression:", exp) 
                if self.x86:
                    self.comment("x86- deallocate two args and self.")
                    self.append_asm(ASM_Li(temp_reg,ASM_Word(3)))
                    self.append_asm(ASM_Add(temp_reg,"sp"))
                # CLEANUP
                self.append_asm(ASM_Pop("fp"))
                self.append_asm(ASM_Pop(self_reg))

                # less than handler gave us something
                self.append_asm(ASM_Ld(acc_reg,acc_reg,3))
                self.append_asm(ASM_Bnz(acc_reg, self.cond_then_label))



            case Integer(Integer=val, StaticType=st):
                # make new int , (default initialized with 0)
                self.cgen(New(Type="Int",StaticType="Int"))

                # access secrete fields :)
                # this depends on the fact that the location of the raw int is the first attribute index.
                self.comment(f"put {val} in the first attribute for a Cool Int Object :)")
                self.append_asm(ASM_Li(temp_reg,ASM_Value(val)))
                self.append_asm(ASM_St(acc_reg,temp_reg,attributes_start_index))
                # Integer object now in accumulator register.

            # look up in symbol table, if found, store in accumulator.
            case Identifier(Var):
                match self.lookup_symbol(Var):
                    case Register(reg):
                        self.comment(f"Found variable in register {reg}")
                        self.append_asm(ASM_Mov(dest = acc_reg, src = reg))
                    case Offset(reg,offset):
                        self.comment(f"Found variable in register {reg} at offset {offset}")
                        if not self.x86:
                            self.append_asm(ASM_Ld(dest=acc_reg,src=reg,offset=offset))
                        else:
                            self.comment(f"x86: have to add one to offset (so offset is {offset+1}), because rbp is pushed.")
                            self.append_asm(ASM_Ld(dest=acc_reg,src=reg,offset=offset+1))
                    case _:
                        print(f"Could not find identifier {Var}")
                        self.append_asm(ASM_Mov(dest=acc_reg, src="NOT_FOUND" ))

            case true(Value):
                self.cgen(New(Type="Bool", StaticType="Bool"))
                self.append_asm(ASM_Li(temp_reg,ASM_Value(1)))
                self.append_asm(ASM_St(acc_reg,temp_reg,attributes_start_index))
                self.append_asm(ASM_Ld(acc_reg,acc_reg,attributes_start_index))
                self.append_asm(ASM_Bnz(acc_reg,self.cond_then_label))
                
            case false(Value):
                self.cgen(New(Type="Bool", StaticType="Bool"))
                self.append_asm(ASM_Ld(acc_reg,acc_reg,attributes_start_index))
                self.append_asm(ASM_Bnz(acc_reg,self.cond_then_label))

            case Internal(Body):

                if Body == "IO.out_int":
                    # in the case of out_int, x should be an integer.
                    self.cgen(Identifier(Var="x", StaticType=None))

                    self.comment("Load unboxed int.")
                    self.append_asm(ASM_Ld(acc_reg, acc_reg, attributes_start_index))

                    self.append_asm(ASM_Syscall(Body))
                else:
                    # print("Unhandled Internal: ",Body)
                    pass
            case _:
                print("Unknown expression in cgen: ", exp)
                pass

        self.comment(f"cgen-: {type(exp).__name__}")


    def gen_dispatch_helper(self, Exp, Method, Args):

        #save self object and frame pointer to restore later
        self.append_asm(ASM_Push("fp"))
        self.append_asm(ASM_Push(self_reg))

        """
        Here how the stack frame look like:
        arg 1,
        arg 2,
        arg n....
        receiver object
        """
        for arg in Args:
            self.cgen(arg[1]) # skip line number
            self.comment("Push argument on the stack.")
            self.append_asm(ASM_Push(acc_reg))

        if Exp:
            self.cgen(Exp)
        else:
            # object on which current method is invoked.
            self.comment("Move receiver to accumulator.")
            self.append_asm(ASM_Mov(acc_reg,self_reg))

        self.comment("Push self receiver on the stack.")
        self.append_asm(ASM_Push(acc_reg))


        """
        1. load RO (acc) vtable into (temp)
        2. load the vtable index into (temp2)
        3. temp <- temp[temp2] -- get method pointer
        4. call temp
        """
        # receiver object in acc.
        # e.g: someone wants to invoke "out_int" or "main"
        # emit code to lookup in vtable.
        self.comment("Loading v table.")
        self.append_asm(ASM_Ld(dest=temp_reg, src=acc_reg, offset=vtable_index))

        class_name = Exp.Type if Exp else self.current_class
        method_name = Method.str
        # This should always access - unless we have a problem.
        method_vtable_index = self.vtable_method_indexes[(class_name, method_name)]
        # self.add_asm(ASM_Li(temp2_reg,method_vtable_index))
        self.comment(f"{class_name}.{method_name} lives at vindex {method_vtable_index}, loading the address.")
        self.append_asm(ASM_Ld(temp_reg, temp_reg, method_vtable_index))
        self.comment(f"Indirectly call the method.")
        self.append_asm(ASM_Call_Reg(temp_reg))


        # in cool_asm we are adding to stack pointer in callee
        # cant do this in x86, the return address is in the way.
        # so we do it in the caller, where the return address has already been popped off by ret.
        if self.x86:
            self.comment(f"x86- clean up stack.")
            self.append_asm(ASM_Li(acc_reg,ASM_Word(len(Args)+1)))
            self.append_asm(ASM_Add(acc_reg,"sp"))
            pass

        # self.add_asm(ASM_Pop(self_reg))
        # get back old frame pointer
        self.append_asm(ASM_Pop(self_reg))
        self.append_asm(ASM_Pop("fp"))


    def comment(self,comment,not_tabbed=False):
        self.asm_instructions.append(ASM_Comment(comment=comment,not_tabbed=not_tabbed))

    # call when entering new expression
    def push_scope(self):
        self.symbol_stack.append({})
    def pop_scope(self):
        self.symbol_stack.pop()

    def insert_symbol(self, symbol, loc):
        self.symbol_stack[-1][symbol] = loc

    def lookup_symbol(self, symbol):
        for scope in reversed(self.symbol_stack):
            if symbol in scope:
                return scope[symbol]
        return None
        # print (f"Could not find symbol {symbol} in scope!")
        # sys.exit(1)

    def get_branch_label(self):
        self.branch_counter+=1
        return f"branch_{self.branch_counter}"


if __name__ == "__main__":
    file = sys.argv[1]
    # open .cl-asm file to write.
    asm_file = file.replace(".cl-type",".cl-asm")
    with open(asm_file,"w") as outfile:
        coolAsmGen = CoolAsmGen(file=file)
        coolAsmGen.flush_asm(outfile)
