native class Object {}
native class List[T] {}
native string str[T](T x)
native void printstr(string s)

void print[T](T x) = {
  printstr(str(x))
}
