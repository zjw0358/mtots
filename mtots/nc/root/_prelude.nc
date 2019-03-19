inline inline_include "include" r"""// <generated by nc transpiler>
#include <iostream>
#include <memory>
#include <string>
"""

inline inline_fwd "fwd" r"""
using NCX_VOID = int;
using NCX_BOOL = bool;
using NCX_INT = long;
using NCX_DOUBLE = double;
using NCX_STRING = std::shared_ptr<std::string>;
struct NCXX_ZUpreludeZDObject;
template <class T> NCX_STRING NCXX_ZUpreludeZDstr(T x) {
    return x->NCX_str();
}
template <> NCX_STRING NCXX_ZUpreludeZDstr(NCX_STRING s) {
    return s;
}
"""

inline inline_hdr "hdr" r"""
struct NCXX_ZUpreludeZDObject {
    virtual NCX_STRING NCX_str();
};
NCX_VOID NCXX_ZUpreludeZDprintstr(NCX_STRING s);
NCX_STRING NCX_mkstr(const char *s);
"""

inline inline_src "src" r"""
NCX_STRING NCX_mkstr(const char *s) {
    return std::make_shared<std::string>(s);
}
NCX_STRING NCXX_ZUpreludeZDObject::NCX_str() {
    return NCX_mkstr("<Object>");
}
NCX_VOID NCXX_ZUpreludeZDprintstr(NCX_STRING s) {
    std::cout << *s << std::endl;
    return 0;
}
"""

inline inline_epilogue "epilogue" r"""
int main() {
    NCXX_ZUmainZDmain();
}
"""

native class Object {}
native class List[T] {}
native string str[T](T x)
native void printstr(string s)

void print[T](T x) = {
  printstr(str(x))
}
