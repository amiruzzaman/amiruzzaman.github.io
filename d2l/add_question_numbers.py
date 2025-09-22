def add_question_numbers(text):
    """
    Adds question numbers to a block of text where each question starts with a capital letter.

    Args:
        text (str): The input text containing questions and answers.

    Returns:
        str: The text with question numbers added.
    """
    lines = text.strip().split('\n')
    numbered_lines = []
    question_number = 1
    
    # Iterate through the lines and add a question number to each new question.
    for line in lines:
        if line and line[0].isalpha() and line[0].isupper():
            numbered_lines.append(f"{question_number}. {line}")
            question_number += 1
        else:
            numbered_lines.append(line)
    
    return '\n'.join(numbered_lines)

# Example Usage:
text = """
What is the decimal value of binary 101?
*a) 5
b) 7
c) 6
d) 4
e) 3

Which base does binary use?
a) 8
*b) 2
c) 10
d) 16
e) 32

What is the hexadecimal equivalent of binary 1111?
a) E
b) 9
*c) F
d) D
e) B

What is the binary of decimal 6?
a) 111
b) 101
c) 100
*d) 110
e) 1111

Which hexadecimal digit represents decimal 13?
a) B
b) C
c) F
d) A
*e) D

Binary 111 equals decimal:
*a) 7
b) 6
c) 5
d) 4
e) 8

Binary numbers are made up of which digits?
a) 2 and 3
*b) 0 and 1
c) 1 and 2
d) 1 and 9
e) 5 and 6

Which hexadecimal value is equal to decimal 10?
a) 9
*b) A
c) B
d) C
e) D

What is (100111) in hexadecimal?
a) 29
b) 1D
*c) 27
d) 2F
e) 1C

Binary (111111111100) converts to which hexadecimal?
a) FFC
b) 1FF
c) 27C
*d) FFC
e) FFE

Which of the following is true about hexadecimal digits?
a) They only go up to 9
b) They are base 8
c) They are limited to binary mapping
*d) They range from 0–9 and A–F
e) They cannot represent letters

Decimal 12 corresponds to which hex digit?
a) B
b) A
*c) C
d) D
e) F

The binary (11101) equals which hexadecimal value?
a) 1F
*b) 1D
c) 2E
d) 1C
e) 1B

Which hexadecimal digit represents decimal 15?
a) D
b) E
c) B
*d) F
e) C

What is (111111111) in hexadecimal?
a) FFE
b) 27F
c) 3FF
d) FFC
*e) 1FF

In C, the first index of an array starts at:
*a) 0
b) 1
c) 2
d) -1
e) depends on compiler

Which keyword is used to allocate memory dynamically?
a) free
*b) malloc
c) sizeof
d) realloc
e) new

What does sizeof(array) return in C?
a) size of pointer
b) size of one element
*c) total size of array in bytes
d) index count
e) always 8

What is a pointer in C?
a) A variable holding binary numbers
b) A keyword
c) A structure
*d) A variable holding an address
e) An operator

What happens when you dereference a NULL pointer?
a) It prints zero
b) Nothing happens
c) It allocates memory
d) It compiles but crashes at runtime
*e) Segmentation fault

What does a[i] equal in pointer notation?
a) *(i + a)
*b) *(a + i)
c) (a * i)
d) *(a - i)
e) a[i+1]

What is the size of a pointer on a 64-bit system?
a) 2 bytes
b) 4 bytes
c) 6 bytes
*d) 8 bytes
e) 16 bytes

Which statement is true about arrays in C?
a) They support bounds checking
b) They can store different types
*c) They are homogenous
d) They automatically resize
e) They always initialize to zero

Strings in C are terminated with:
a) '\n'
b) space
c) EOF
*d) '\0'
e) None of these

Which function computes string length in C?
a) strcopy()
*b) strlen()
c) size()
d) strcpy()
e) strcount()

Which keyword is used to deallocate memory?
a) malloc
b) calloc
c) realloc
*d) free
e) delete

Which operator is used to get the address of a variable?
a) *
*b) &
c) ->
d) %
e) @

Which is a generic pointer type in C?
a) int*
b) char*
c) double*
d) void
e) null*

Which function allows resizing previously allocated memory?
a) malloc()
b) free()
*c) realloc()
d) calloc()
e) resize()

Passing an array to a function in C actually passes:
a) A copy of the array
*b) A pointer to the first element
c) The entire array with size
d) Reference only
e) Constant address

What is the output of sizeof(array) inside a function parameter?
a) Number of elements
*b) Size of pointer
c) Total size of array
d) Always 40
e) It causes error

Which of the following is NOT true about pointer arithmetic?
a) pointer + 1 increments by element size
b) pointer - 1 decrements by element size
c) It depends on type of pointer
*d) It increments by exactly 1 byte always
e) It is type-dependent

Which function allocates zero-initialized memory in C?
a) malloc()
*b) calloc()
c) realloc()
d) free()
e) initalloc()

A pointer storing no valid memory location is called:
a) Empty pointer
b) Nullified pointer
c) Wild pointer
*d) NULL pointer
e) Free pointer

Which symbol is used to dereference a pointer?
a) &
b) ->
c) %
*d) *
e) #

"""

numbered_text = add_question_numbers(text)
print(numbered_text)

# Add question numbers to the text
numbered_text = add_question_numbers(text)

# Save the numbered text to a file
file_name = "questions.txt"
try:
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(numbered_text)
    print(f"Successfully saved the numbered text to '{file_name}'")
except IOError as e:
    print(f"An error occurred while writing the file: {e}")