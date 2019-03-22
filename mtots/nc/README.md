## Running sanity test

python3 -m mtots.nc mtots/nc/hello.nc > main.cc && g++ -Wall -Werror -Wpedantic -std=c++11 main.cc && ./a.out

## Stages

Macros are not yet implemented, but once they are,
semantically the compilation stages should look like this:

  '.nc' source
    |
    parse
    v
  CST
    |
    evaluate macros
    v
  CST (but no more Macro nodes)
    |
    resolve
      a. global symbols
      b. types
      c. expressions
    v
  AST
    |
    code-generator
      could potentially vary but
      right now, only C++11 blob
      backend is implemented
    v
  Target source
    (e.g. C++11 blob)


## TODO

* Macros
  This would involve syntax that will probably look something like

  ```
  def some_macro_var = [1, 2, 3]

  def some_macro_func(cls) = {
      ...
  }

  @some_macro_func
  class Foo {
  }
  ```

  The macros would work purely on the CST, and not at all on the AST,
  since, working with resolved types would get complicated because
  they require multiple passes to work with properly.
  With CSTs, the order of how the macros should be evaluated is
  a lot clearer.
  Furthermore, the CST is cleaner with everything being immutable.

  Importing macros should use a different syntax that normal imports.
  Probably something like

  ```
  @import foo.module_name as module_alias

  def some_macro_func() = {
    module_alias.some_other_func()
  }
  ```

  Since CSTs should be importable on their own, resolving macros should
  not require looking up all the files for normal imports.
  Just looking up macro imports should be enough.

  Definitely interested in writing a `dataclass` macro that will
  behave like `dataclass(frozen=True)` in Python or `case class` in
  Scala.

* Metadata dump
  It would be useful to be able to extract metadata from various
  stages of the build process.
  In particular:
  * CST right after parse
  * CST right after macro evaluation
  * Explicitly exported metadata right after macro evaluation
    * This information could be used for builds
      E.g. for Android targets, it can specify which classes
      are intents, etc. so that the information that may
      need to go into separate configuration files can be
      specified directly in the code through macro calls.
  * State of all file level macro variables after macro evaluation
  * Dump of the AST with all processed semantic information

* Closures
  Closures/lambdas are pretty useful to have, generally.
  In particular, I plan on not adding exceptions.
  In order for error handling to work reasonably in cases
  like these, I really do need lambdas here to make
  the api look nicer.

* No Exceptions
  Well, this is already true, but I plan on not adding throw/catch
  in the language even in the future.
  It can be useful to have, but it can break APIs, and from a purist
  standpoint it's also kind of weird because you can end up constructing
  code that depend on exceptions for normal flow (e.g. Python's normal
  way of doing things), which can be convenient, but in a language
  like this where it's unknown exactly what the underlying implementation
  will looks like depending on targeted backend, it can get
  unexpectedly expensive.

* Coroutines (maybe)
  It may be useful to have something like Python's asymmetric coroutines.
  In particular, it would be useful for
    * cleanly defining iterators
    * async/await
    * being able write code that look like throw/catch
  Coroutines would be really really fun to have, but they're also
  rather tricky to implement in all targets.
  To implement coroutines in a language that doesn't already have similar
  features (e.g. C/C++ or Java), expressions would have to be unrolled
  into statements and all variables noted carefully so that they could
  be implemented with classes. Would be quite a bit of work.

* Formatting through unparsing the CST
  Formatting nc code can be really simple by simply parsing into CST
  then unparsing the CST back into the code.
  This is the reason why comments are part of the grammar and not
  simply discarded -- this way the places where comments can appear
  are actually restricted.
  The only other thing needed on the parser side is keeping track of
  repeats of NEWLINEs, to potentially preserve empty line formatting.
  However, this shouldn't restrict the space of acceptable grammars,
  so fixing this isn't urgent (the comments issue was urgent, because
  it could potentially create many uses of comments that would not
  be acceptable for the parser simple).
