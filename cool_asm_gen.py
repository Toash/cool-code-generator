from collections import namedtuple
from annotated_ast_reader import AnnotatedAstReader
from ast_nodes import *
from cool_asm_instructions import *
import sys
from pprint import pprint

self_reg = "r0"
acc_reg = "r1"  # result of expressions are always in accumulator
temp_reg = "r2"
temp1_reg = temp_reg
temp2_reg = "r3"



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
    def __init__(self,file):
        try:
            self.file = file
            self.asm_instructions = []

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

            asm_file = self.file.replace(".cl-type",".cl-asm")
            self.outfile = open(asm_file,"w")

            parser = AnnotatedAstReader(file)
            self.class_map, self.imp_map, self.parent_map,self.direct_methods = parser.parse()

            # attributes
            self.class_map["Int"].append(Attribute("val","Unboxed_Int",("0",Integer("0","Int"))))

            # from pprint import pprint

            self.emit_vtables()
            self.emit_constructors()
            self.emit_methods()

            self.flush_asm()

        finally:
            self.outfile.close()

    def get_asm(self,include_comments = True):
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

    def add_asm(self,instr):
        self.asm_instructions.append(instr)


    # write to file
    def flush_asm(self):
        for instr in self.asm_instructions:
            self.outfile.write(self.format_asm(instr) + "\n")

    def format_asm(self,instr):
        tabs="\t\t"


        if type(instr).__name__ != "ASM_Label" and type(instr).__name__ != "ASM_Comment":
            self.outfile.write(tabs)

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
                return f"li {reg} <- {imm}"
            case ASM_Mov(dest, src):
                return f"mov {dest} <- {src}"
            case ASM_Add(dst, left, right):
                return f"add {dst} <- {left} {right}"

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

    # Loop through classes in imp map for their methods
    def emit_vtables(self):
        self.comment("VIRTUAL TABLES",not_tabbed=True)
        self.comment("constants will represent .quad in x86",not_tabbed=True)
        self.comment("they will represent 8 byte delineations in memory.",not_tabbed=True)
        self.comment("key insight for dynamic dispatch to work correctly: method ordering should be the same",not_tabbed=True)
        for cls in self.class_map:
            index = 0
            # self.outfile.write( # label
            self.add_asm(ASM_Label(label = f"{cls}..vtable"))

            constant_constructor = f"{cls}..new"
            self.add_asm(ASM_Constant_label(label= constant_constructor))
            # self.vtable_method_indexes[(cls, constant_constructor)] = index
            self.vtable_method_indexes[(cls, "new")] = index
            index += 1
            # self.write(f"constant {cls}..new") # constructor

            # inherited methods
            for (class_name,method_name), imp in self.imp_map.items():

                exp = imp[-1][1] # skip over formals and line number
                # TODO: This is probably not handling inheritance for non internals.
                if type(exp).__name__ == "Internal":
                    if cls == class_name:
                        # body contaisn a string for the actual class and method called.
                        self.add_asm(ASM_Constant_label(label=f"{exp.Body}"))
                        # self.vtable_method_indexes[(class_name, exp.Body)] = index
                        self.vtable_method_indexes[(class_name, (exp.Body).split(".")[1] )] = index
                        index += 1
                else:
                    if cls == class_name:
                        self.add_asm(ASM_Constant_label(label=f"{class_name}.{method_name}"))
                        # self.vtable_method_indexes[(class_name, method_name)] = index
                        self.vtable_method_indexes[(class_name, method_name)] = index
                        index+=1


    def emit_constructors(self):
        self.comment("CONSTRUCTORS",not_tabbed=True)
        self.comment("These will allocate memory (based on object layout gone over in class),",not_tabbed=True)
        self.comment("and will return the object.",not_tabbed=True)
        for cls,attrs in self.class_map.items():
            self.add_asm(ASM_Label(label=f"{cls}..new"))
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
            # FIXME: save old frame pointer
            # after returning, will restore ( so caller can also deallocate)
            # self.add_asm(ASM_Push("fp"))
            # stack room for temporaries
            



            # set up frame pointer (will use to refer to variables later.)
            self.add_asm(ASM_Mov("fp","sp"))
            # save return address
            self.add_asm(ASM_Push("ra"))

            # adding 1 for v table ptr.
            size = len(attrs) + 1
            # load immediate to alloc object layout.
            # emit first real cool asswmbly istrucionts.
            self.comment(f"allocating {size} words of memory for object layout for class {cls}.")
            self.add_asm(ASM_Li(reg = self_reg, imm = size))
            self.add_asm(ASM_Alloc(dest = self_reg, src = self_reg))

            # store vtable pointer
            self.comment("VTable")
            vtable_index = 0

            self.comment(f"Store vtable pointer at index {vtable_index}")
            self.add_asm(ASM_La(temp_reg, f"{cls}..vtable"))

            # store address of vtable in this slot
            self.add_asm(ASM_St(self_reg, temp_reg, 0))

            # attributes - default initializer
            if attrs:
                self.comment("Attributes - default allocation")
            for attr_index,attr in enumerate(attrs, start=1):

                # we are in Int Class.
                # we need to store the raw int value in an attribute.
                if attr.Type == "Unboxed_Int":
                    self.comment(f"Store raw int {0} for attribute in Int.")
                    self.add_asm(ASM_Li(acc_reg,0))
                else:
                    self.cgen(New(Type=attr.Type))
                # store attribute in allocated self object.
                self.add_asm(ASM_St(dest = self_reg,src = acc_reg,offset = attr_index))

            #initializers - explicit user defined.
            if attrs:
                self.comment("Initializers- overwriting attributes if defined.")
            for attr_index,attr in enumerate(attrs, start=1):
                if attr.Type == "Unboxed_Int":
                    continue # already initialized this to 0.

                exp = attr.Initializer[1]
                # generate code for the initializer and put it in r1 (accumulator)
                self.cgen(exp)
                # store the result of cgen in an attribute slot.
                self.comment(f"Initialized {attr}")
                self.add_asm(ASM_St(dest = self_reg,src = acc_reg,offset = attr_index))


            self.comment("return the new object")
            self.add_asm(ASM_Mov(acc_reg,self_reg))

            # self.comment("\t\t\t\tJump to address in ra.")

            # pop the return address.
            self.add_asm(ASM_Pop("ra"))
            # may need to adjust the stack pointer more.
            # add sp <- sp z?
            #   z is the "stack room for temporaries"
            self.add_asm(ASM_Return())


    def emit_methods(self):
        self.comment("METHODS",not_tabbed=True)

        for (cname,mname), imp in self.direct_methods.items():
            self.current_class = cname
            num_args = len(imp)-1
            exp = imp[-1][1]
            self.add_asm(ASM_Label(f"{cname}.{mname}"))

            # set up base pointer address.
            self.add_asm(ASM_Mov("fp","sp"))

            # caller has pushed: arg1, arg2, arg3 receiver_object
            # receiver object is top of stack!!
            # so we want to set "self" <- receiver object
            self.comment("Presumably, caller has pushed arguments,then receiver object on stack.")
            self.comment("Load receiver object into r0 (receiver object is on top of stack).")
            self.add_asm(ASM_Ld(self_reg,"sp",1))
            # self.comment("\t\t\t\tPush return address (call instruction automatically stores it in ra.)")
            self.add_asm(ASM_Push("ra"))

            # when we call Point.setX(newX : Integer)
            # there are a few variables in scope
            # first, all of Point's fields (x,y,Color)
            #   -- live at offsets from receiver object
            # second, and overriding all of setX's formals
            #   -- live at offsets from the frame pointer

            self.push_scope()

            # step 1 - fields / attr in scope
            # print(f"Class map for {cname}:",self.class_map[cname])
            for index,attr in enumerate(self.class_map[cname],start=1):
                if index==1:
                    self.comment("Setting up addresses for attributes (based off offsets from self reg)")
                # self.symbol_stack[attr.Name] = Offset(self_reg, index)
                self.comment(f"Setting up attribute, it lives in {self_reg}[{z}]")
                self.insert_symbol(attr.Name , Offset(self_reg, index))

            # step 2 - formals in scope
            for index,arg in enumerate(imp[:-1],start=1):
                if index == 1:
                    self.comment("Setting up addresses for arguments (based off frame pointer reg)")
                # + 1 because of self object
                # get offset from frame pointer for arguments.
                z=num_args+1-index + 1
                # these formals live at at offset of the frame pointer.
                # self.symbol_stack[arg] = Offset("fp", z)
                # print(f"{arg} lives in fp[{z}]")
                self.comment(f"Setting up argument {arg}, it lives in fp[{z}]")
                self.insert_symbol(arg, Offset("fp", z))

            # call method body.
            self.cgen(exp)

            # ra gets top of stack
            self.add_asm(ASM_Ld("ra","sp",1))
            # arg1 .. n
            # receiver_object
            # return address
            z=num_args+2
            self.add_asm(ASM_Li(temp_reg,z))

            # add sp <- sp z
            self.comment("deallocating stack frame (this also removes the ra that was pushed earlier).")

            self.add_asm(ASM_Add("sp","sp",temp_reg))

            self.pop_scope()



            self.add_asm(ASM_Return())


        # the special start method.
        self.comment("\n\n-=-=-=-=-=-=-=-=-  PROGRAM STARTS HERE  -=-=-=-=-=-=-=-=-",not_tabbed=True)
        self.add_asm(ASM_Label("start"))
        # exp = Dynamic_Dispatch(Exp=New(Type="Main",StaticType="Main"), Method = ID(loc=0,str="main"), Args=[],StaticType="Main")
        # self.add_asm(ASM_Push("ra"))
        # self.cgen(exp)

        self.add_asm(ASM_Call_Label("Main..new"))
        self.add_asm(ASM_Push(acc_reg))
        self.add_asm(ASM_Call_Label("Main.main"))

        # self.add_asm(ASM_Ld("ra", "sp", 1))

        self.add_asm(ASM_Syscall("exit"))

    # generate code for e, put on accumulator register.
    # leave stack the way we found it (good behaviour)
    def cgen(self, exp):
        # we need to change this when adding tags and size in the object layout.
        attr_start_index = 1

        # self.comment(f"\t\t\t\tcgen+: {exp}")

        # locs = []
        # for var, loc in self.symbol_stack[-1].items():
        #     match loc:
        #         case Register(reg):
        #             locs.append(f"{var}={reg}")
        #         case Offset(reg,loc):
        #             locs.append(f"{var}={reg}[{loc}]")

        # self.comment(f"\t\t\tsymbol_table in current scope: {locs}")

        match exp:
            # look up in symbol table, if found, store in accumulator.
            case Identifier(Var):

                match self.lookup_symbol(Var):
                    case Register(reg):
                        # print(f"Found variable in register {reg}")
                        self.add_asm(ASM_Mov(dest = acc_reg, src = reg))
                    case Offset(reg,offset):
                        # print(f"Found variable in register {reg} at offset {offset}")
                        self.add_asm(ASM_Ld(dest=acc_reg,src=reg,offset=offset))
                    case _:
                        print(f"Could not find identifier {Var}")
                        self.add_asm(ASM_Mov(dest=acc_reg, src="NOT_FOUND" ))

            case Integer(Integer=val, StaticType=st):
                # make new int , (default initialized with 0)
                self.comment("We are making an int, so we need an Int object.")
                self.cgen(New(Type="Int",StaticType="Int"))
                # access secrete fields :)
                # right now, this depends on the fact that the location of the raw int is the first attribute index.
                self.comment(f"put {val} in the first attribute for a Cool Int Object :)")
                self.add_asm(ASM_Li(temp_reg,val))
                self.add_asm(ASM_St(acc_reg,temp_reg,attr_start_index))

                # an integer object  with the value in the first attribute is not on the stack.

            case Plus(Left,Right):
                """
                cgen left
                push acc
                cgen right; now in acc
                pop temp

                UNBOXED VALUES
                acc <- ld acc[1]
                temp <- ld temp[1]
                add temp <- temp acc

                push temp
                new Int
                pop temp
                
                UNBOXED
                store acc[1] <- temp
                """
                # Code gen full-fledged cool integer objects.
                self.cgen(Left[1])
                self.add_asm(ASM_Push(acc_reg))
                self.cgen(Right[1])
                self.add_asm(ASM_Pop(temp_reg))

                # load unboxed integers (raw values).
                self.comment("Load unboxed integers.")
                self.add_asm(ASM_Ld(
                    dest = acc_reg,
                    src = acc_reg,
                    offset = attr_start_index))
                self.add_asm(ASM_Ld(temp_reg,temp_reg,attr_start_index))

                # add the raw values.
                self.comment("Add unboxed integers.")
                self.add_asm(ASM_Add(temp_reg,acc_reg,temp_reg))

                # save result
                self.comment("Push result of adding on the stack.")
                self.add_asm(ASM_Push(temp_reg))
                # now in acc.
                self.comment("Create new Int Object.")
                self.cgen(New(Type="Int", StaticType="Int"))
                self.comment("Pop previously saved addition result off of stack.")
                self.add_asm(ASM_Pop(temp_reg))

                # store unboxed int in the new int
                # stores value in src to dest[offset]
                self.comment("Store unboxed int int new Int Object.")
                self.add_asm(ASM_St(
                    dest = acc_reg,
                    src = temp_reg,
                    offset = attr_start_index))


            case New(Type):
                self.add_asm(ASM_Push("fp"))
                self.add_asm(ASM_Push(self_reg))
                # going to put result in ra register.
                # constructor has no arguments and no self object.
                self.add_asm(ASM_Call_Label(f"{Type}..new"))
                self.add_asm(ASM_Pop(self_reg))
                self.add_asm(ASM_Pop("fp"))

            # Dispatch
            case Dynamic_Dispatch(Exp,Method,Args):
                self.gen_dispatch_helper(Exp=Exp, Method=Method, Args=Args)
            case Self_Dispatch(Method,Args):
                self.gen_dispatch_helper(Exp=None, Method=Method, Args=Args)
            case Internal(Body):

                if Body == "IO.out_int":
                    # in the case of out_int, x should be an integer.
                    self.cgen(Identifier(Var="x", StaticType=None))
                    # load unboxed int
                    self.add_asm(ASM_Ld(acc_reg, acc_reg, attr_start_index))
                    self.add_asm(ASM_Comment("out_int writes the raw integer in r1 to standard output."))
                    self.add_asm(ASM_Syscall(Body))
                else:
                    # print("Unhandled Internal: ",Body)
                    pass
            case _:
                print("Unknown expression in cgen: ", exp)
                pass

        # self.comment(f"cgen-: {type(exp).__name__}")


    def gen_dispatch_helper(self, Exp, Method, Args):
        vtable_index = 0
        self.add_asm(ASM_Push("fp"))
        # args has line numbers and we need to skip them.

        """
        Here how the stack frame look like:
        arg 1,
        arg 2,
        arg n....
        receiver object
        """
        self.comment("Push arguments on the stack.")
        for arg in Args:
            self.cgen(arg[1]) # skip line number
            self.add_asm(ASM_Push(acc_reg))

        self.comment("Push receiver on the stack.")
        if Exp:
            self.cgen(Exp)
            self.add_asm(ASM_Push(acc_reg))
        else:
            # object on which current method is invoked.
            self.add_asm(ASM_Mov(acc_reg,self_reg))
            self.add_asm(ASM_Push(self_reg))

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
        self.add_asm(ASM_Ld(dest=temp_reg, src=acc_reg, offset=vtable_index))

        class_name = Exp.Type if Exp else self.current_class
        method_name = Method.str
        # This should always access - unless we have a problem.
        method_vtable_index = self.vtable_method_indexes[(class_name, method_name)]
        # self.add_asm(ASM_Li(temp2_reg,method_vtable_index))
        self.comment(f"{class_name}.{method_name} lives at vindex {method_vtable_index}, loading the address.")
        self.add_asm(ASM_Ld(temp_reg, temp_reg, method_vtable_index))
        self.comment(f"Indirectly call the method.")
        self.add_asm(ASM_Call_Reg(temp_reg))

        # get back old frame pointer
        self.add_asm(ASM_Pop("fp"))

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

if __name__ == "__main__":
    coolAsmGen = CoolAsmGen(sys.argv[1])
