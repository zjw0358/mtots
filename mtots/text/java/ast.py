from mtots.parser import base
from mtots.util.dataclasses import dataclass
from mtots.util.typing import List, Optional


@dataclass(frozen=True)
class CompilationUnit(base.Node):
    package_declaration: 'PackageDeclaration'
    import_declarations: List['ImportDeclaration']
    type_declarations: List['TypeDeclaration']


@dataclass(frozen=True)
class PackageDeclaration(base.Node):
    name: str


@dataclass(frozen=True)
class ImportDeclaration(base.Node):
    static: bool
    pattern: str


@dataclass(frozen=True)
class TypeDeclaration(base.Node):
    # NOTE: Technically, you can mix annotations and
    # simple modifiers, but this is not common practice,
    # so I'll separate them like this for now.
    modifiers: List['Modifier']
    short_name: str


class Modifier(base.Node):
    pass


@dataclass(frozen=True)
class SimpleModifier(Modifier):
    name: str


@dataclass(frozen=True)
class Annotation(Modifier):
    pass


@dataclass(frozen=True)
class ClassDeclaration(TypeDeclaration):
    type_parameters: List['TypeParameter']
    super: Optional[str]
    interfaces: List[str]
    body: List['ClassBodyDeclaration']


@dataclass(frozen=True)
class Block(base.Node):
    "Executable Java statements, but unparsed as text"
    pass
