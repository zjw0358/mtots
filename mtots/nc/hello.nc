from io import File
from io import open as fopen

trait A {
  int x
  string foo() = 'A.foo method'
}

trait B < A {
  string y
  string z
  string foo() = 'B.foo method'
}

class C < B {}

class D[T] {
  T t
}

void main() = {
  final c = new(C)
  print(c.foo())
  final a = new(A)
  print(a.foo())

  final d = new(D[string])
  # print(d->t)

  final file = fopen("setup.py", "r")
  print("Hello world!")
  final data = file.read()
  print(data)
  file.close()
}
