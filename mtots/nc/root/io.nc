inline inline_include "include" r"""
#include <stdio.h>
#include <stdlib.h>
"""

inline inline_fwd "fwd" r"""
struct NCXX_ioZDFile;
"""

inline inline_hdr "hdr" r"""
struct NCXX_ioZDFile: NCXX_ZUpreludeZDObject {
  const NCX_STRING path;
  const NCX_STRING mode;
  const bool should_close;
  FILE *const filep;
  bool already_closed;
  NCXX_ioZDFile(NCX_STRING p, NCX_STRING m, bool sc, FILE *fp):
    path(p),
    mode(m),
    should_close(sc),
    filep(fp),
    already_closed(false) {}
  ~NCXX_ioZDFile() {}
  NCX_VOID NCXX_close() {
    if (should_close && !already_closed) {
      already_closed = true;
      fclose(filep);
    }
    return 0;
  }
  NCX_BOOL NCXX_eof() {
    return feof(filep);
  }
  NCX_STRING NCXX_read() {
    size_t buffer_size = 1024;
    size_t filled_size = 0;
    char *buffer = (char*) malloc(sizeof(buffer_size));
    do {
      if (buffer_size < 1024 * 8 * 8) {
        buffer_size *= 8;
      } else {
        buffer_size *= 2;
      }
      buffer = (char*) realloc(buffer, buffer_size);
      filled_size +=
        fread(buffer + filled_size, 1, buffer_size - filled_size, filep);
    } while (filled_size == buffer_size);
    NCX_STRING ret = NCX_mkstr(buffer);
    free(buffer);
    return ret;
  }
};
NCX_PTR<NCXX_ioZDFile> NCXX_ioZDopen(NCX_STRING path, NCX_STRING mode);
"""

inline inline_src "src" r"""
NCX_PTR<NCXX_ioZDFile> NCXX_ioZDopen(NCX_STRING path, NCX_STRING mode) {
  FILE *fp = fopen(path->c_str(), mode->c_str());
  NCX_PTR<NCXX_ioZDFile> file =
    NCX_MKPTR<NCXX_ioZDFile>(path, mode, true, fp);
  return file;
}
"""

native class File {
  void close()
  bool eof()
  string read()  # TODO: return Try[string] instead
}
native File open(string path, string mode)
