
Unfortunately, to get namespaces and static typing working as simply
as possible, I actually have three separate parsers.

fwd_parser -- this one runs first. All this does is figure out what symbols
are exported in given file. Essentially information you might see in
C/C++ forward declarations. This is to simplify dealing with namespaces.

hdr_parser -- this one runs second. The parser will return a callback that
when fed the output of fwd_parser, will parse everything but
function/method bodies. Once this one finishes, you should have the types
and structures of all functions, classes and global variables.

src_parser -- this one runs third. The parser will return a callback that
when fed the output of hdr_parser, will parse everything.
