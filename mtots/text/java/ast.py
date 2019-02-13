from mtots.text import base
from mtots.util.dataclasses import dataclass
from typing import List, Optional


@dataclass
class CompilationUnit(base.Node):
    package_declaration: 'PackageDeclaration'
    import_declarations: List['ImportDeclaration']
    type_declarations: List['TypeDeclaration']


@dataclass
class PackageDeclaration(base.Node):
    name: str


@dataclass
class ImportDeclaration(base.Node):
    static: bool
    pattern: str


@dataclass
class TypeDeclaration(base.Node):
    # NOTE: Technically, you can mix annotations and
    # simple modifiers, but this is not common practice,
    # so I'll separate them like this for now.
    modifiers: List['Modifier']
    short_name: str


class Modifier(base.Node):
    pass


@dataclass
class SimpleModifier(Modifier):
    name: str


@dataclass
class Annotation(Modifier):
    pass


@dataclass
class ClassDeclaration(TypeDeclaration):
    type_parameters: List['TypeParameter']
    super: Optional[str]
    interfaces: List[str]
    body: List['ClassBodyDeclaration']


@dataclass
class Block(base.Node):
    "Executable Java statements, but unparsed as text"
    pass
