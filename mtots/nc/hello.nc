from io import File
from io import open as fopen
from io import close as fclose
from io import read as fread

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

void main() = {
  final c = new(C)
  print(c.foo())
  final a = new(A)
  print(a.foo())

  final file = fopen("setup.py", "r")
  print("Hello world!")
  final data = fread(file)
  print(data)
  fclose(file)
}
