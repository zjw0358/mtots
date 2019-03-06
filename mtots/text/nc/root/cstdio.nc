inline** """
#include <stdio.h>
"""

native typedef $FILE

int $printf(const char* format, ...);
$FILE* $fopen(const char* filename, const char* mode);
int $fclose($FILE* stream);
int $fprintf($FILE* stream, const char* format, ...);
