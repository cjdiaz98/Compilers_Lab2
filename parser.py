import sys
import math
from sys import stdin, stdout
from datetime import datetime
from collections import deque

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

class IRArray:
    def __init__(self, opcode, int1, int2, int3):
        """
        Initializes a doubly linked list

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
        global operations
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
        global operations
        reg_array = ["SR", "VR", "PR", "NU", "SR", "VR", "PR", "NU",
                     "SR", "VR", "PR", "NU"]

        output = operations[self.opcode] + "(" + str(self.opcode) + ")  "

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

    def remove_self(self):
        """
        Appropriately removes this node and updates the 
        head and tail of DLL

        Note: this is only to be used by the main DLL of our allocator. 
        :return: 
        """
        global IrHead, IrTail
        if not self.prev and not self.next:
            IrTail = None
            IrHead = None
            return

        if self.prev == None:
            self.next.prev = None
            IrHead = self.next
            return
        if self.next == None:
            self.prev.next = None
            IrTail = self.prev
            return

        self.next.prev = self.prev
        self.prev.next = self.next


def print_ir():
    """
    Prints out the intermediate representation in an 
    "appropriately human readable format"
     Note: also prints out all trailing IRArrays
    :return: None
    """
    global IrHead
    next_ir = IrHead

    while next_ir != None:
        print(next_ir.sr_to_string())
        # total_output += "\n" + next_ir.to_string()
        next_ir = next_ir.next
        # print(total_output)


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

        if temp == "":
            # if the end of file has been reached, then we don't overwrite
            # the buffer in the case that we need to rollback

            EOF = True
            f.close()
            char = ""
            return
        else:
            # then we're going to overwrite the 1st buffer with the 2nd one
            # and the second one with the new one
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

    # if we get down here, then we know that 0 < i < 2 * BUF_SIZE
    get_char()
    i += 1


def rollback():
    """
        Will signal rollback error if index falls behind the fence. 
    :param i: the current index in the buffer 
    :return: 
        Will return -1 if i == fence and can no longer be rolled back. 
        Else will return 0. 
    """
    global i, char
    if i <= 0:
        print("ERROR - can't rollback past the start of the current line")
        return -1
    else:
        i -= 1
        get_char()


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
            next_char()
        if char == "\n":
            break

        if char == "":
            # if empty string then we've hit the end of file
            # ENDFILE 14
            token = [line_num, 14, ""]
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

                            found = True
                            next_char()
                        else:
                            # print("before load rollback %d buf1len %d buf2len %d"
                            #       % (i, len(buf1),buf2_len))
                            # then rollback here to LOAD (1)

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
                found = True
                next_char()
        elif char == ",":
            curr_string += char
            # COMMA (,) (12)
            token = [line_num, 12, curr_string]
            found = True
            next_char()
        elif char == "/":
            next_char()
            if char == "/":
                # found a comment -- burn through the rest of the line
                # and then return the tokens that we have so far
                skip_comment()
                return token_list
        else:
            # check if we've hit a CONSTANT (10)
            if is_number(char):
                detect_int()
                token = [line_num, 10, curr_string]

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
            lex_errors += 1
            # next_char()

        else:
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

    valid = True
    tok_len = len(token_list)
    if tok_len != 4:
        print(
            "MEMOP operation on line %d is of incorrect length %d : should be in format: \n"
            "MEMOP REG INTO REG" % (token_list[0][0], len(token_list)))
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
    valid = True
    tok_len = len(token_list)

    if tok_len != 4:
        syntax_errors += 1
        print(
            "LOADI operation on line %d is of incorrect length %d : should be in format: \n"
            "LOADI CONSTANT INTO REG" % (token_list[0][0], len(token_list)))
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

    valid = True
    tok_len = len(token_list)

    if tok_len != 6:
        print(
            "ARITHOP operation on line %d is of incorrect length %d: should be in format: \n"
            "ARITHOP REG COMMA REG INTO REG" % (
            token_list[0][0], len(token_list)))
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

    # print("%d  %d  %s" % (token_list[0][0], token_list[0][1], token_list[0][2]))

    tok_len = len(token_list)
    if tok_len != 1:
        print(
            "NOP operation on line %d is of incorrect length %s: should be in format: \n"
            "NOP" % (token_list[0][0], len(token_list)))
        syntax_errors += 1
        return None
    else:
        # print(type(token_list[0][1]))
        return IRArray(token_list[0][1], None, None, None)


def finish_output(token_list):
    global syntax_errors

    valid = True
    tok_len = len(token_list)
    if tok_len != 2:
        print(
            "OUTPUT operation on line %d is of incorrect length %d: should be in format: \n"
            "OUTPUT CONSTANT" % (token_list[0][0], len(token_list)))
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
