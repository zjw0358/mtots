inline inline_include "include" r"""
#include <stdio.h>
"""

inline inline_fwd "fwd" r"""
struct NCXX_ioZDFile;
"""

inline inline_hdr "hdr" r"""
struct NCXX_ioZDFile: NCXX_ZUpreludeZDObject {
  FILE *const file;
  NCXX_ioZDFile(FILE *f): file(f) {}
};
"""

native class File {}
