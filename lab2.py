import sys
import math
from sys import stdin, stdout
from datetime import datetime
import os
from os.path import expanduser

# BUF_SIZE = 1024 # used for reading a fixed buffer size
BUF_SIZE = 4096  # used for reading a fixed buffer size
# BUF_SIZE = 32768 # used for reading a fixed buffer size
# fence = 0 # indicates the beginning of the valid context TODO: will become relevant when you're not just reading in lines
i = 0  # indicates the index of the character we're looking at
buf1 = ""
buf2 = ""
buf1_len = 0  # length of buf1
buf2_len = 0  # length of buf2

char = ""  # current character that we're on
line_num = 0  # keeps track of line number
curr_string = ""  # holds the current lexeme as we're scanning the input
flag_level = -1
EOF = False
IrHead = None
IrTail = None
verbose = False
lex_errors = 0
syntax_errors = 0
f = None
k = 0
MAXLIVE = 0
MAX_SOURCE = 0
MAX_VR = 0
tot_block_len = 0
VrToPr = []
PrToVr = []
PrNu = []
pr_queue = [] # stack of free PRs
spilled_bits = 0
# keeps track of which virtual registers have been spilled
    # note: we'll only ever add bits to this number

class IRArray:
    def __init__(self, opcode, int1, int2, int3):
        """

        :param opcode: The operation code 
        :param int1: the value for the first argument to the operation.
        :param int2: the value for the second argument to the operation.
        :param int3: the value for the third argument to the operation.
        Note that for the above 3 int values we deduce whether they refer to 
        constants or registers from the operation code. 
        They can also be None, indicating that the operation has no such argument

        Upon intializing the object, we create the array and fill it in appropriately.
        Entries will only get a number if they have an argument
        """
        self.opcode = opcode
        self.ir_data = []
        for i in range(12):
            self.ir_data.append(None)
        self.ir_data[0] = int1
        self.ir_data[4] = int2
        self.ir_data[8] = int3
        self.next = None
        self.prev = None

    def link_next(self, next_ir):
        """

        :param next_ir: Refers to the IRArray object which we want to link as
        coming after this one
        :return: 
        """
        next_ir.prev = self
        self.next = next_ir

    def sr_to_string(self):
        """
        :return: 
            Returns the string representation of this IRArray
        """
        operations = ["LOAD", "STORE", "LOADI", "ADD", "SUB", "MULT",
                      "LSHIFT", "RSHIFT", "OUTPUT", "NOP",
                      "CONSTANT", "REGISTER", "COMMA", "INTO", "ENDFILE"]
        reg_array = ["SR", "VR", "PR", "NU", "SR", "VR", "PR", "NU",
                     "SR", "VR", "PR", "NU"]

        output = operations[self.opcode] + "(" + str(self.opcode) + ")"
        reg1 = False

        if self.opcode == 2 or self.opcode == 8:
            for i in range(0, 4):
                if self.ir_data[i] != None:
                    reg1 = True
                    # print(self.ir_data[i])
                    output += " [ val: " + str(self.ir_data[i]) + " ], "
        else:
            for i in range(0, 4):
                if self.ir_data[i] != None:
                    # print(self.ir_data[i])
                    reg1 = True
                    output += " [ " + reg_array[i] + " " + str(
                        self.ir_data[i]) + " ], "
        if not reg1:
            output += " [ ], "

        reg2 = False
        for i in range(4, 8):
            if self.ir_data[i] != None:
                # print(self.ir_data[i])
                reg2 = True
                output += " [ " + reg_array[i] + " " + str(
                    self.ir_data[i]) + " ], "

        if not reg2:
            output += " [ ], "
        reg3 = False

        for i in range(8, 12):
            if self.ir_data[i] != None:
                # print(self.ir_data[i])
                reg3 = True
                output += " [ " + reg_array[i] + " " + str(
                    self.ir_data[i]) + " ] "

        if not reg3:
            output += " [ ] "
            # print(p_line_num)
            # print(output)
        return output

    def complete_to_string(self):
        """
        :return: 
            Returns the string representation of this IRArray, 
            including SR, VR, PR and NU
        """
        operations = ["LOAD", "STORE", "LOADI", "ADD", "SUB", "MULT",
                      "LSHIFT", "RSHIFT", "OUTPUT", "NOP",
                      "CONSTANT", "REGISTER", "COMMA", "INTO", "ENDFILE"]
        reg_array = ["SR", "VR", "PR", "NU", "SR", "VR", "PR", "NU",
                     "SR", "VR", "PR", "NU"]

        output = operations[self.opcode] + "(" + str(self.opcode) + ")  "

        if verbose:
            print("actual array:")
            print(self.ir_data)

        for i in range(11):
            output += reg_array[i]
            if self.ir_data[i] == None:
                output += ":[], "
            else:
                output += ":[ %d ], " % self.ir_data[i]

        output += reg_array[11]
        if self.ir_data[11] == None:
            output += ":[] "
        else:
            output += ":[ %d ] " % self.ir_data[11]
        return output

def print_ir():
    """
    Prints out the intermediate representation in an 
    "appropriately human readable format"
     Note: also prints out all trailing IRArrays
    :return: None
    """
    global IrHead

    if verbose:
        print("about to print out intermediate representation")
    next_ir = IrHead

    while next_ir != None:
        print(next_ir.sr_to_string())
        # total_output += "\n" + next_ir.to_string()
        next_ir = next_ir.next
        # print(total_output)

def main():
    """
    Will appropriately read in the file arguments and run the operation that we 
    want. This might be to run on a single file, or a directory of files. 
    We can do any one of the following operations: 
    -print help options
    -print out all tokens and lexical errors
    -scan and parse
    -scan, parse, and print out the intermediate representation
    :return: 
    """
    global verbose, flag_level, f, char, EOF, k
    numArgs = len(sys.argv)
    numFlags = 0  # counts how many of provided args are flags


    if is_number(sys.argv[1]):
        k = int(sys.argv[1])

    if "-x" in sys.argv:
        flag_level = 1
        numFlags += 1
    if "-h" in sys.argv:
        flag_level = 0
        numFlags += 1
    if "-v" in sys.argv:
        print("verbose turned on")
        verbose = True
        numArgs -= 1

    if len(sys.argv) < 3:
        print("Note: 412alloc takes 3 arguments:"
              "412fe <flag> <filename>")


    if numFlags > 1:
        print("Note: 412alloc takes only 1 flag:"
              "412fe <flag> <filename>. You specified %d " % numFlags)

    if flag_level == -1:
        flag_level = 2
    if flag_level == 0:
        print("412alloc.py takes the arguments <k|-x> <filename>")
        return
        # print out help statement

    if verbose:
        f = open(sys.argv[numArgs], 'r')
    else:
        f = open(sys.argv[numArgs - 1], 'r')
    init_double_buf()
    parse()

    if flag_level == 1:
        if verbose:
            print("About to print renamed")
        rename()
        print_renamed_ir()

        if verbose:
            # check that we didn't prematurely use any undefined registers
            check_not_using_undefined()
        # then we print the renamed intermediate representation
        return
    else:
        # then we allocate the registers
        reg_alloc()
    # construct the IR

def rename():
    """
        Renames source registers into Live Ranges. 
        Will print out the output. 
    :return: 
    """
    global IrHead, IrTail, MAXLIVE, MAX_VR, k
    SrToVr = []
    LU = []

    if verbose:
        print("max source: %d" % MAX_SOURCE)
    for i in range(MAX_SOURCE + 1):
        SrToVr.append(-1) # indicates invalid
        LU.append(-1)

    curr = IrTail
    if curr == None:
        print("The IR wasn't constructed")
    vr_name = 0
    curr_max = MAXLIVE

    index = tot_block_len
    while curr != None:
        curr_arr = curr.ir_data
        # print(curr_arr)
        # look through all the operands that we define first

        defined = get_defined(curr.opcode)
        for j in defined:
            if verbose:
                print("current register: %d" % curr_arr[j])
            if SrToVr[curr_arr[j]] == -1:
                curr_max -= 1
                # if we hit the definition of the SR, then we decrement curr_max
                SrToVr[curr_arr[j]] = vr_name
                vr_name += 1

            # set NU and VR of the operand
            curr_arr[j + 1] = SrToVr[curr_arr[j]] # virtual register
            curr_arr[j + 3] = LU[curr_arr[j]] # next use
            LU[curr_arr[j]] = -1 # NOTE: we represent infinity with -1.
            # LU[curr_arr[j]] = math.inf
            SrToVr[curr_arr[j]] = -1

        ###################################
        # TODO's:
        # have another function that takes in the IRArray and adds to the
            # mapping
        # how are we going to deal with entries that don't yet exist in the mappings?
            # ie for registers that are out of range
        # note: to set NU, VR and all that we're literally filling in the array!
            # when do we print it out though
        # ignore NOP. maybe ignore output?

        # calculating maxlive --> do we just decrement with
        # every definition on a line and increment with every first new use?
        #####################################

        # look through all the operands that we use next
        used = get_used(curr.opcode)

        for j in used:
            if verbose:
                print("current register: %d" % curr_arr[j])
            if SrToVr[curr_arr[j]] == -1:
                curr_max += 1
                # if we haven't see this operation before, then we
                # have encountered a new live range, and we increment curr_max
                SrToVr[curr_arr[j]] = vr_name
                vr_name += 1

            # set NU and VR of the operand
            curr_arr[j + 1] = SrToVr[curr_arr[j]] # virtual register
            curr_arr[j + 3] = LU[curr_arr[j]] # next use
            LU[curr_arr[j]] = index

        # after we've looked thru uses and def's, then we check if
        # MAXLIVE has changed
        if MAXLIVE < curr_max:
            MAXLIVE = curr_max
        index -= 1
        curr = curr.prev

    if MAXLIVE > k:
        k -= 1
        # we have to reserve a pr for spilling

    if vr_name != 0:
        MAX_VR = vr_name - 1

def print_operation(ir_entry, offset):
    """
    
    :param ir_entry: an IRArray object and member of the doubly linked list
    :param offset: corresponds to the register type that we want to print out. 
    0 = source, 1 = virtual, 2 = physical
    :return: 
    Nothing, but prints out the operation and its arguments
    """
    operations = ["load", "store","loadI", "add", "sub", "mult",
                  "lshift", "rshift", "output", "nop"]
    output = operations[ir_entry.opcode] + " "
    arg_types = get_arg_types(ir_entry.opcode)
    data = ir_entry.ir_data

    if arg_types[0] == 1:
        # register
        # true for every op except loadI, output, and nop
        output += "r%d " % data[0 + offset]
    elif arg_types[0] == 0:
        output += str(data[0]) + " "

    if arg_types[1] == 1:
        # register
        # true for any numerical operation
        output += ", r%d " % data[4 + offset]

    if arg_types[2] == 1:
        # register
        # will be true for every case other than output and nop
        output += "=> r%d" % data[8 + offset]
    print(output)

def get_arg_types(opcode):
    """
    
    :param opcode: opcode representing operation we want to print
    :return: a three part list indicating the type of each respective argument. 
    0 = constant
    1 = register
    None = empty
    """
    # operations = ["load", "store","loadI", "add", "sub", "mult",
    #               "lshift", "rshift", "output", "nop"]
    if opcode >= 0 and opcode <= 1:
        return [1,None,1]
    if opcode == 2:
        return [0,None,1]
    if opcode >= 3 and opcode <= 7:
        return [1,1,1]
    if opcode == 8:
        return [0,None, None]
    else:
        # NOP or invalid
        return [None, None, None]


def print_renamed_ir():
    """
        Will print out the IR after it's been renamed. 
        The new ILOC will look identical to the old one, except that each register 
        is defined exactly once. 
    :return: 
    """
    global IrHead
    # TODO: first implement it so that it only prints out the virtual
        # registers.
    curr = IrHead

    while curr != None:
        print_operation(curr,1)
        curr = curr.next

def check_pr_vr():
    """
    Will print out all the virtual registers in violation of the 
    PRToVR[VRToPR[vr]] = vr rule
    :return: 
    Returns true if the mapping wasn't violated, else false.
    """
    global VrToPr, PrToVr, MAX_VR
    valid = true
    for v in range(MAX_VR):
        if VrToPr[v] != -1 and PrToVr[VrToPr[v]] != v:
            valid = false
            print("VR %d violated. Corresponding pr %d mapped to %d" %
                  (v, VrToPr[v], PrToVr[VrToPr[v]]))
    return valid

def check_not_using_undefined():
    global IrHead, MAX_VR
    defined = []
    operations = ["load", "store","loadI", "add", "sub", "mult",
                  "lshift", "rshift", "output", "nop"]
    for i in range(MAX_VR + 1):
        defined.append(False)
    # print("Max vr %d" % MAX_VR)
    curr = IrHead
    line = 1

    while curr != None:
        uses = get_used(curr.opcode)
        for i in uses:
            if not defined[curr.ir_data[i + 1]]:
                print("Register r%d for %s at Line %d not defined before this" %
                      (curr.ir_data[i + 1], operations[curr.opcode], line))

        defined_ind = get_defined(curr.opcode)
        for i in defined_ind:
            # print("defined ind: %d" % curr.ir_data[i + 1])
            defined[curr.ir_data[i + 1]] = True

        curr = curr.next
        line += 1

def getAPR(vr, nu):
    """"""
    global VrToPr, PrToVr, PrNu
    # We should always conserve the property VrToPr[VrToPr[vr]] = vr
    # when VrToPr[vr] != invalid

    if pr_queue: # if stack isn't empty
        x = pr_queue.pop()
    else:
        # note: x is a physical register
        x = find_spill()
        spill(x)

    VrToPr[vr] = x
    PrToVr[x] = vr
    PrNu[x] = nu
    return x

def find_spill():
    """
    Returns the physical register which we should spill
    :return: 
    Number of physical register
    """
    global PrNu
    # TODO: first simple heuristic is most distantly used
    # note: we assume that every PR has a next use,
        # else we wouldn't be here
    curr_max = -1
    pr = -1
    for i in range(len(PrNu)):
        if PrNu[i] > curr_max:
            curr_max = PrNu[i]
            pr = i
        # todo: maybe add an additional check to look for clean values
    return pr

def get_spill_addr(vr):
    """
    Note: for the purposes of this lab, we assume that all memory addressed
    32768 and beyond is reserved for spilling. 
    :param vr: 
        VR for which we need to find a spill address. 
    :return: 
        The VR's spill address. 
    """
    return 32768 + 4 * vr

def check_prim_location(value):
    """
    Checks if the primary memory location has this value
    
    :param value: 
    :return: 
    """
    # TODO: finish this!!!! can we even check this?

def check_spill_addr(pr):
    """
    Check if the value has already been spilled
    :param vr: primary register we're trying to spill 
    :return: Returns boolean value
    """
    global PrToVr, spilled_bits
    vr = PrToVr[pr]
    if (spilled_bits & vr < 1) > 0:
        return True
    else:
        return False


def freeAPR(pr):
    """
    Will free a pr. Will also add it to the queue.
    Maintains the appropriate maps to keep them up to date and consistent. 
    :param pr: pr which we want to free. 
    :return: 
    """
    global VrToPr, PrToVr, PrNu, pr_queue
    VrToPr[PrToVr[pr]] = -1
    PrToVr[pr] = -1
    PrNu[pr] = -1
    pr_queue.append(pr)

def get_defined(opcode):
    """
        Gives us the indices of the defined registers corresponding to a given
        opcode
        :param opcode: operation code. 
        :return: 
        A list of indices
    """
    # operations = [0 "LOAD", 1 "STORE",2 "LOADI",3 "ADD",4 "SUB", 5"MULT",
    #               6 "LSHIFT", 7 "RSHIFT", 8 "OUTPUT", 9 "NOP",
    #               10 "CONSTANT", 11 "REGISTER", 12 "COMMA", 13"INTO", 14"ENDFILE"]
    if verbose:
        print("opcode %d" % opcode)

    elif opcode == 1 or opcode == 8 or opcode == 9:
        return []
    else:
        return [8]

def get_used(opcode):
    """
        Gives us the indices of the used registers corresponding to a given
        opcode
        :param opcode: operation code. 
        :return: 
    A list of indices
    """
    # operations = [0 "LOAD", 1 "STORE",2 "LOADI",3 "ADD",4 "SUB", 5"MULT",
    #               6 "LSHIFT", 7 "RSHIFT", 8 "OUTPUT", 9 "NOP",
    #               10 "CONSTANT", 11 "REGISTER", 12 "COMMA", 13"INTO", 14"ENDFILE"]

    if verbose:
        print("opcode %d" % opcode)
    if opcode == 1:
        # store operation
        return [0,8]
    elif opcode == 2 or opcode == 8 or opcode == 9:
        return []
    elif opcode == 0:
        return [0]
    else:
        return [0, 4]

def spill(x):
    """
    
    :param x: the physical register we want to spill
    :return: 
    Nothing. 
    Prints out the necessary ILOC to spill
    """
    global PrToVr, spilled_bits
    if check_spill_addr(x):
        return # we don't need to spill, as the value is already in spill addr
    # to spill, we loadI then store

    # record that we've spilled this virtual register
    spilled_bits = spilled_bits | (1 < PrToVr[x])

    # now print out!!
    print("loadI %d => r%d" % (get_spill_addr(PrToVr[x]), k + 1))
    # note: that we've reserved register k + 1
    print("store r%d => r%d" % (x, k+1))
    # note: we print out the values right away

# TODO: where are we going to want to add new operations, such as the
    # immediate load operation detailed on page 689?
    # would it be in spill?

def restore(vr, pr):
    """
    
    :param vr: virtual register which we're trying to restore 
    :param pr: physical register corresponding to this vr. 
    :return: 
    Nothing. 
    Will print out the ILOC code necessary to restore the value. 
    """
    print("loadI %d => r%d" % (get_spill_addr(vr), k + 1))
    print("load r%d => r%d" % (k + 1, pr))

def reg_alloc():
    """
        
    :return: 
    """
    # note: structure of registers in IR is <SR, VR, PR, NU>
    global MAX_VR, MAXLIVE, k, IrHead, pr_queue

    for i in range(MAX_VR):
        VrToPr.append(-1)

    for i in range(k):
        PrToVr.append(-1)
        PrNu.append(-1) # -1 represents infinity
        pr_queue.append(i)
        # push pr onto the queue

    curr = IrHead
    while curr != None:
        # we make a single pass through the operations
        curr_arr = curr.ir_data
        opcode = curr.opcode

        for i in get_used(opcode):
            # iterate through the uses and allocate
            if curr_arr[i + 2] == -1:
                # we assign a PR to those operations that don't have
                curr_arr[i + 2] = getAPR(curr_arr[i + 1], curr_arr[i + 3])
                restore(curr_arr[i + 1], curr_arr[i + 2])
                # TODO: check this usage of restore!!!!!

        for i in get_used(opcode):
            # check if this is the last use
            # reiterate over the uses and re-checks if any of them are
                # the last use of the VR. if so we free the PR
            if curr_arr[i + 3] == -1:
                free_pr = curr_arr[i + 2]
                freeAPR(free_pr)

        for i in get_defined(opcode):
            # allocate definitions
            curr_arr[i + 2] = getAPR()
        print_operation(curr.ir_data, 2)
        curr = curr.next
    # TODO: note -- are we going to do rematerialization??

def init_double_buf():
    """
    Will initialize the double buffer to be ready for reading. 
    :return: 
    """
    global i, buf1, buf2, buf1_len, buf2_len, f, EOF
    EOF = False
    i = 0
    buf1 = f.read(BUF_SIZE)
    buf2 = f.read(BUF_SIZE)
    buf1_len = len(buf1)
    buf2_len = len(buf2)

def get_char():
    """
    Sets char to whatever's at the index i. Appropriately searches in 
    buf1 or buf2
    :return: 
    """
    global BUF_SIZE, i, char, buf1, buf2
    if i < buf1_len:
        # everything up until index BUF_SIZE - 1 is in the first array
        char = buf1[i]
    else:
        char = buf2[i - buf1_len]

def next_char():
    """
        See pg 71 of the TB for a reference implementation
        Will also keep the buffer filled if necessary    
        Note that the only time that we should set char to "" is if we've hit EOF
        Otherwise, we'll always return the next character
    :return: 
        Returns nothing, but updates the global var char
    """
    global i, buf1, buf2, char, buf1_len, buf2_len, EOF, f, BUF_SIZE
    if EOF and i >= buf1_len + buf2_len:
        # note the condition above, for the case where we hit EOF but had to rollback
        char = ""
        return
    # print("length buf1 : %d  length buf2 : %d   i: %d" % (buf1_len, buf2_len, i))
    if i >= buf1_len + buf2_len:
        # print("i %d" % i)
        # ONLY if we've exhausted this buffer, refill it
        temp = f.read(BUF_SIZE)
        temp_len = len(temp)


        if verbose:
            print("Reading next buffer in:")
            # print(buf1)
            # print("buffer1 length:  %d" % len(buf1))
            # print("buffer2 length:  %d" % buf2_len)
        if temp == "":
            # if the end of file has been reached, then we don't overwrite
            # the buffer in the case that we need to rollback
            if verbose:
                print("Hit EOF")
            EOF = True
            f.close()
            char = ""
            return
        else:
            # then we're going to overwrite the 1st buffer with the 2nd one
            # and the second one with the new one
            if verbose:
                print("buffer2 length:  %d" % buf2_len)
            buf2_len = temp_len
            buf1_len = buf2_len
            i = buf1_len
            buf1 = buf2
            buf2 = temp
            # if len(buf2) < BUF_SIZE: # todo: used for debugging weir
            #     print("buffer 1 and length %d" % buf1_len)
            #     print(buf1)
            #     # print(buf1[-100:])
            #     print("buffer 2 and length %d" % buf2_len)
            #     print(buf2)
            #     print("char %s" % get_char())
                # reset the information we have about the buffer
    # if verbose:
    #     print("about to increment char")
    # i = (i + 1) % (2 * BUF_SIZE)
    # if we get down here, then we know that 0 < i < 2 * BUF_SIZE
    get_char()
    i += 1
    # if verbose:
    #     print("char   %s, next index: %d" % (char, i))

def rollback():
    """
        Will signal rollback error if index falls behind the fence. 
    :param i: the current index in the buffer 
    :return: 
        Will return -1 if i == fence and can no longer be rolled back. 
        Else will return 0. 
    """
    global i, char
    # if verbose:
    #     print("rolling back")
    if i <= 0:
        print("ERROR - can't rollback past the start of the current line")
        return -1
    else:
        i -= 1
        get_char()
        # if verbose:
        #     print("Rollback successful")
        #     print("char   %s" % char)

def detect_int():
    """    
        Detects and appends to the end of the constructed string 
        whatever integer we find in scanning. 
        Also advances the character pointer in the buffer. 
    :return:
        -1 if no integer was found.
        else returns a 0.
    """
    global curr_string
    found_num = False
    # Note: we have to make sure that we don't throw away the constant if it's 0
    # just throw away all the extra 0's
    is_zero = True
    while char == "0":
        # strip all the leading 0s
        next_char()
        found_num = True
    while is_number(char):
        is_zero = False
        found_num = True
        curr_string += char
        next_char()
    if is_zero and found_num:
        curr_string += "0"
    # we know that we're no longer on a number, so rollback once
    # for our next invocation of next_char()
    return found_num


def skip_comment():
    """
        Will skip ahead until we find a newline
    :return:
    """
    global char
    next_char()
    while char != "\n" and char != "":
        next_char()
    if verbose:
        print("comment skipped")


def is_number(s):
    """
    got from below link:
    https://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-float

    :param s: the string in question 
    :return: true or false
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def to_int(str_num):
    """
    :param str_num: a number represented as a string
    :return: 
    returns the integer representation of the string
    """
    # TODO: make efficient string to integer conversion --> is python's way good?

    try:
        num = int(str_num)
        return num
    except:
        return math.inf


def scan():
    """
    Currently uses single buffering. Will read in things line-by-line     
    :return: 
        Will return a list of <line, category, lexeme> triple-lists, 
        of the types <int, int, string>, respectively
        This list will be empty if there are any invalid tokens in the line.

    Note: this function also reports any lexical errors. 
    It will report all lexical errors on a line
    It is assumed that whatever text follows a lexical error and is unseparated
    by whitespace is also part of that same error
    """

    global buf1, curr_string, char, line_num, lex_errors, MAX_SOURCE
    token_list = []
    line_num += 1

    tokens_found = False
    # used to tell us whether any other tokens were found on this line
    # if any other were, then we don't want to add the end of file token
    lexical_err_present = False  # tells us if we want to throw away this line

    # if we see newline or carriage returns, then we know the
    #  current instruction is done
    next_char()
    while True:
        curr_string = ""
        found = False
        # indicates whether we've found an actual token
        while char == " " or char == "\t":
            # Whitespace is any combination of tabs and spaces
            # --> we'll skip past this.
            # if verbose:
            #     print("skimmming whitespace")
            next_char()
        if char == "\n":
            # if verbose:
            #     print("newline found")
            break

        if char == "":
            # if empty string then we've hit the end of file
            # ENDFILE 14
            token = [line_num, 14, ""]
            if verbose:
                print("EOF found")
                print("double buffer currently: \n %s" % buf2)
                print("value of i %d, curr char %s" % (i, char))
            if not tokens_found:
                token_list.append(token)
            return token_list
        elif char == "s":
            curr_string += char
            next_char()
            if char == "t":
                curr_string += char
                next_char()
                if char == "o":
                    curr_string += char
                    next_char()
                    if char == "r":
                        curr_string += char
                        next_char()
                        if char == "e":
                            curr_string += char
                            # STORE (1)
                            found = True  # we found a valid token!
                            token = [line_num, 1, curr_string]
                            next_char()
            elif char == "u":
                curr_string += char
                next_char()
                if char == "b":
                    curr_string += char
                    # SUB (4)
                    token = [line_num, 4, curr_string]
                    found = True
                    next_char()
        elif char == "l":
            curr_string += char
            next_char()
            if char == "s":
                curr_string += char
                next_char()
                if char == "h":
                    curr_string += char
                    next_char()
                    if char == "i":
                        curr_string += char
                        next_char()
                        if char == "f":
                            curr_string += char
                            next_char()
                            if char == "t":
                                curr_string += char
                                # if verbose:
                                #     print("Lshift found")
                                # LSHIFT (6)
                                token = [line_num, 6, curr_string]
                                found = True
                                next_char()
            elif char == "o":
                curr_string += char
                next_char()
                if char == "a":
                    curr_string += char
                    next_char()
                    if char == "d":
                        curr_string += char
                        next_char()
                        if char == "I":
                            curr_string += char
                            # LOADI (2)
                            token = [line_num, 2, curr_string]
                            # if verbose:
                            #     print("Loadi found")
                            found = True
                            next_char()
                        else:
                            # print("before load rollback %d buf1len %d buf2len %d"
                            #       % (i, len(buf1),buf2_len))
                            # then rollback here to LOAD (1)
                            # if verbose:
                            #     print("Load found")
                            if rollback() != -1:
                                token = [line_num, 0, curr_string]
                                found = True
                                next_char()
                            else:
                                return token_list
        elif char == "r":
            curr_string += char
            next_char()
            if char == "s":
                curr_string += char
                next_char()
                if char == "h":
                    curr_string += char
                    next_char()
                    if char == "i":
                        curr_string += char
                        next_char()
                        if char == "f":
                            curr_string += char
                            next_char()
                            if char == "t":
                                curr_string += char
                                # RSHIFT (7)
                                # if verbose:
                                #     print("Rshift found")
                                token = [line_num, 7, curr_string]
                                found = True
                                next_char()
            else:
                # check if we've found a REGISTER
                # (it's followed by an integer) (11)
                if is_number(char):
                    detect_int()
                    # we successfully found a number and attached it to curr_string
                    found = True
                    # if verbose:
                    #     print("Register found")
                    token = [line_num, 11, curr_string[1:]]
                    num_value = int(curr_string[1:])
                    if num_value > MAX_SOURCE:
                        MAX_SOURCE = num_value

                        # if we've found a register then shave off the "r" from
                    # the beginning

        elif char == "m":
            curr_string += char
            next_char()
            if char == "u":
                curr_string += char
                next_char()
                if char == "l":
                    curr_string += char
                    next_char()
                    if char == "t":
                        curr_string += char
                        # if verbose:
                        #     print("Mult found")
                        # MULT (5)
                        token = [line_num, 5, curr_string]
                        found = True
                        next_char()
        elif char == "a":
            curr_string += char
            next_char()
            if char == "d":
                next_char()
                curr_string += char
                if char == "d":
                    curr_string += char
                    # ADD (3)
                    # if verbose:
                    #     print("Add found")
                    token = [line_num, 3, curr_string]
                    found = True
                    next_char()

        elif char == "n":
            curr_string += char
            next_char()
            if char == "o":
                curr_string += char
                next_char()
                if char == "p":
                    curr_string += char
                    # NOP (9)
                    # if verbose:
                    #     print("Nop found")
                    token = [line_num, 9, curr_string]
                    found = True
                    next_char()
        elif char == "o":
            curr_string += char
            next_char()
            if char == "u":
                curr_string += char
                next_char()
                if char == "t":
                    curr_string += char
                    next_char()
                    if char == "p":
                        curr_string += char
                        next_char()
                        if char == "u":
                            curr_string += char
                            next_char()
                            if char == "t":
                                curr_string += char
                                # OUTPUT (8)
                                # if verbose:
                                #     print("Output found")
                                token = [line_num, 8, curr_string]
                                found = True
                                next_char()
        elif char == "=":
            curr_string += char
            next_char()
            if char == ">":
                # INTO (=>) (13)
                curr_string += char
                token = [line_num, 13, curr_string]
                # if verbose:
                #     print("Into found")
                found = True
                next_char()
        elif char == ",":
            curr_string += char
            # COMMA (,) (12)
            token = [line_num, 12, curr_string]
            # if verbose:
            #     print("Comma found")
            found = True
            next_char()
        elif char == "/":
            next_char()
            if char == "/":
                # found a comment -- burn through the rest of the line
                # and then return the tokens that we have so far
                # if verbose:
                #     print("Comment found")
                skip_comment()
                return token_list
        else:
            # check if we've hit a CONSTANT (10)
            if is_number(char):
                detect_int()
                token = [line_num, 10, curr_string]
                # if verbose:
                #     print("Constant found")
                found = True
                # we successfully found a number
            else:
                curr_string += char
                next_char()

        if not found:
            while char != " " and char != "\t" and char != "\n" and char != "" \
                    and char != "/":
                curr_string += char
                next_char()
                # todo: do we want this behavior??

            # then output an error here
            # append the last-read character onto curr_string
            if flag_level == 3:
                print("Lexical error: \"%s\" on line %d isn't a valid word"
                      % (curr_string, line_num))
            # print("Lexical error: \"%s\" on line %d isn't a valid word"
            #   % (curr_string, line_num))
            # if we find an error in the scanner, then we skip
            # the rest of the line --> this isn't what the reference does
            # but is permissible
            lexical_err_present = True
            # empty the token list. We've already reported the lexical error
            # if verbose:
            #     print("Unrecognized word:  %s" % curr_string)
            # TODO: do we want to skip this line, or just find the rest of the scanning errors?
            lex_errors += 1
            # next_char()

        else:
            # if verbose:
            #     print(
            #         "Recognized word:  %s on line %d" % (curr_string, line_num))
            token_list.append(token)
            tokens_found = True
            # next_char() # read the next character in
    if lexical_err_present:
        token_list = []
    return token_list

def print_token_list(token_list):
    """
    Prints out a list of tokens in the form line: <category, lexeme>
    :param token: token of format (line, category, lexeme)
    :return: 
    Nothing
    """
    num_to_cat = ["MEMOP", "MEMOP", "LOADI", "ARITHOP", "ARITHOP", "ARITHOP",
                  "ARITHOP", "ARITHOP",
                  "OUTPUT", "NOP",
                  "CONSTANT", "REGISTER", "COMMA", "INTO", "ENDFILE"]
    # iterate through the tokenlist again and print out everything

    for token in token_list:
        ln = token[0]
        cat = num_to_cat[token[1]]
        lexeme = token[2]
        print("%d: < %s, %s >" % (ln, cat, lexeme))


def parse():
    """
    This function is only called if we have a flag of priority higher than -s (0)
    Creates the intermediate representation of the ILOC
    :param token_list: list of tokens from the scanning phase
        of the form <line, category, lexeme>
        We need the line number to accurately 
        report any errors in the input file
    :return: 
     IR form is a doubly-linked list of arrays. 
     See end of lecture 3 for a representation
    """
    global IrTail, IrHead, EOF, lex_errors, syntax_errors, tot_block_len
    if verbose:
        time_start = datetime.now()

    token_list = scan()
    while True:  # while we haven't hit EOF
        # note: the only way that we
        # should stop parsing is if we hit the EOF token

        while len(token_list) == 0:
            # while the tokenlist is empty, keep calling scanner
            token_list = scan()

        # Tokens are of the form <line, category, lexeme>
        # if we get here, we know that the scanner was successful
        tok_cat = token_list[0][1]  # get category
        # if we encounter any errors in parsing, then we move onto the next line
        # operations = [0 "LOAD", 1 "STORE",2 "LOADI",3 "ADD",4 "SUB", 5"MULT",
        #               6 "LSHIFT", 7 "RSHIFT", 8 "OUTPUT", 9 "NOP",
        #               10 "CONSTANT", 11 "REGISTER", 12 "COMMA", 13"INTO", 14"ENDFILE"]
        if EOF and verbose:
            print("END OF FILE FOUND IN PARSER!!!")
        if tok_cat >= 0 and tok_cat <= 1:
            next_ir_arr = finish_memop(token_list)
        elif tok_cat == 2:
            next_ir_arr = finish_loadI(token_list)
        elif tok_cat >= 3 and tok_cat <= 7:
            next_ir_arr = finish_arithop(token_list)
        elif tok_cat == 8:
            next_ir_arr = finish_output(token_list)
        elif tok_cat == 9:
            next_ir_arr = finish_nop(token_list)
        elif tok_cat == 14:
            # if we found end of file, then we stop parsing
            break  # break out of the while loop to the return statements
        else:
            # then the beginning token isn't a valid start to an operation
            # print an error!
            syntax_errors += 1
            print("Error: line %d didn't start with a valid token. "
                  "Must be one of the following: "
                  "<MEMOP>|<LOADI>|<ARITHOP>|<OUTPUT>|<NOP>" % token_list[0][0])
            token_list = scan()
            continue
        # now add to the list of IR arrays.

        if next_ir_arr != None:
            tot_block_len += 1
            if IrHead == None:
                IrHead = next_ir_arr
                IrTail = next_ir_arr
            else:
                IrTail.link_next(next_ir_arr)
                IrTail = next_ir_arr
        token_list = scan()

    if flag_level == 1:
        if syntax_errors + lex_errors > 0:
            print("There were %d lexical errors and %d parsing errors - "
                  "could not construct the intermediate representation" %
                  (lex_errors, syntax_errors))
            # If we get down here and there are no errors
            # whatsoever, then print
        if verbose and syntax_errors + lex_errors > 0:
            print("Errors encountered, but now printing out the incomplete IR:")
            print_ir()
    if verbose:
        time_end = datetime.now()
        print("Total time take for parsing tokens:   %s"
              % str(time_end - time_start))


# operations = [0 "LOAD", 1 "STORE",2 "LOADI",3 "ADD",4 "SUB", 5"MULT",
#               6 "LSHIFT", 7 "RSHIFT", 8 "OUTPUT", 9 "NOP",
#               10 "CONSTANT", 11 "REGISTER", 12 "COMMA", 13"INTO", 14"ENDFILE"]

def finish_memop(token_list):
    """
    Opcode: 0 or 1
    :param token_list: list of tokens, starting with a MEMOP token. 
    The token list isn't guaranteed to have the right number of tokens. 
    :return: 
    If successful parsing, then returns an IRArray object. 
    Else, returns None

    Is expected to print out error statements 
    to diagnose faults with the token list. 
    """
    global syntax_errors
    if verbose:
        print("parsing Memop")
    valid = True
    tok_len = len(token_list)
    if tok_len != 4:
        print(
            "MEMOP operation on line %d is of incorrect length %d : should be in format: \n"
            "MEMOP REG INTO REG" % (token_list[0][0],len(token_list)))
        syntax_errors += 1
        return None

    r1 = None
    r3 = None

    # TODO: print out errors and note the line number
    # TODO: think about what we want the errors to say.
    # Do we want to note which argument was wrong?
    #  or should we just say it was all wrong?

    if token_list[1][1] == 11:
        r1 = to_int(token_list[1][2])
    else:
        valid = False
        print("first argument to memop on line %d expected to be REG"
              % token_list[0][0])

    if token_list[2][1] != 13:
        valid = False
        print("second argument to memop on line %d expected to be INTO" %
              token_list[0][0])

    if token_list[3][1] == 11:
        r3 = to_int(token_list[3][2])
    else:
        valid = False
        print("third argument to memop on line %d expected to be a register" %
              token_list[0][0])

    if valid:
        return IRArray(token_list[0][1], r1, None, r3)
    else:
        syntax_errors += 1
        return None


def finish_loadI(token_list):
    """
    Opcode: 2
    :param token_list: 
    :return: 
    """
    global syntax_errors
    if verbose:
        print("parsing loadI")
    valid = True
    tok_len = len(token_list)

    if tok_len != 4:
        syntax_errors += 1
        print(
            "LOADI operation on line %d is of incorrect length %d : should be in format: \n"
            "LOADI CONSTANT INTO REG" % (token_list[0][0],len(token_list)))
        return None

    r1 = None
    r3 = None

    if token_list[1][1] == 10:
        r1 = to_int(token_list[1][2])
    else:
        valid = False
        print("first argument to loadI on line %d expected to be CONSTANT" %
              token_list[0][0])

    if token_list[2][1] != 13:
        valid = False
        print("second argument to loadI on line %d expected to be INTO" %
              token_list[0][0])

    if token_list[3][1] == 11:
        r3 = to_int(token_list[3][2])
    else:
        valid = False
        print("third argument to loadI on line %d expected to be CONSTANT" %
              token_list[0][0])

    if valid:
        return IRArray(token_list[0][1], r1, None, r3)
    else:
        syntax_errors += 1
        return None


def finish_arithop(token_list):
    global syntax_errors
    if verbose:
        print("parsing arithop")
    valid = True
    tok_len = len(token_list)

    if tok_len != 6:
        print(
            "ARITHOP operation on line %d is of incorrect length %d: should be in format: \n"
            "ARITHOP REG COMMA REG INTO REG" % (token_list[0][0],len(token_list)))
        syntax_errors += 1
        return None

    r1 = None
    r2 = None
    r3 = None

    if token_list[1][1] == 11:
        r1 = to_int(token_list[1][2])
    else:
        valid = False
        print("first argument to arithop on line %d expected to be REG" %
              token_list[0][0])

    if token_list[2][1] != 12:
        # check for comma
        valid = False
        print("second argument to arithop on line %d expected to be COMMA" %
              token_list[0][0])

    if token_list[3][1] == 11:
        r2 = to_int(token_list[3][2])
    else:
        valid = False
        print("third argument to arithop on line %d expected to be REG" %
              token_list[0][0])

    if token_list[4][1] != 13:
        valid = False
        print("fourth argument to arithop on line %d expected to be REG" %
              token_list[0][0])

    if token_list[5][1] == 11:
        r3 = to_int(token_list[5][2])
    else:
        valid = False
        print("fifth argument to arithop on line %d expected to be REG" %
              token_list[0][0])

    if valid:
        # print(type(token_list[0][1]))
        return IRArray(token_list[0][1], r1, r2, r3)
    else:
        syntax_errors += 1
        return None


def finish_nop(token_list):
    global syntax_errors
    if verbose:
        print("parsing nop")

    # print("%d  %d  %s" % (token_list[0][0], token_list[0][1], token_list[0][2]))

    tok_len = len(token_list)
    if tok_len != 1:
        print(
            "NOP operation on line %d is of incorrect length %s: should be in format: \n"
            "NOP" % (token_list[0][0],len(token_list)))
        syntax_errors += 1
        return None
    else:
        # print(type(token_list[0][1]))
        return IRArray(token_list[0][1], None, None, None)


def finish_output(token_list):
    global syntax_errors
    if verbose:
        print("parsing output")
    valid = True
    tok_len = len(token_list)
    if tok_len != 2:
        print(
            "OUTPUT operation on line %d is of incorrect length %d: should be in format: \n"
            "OUTPUT CONSTANT" % (token_list[0][0],len(token_list)))
        syntax_errors += 1
        return None

    r1 = None
    r2 = None
    r3 = None
    if token_list[1][1] == 10:
        r1 = to_int(token_list[1][2])
    else:
        valid = False
        print("first argument to OUTPUT on line %d expected to be CONSTANT" %
              token_list[0][0])

    if valid:
        return IRArray(token_list[0][1], r1, r2, r3)
    else:
        syntax_errors += 1
        return None

if __name__ == "__main__":
    if verbose:
        print("running main")
    main()
