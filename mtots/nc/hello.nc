from io import File
from io import open as fopen
from io import close as fclose
from io import read as fread

void main() = {
  final file = fopen("setup.py", "r")
  print("Hello world!")
  final data = fread(file)
  print(data)
  fclose(file)
}
