native trait Object {}
native class Try[T] {}
native class List[T] {}
native Try[T] YES[T](T t)
native Try[T] NO[T](string message)
native string str[T](T x)
native void printstr(string s)

void print[T](T x) = {
  printstr(str(x))
}

inline inline_include "include" r"""// <generated by nc transpiler>
#include <iostream>
#include <memory>
#include <string>
"""

inline inline_fwd "fwd" r"""
#define NCX_MKPTR std::make_shared
#define NCX_YES NCXX_ZUpreludeZDYES
#define NCX_NO NCXX_ZUpreludeZDNO
using NCX_VOID = int;
using NCX_BOOL = bool;
using NCX_INT = long;
using NCX_DOUBLE = double;
using NCX_STRING = std::shared_ptr<std::string>;
template <class T> using NCX_PTR = std::shared_ptr<T>;
struct NCXX_ZUpreludeZDObject;
template <class T> struct NCXX_ZUpreludeZDTry;
using NCX_Object = NCXX_ZUpreludeZDObject;
template <class T> using NCX_Try = NCXX_ZUpreludeZDTry<T>;
"""

inline inline_hdr "hdr" r"""
struct NCXX_ZUpreludeZDObject {
  virtual NCX_STRING NCX_str();
  virtual ~NCXX_ZUpreludeZDObject() {}
};
template<class T> struct NCXX_ZUpreludeZDTry: NCXX_ZUpreludeZDObject {
  T value;
  NCX_STRING error;
  bool ok() const {
    return error;
  }
};
template<class T> NCX_PTR<NCX_Try<T>> NCXX_ZUpreludeZDYES(T t);
template<class T> NCX_PTR<NCX_Try<T>> NCXX_ZUpreludeZDNO(NCX_STRING message);
NCX_VOID NCXX_ZUpreludeZDprintstr(NCX_STRING s);
NCX_STRING NCX_mkstr(const char *s);
template <class T> NCX_STRING NCXX_ZUpreludeZDstr(T x);
template <> NCX_STRING NCXX_ZUpreludeZDstr(NCX_STRING s);
"""

inline inline_src "src" r"""
template<class T> NCX_PTR<NCX_Try<T>> NCXX_ZUpreludeZDYES(T t) {
  auto ret = NCX_MKPTR<NCX_Try<T>>();
  ret->value = t;
  return ret;
}
template<class T> NCX_PTR<NCX_Try<T>> NCXX_ZUpreludeZDNO(NCX_STRING message) {
  auto ret = NCX_MKPTR<NCX_Try<T>>();
  ret->error = message;
  return ret;
}
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
template <class T> NCX_STRING NCXX_ZUpreludeZDstr(T x) {
  return x->NCX_str();
}
template <> NCX_STRING NCXX_ZUpreludeZDstr(NCX_STRING s) {
  return s;
}
"""

inline inline_epilogue "epilogue" r"""
int main() {
  NCXX_ZUmainZDmain();
}
"""
