from . import cst as cst_
from .scopes import Scope
from mtots import util
from mtots.parser import base
from mtots.util import dataclasses
from mtots.util import typing
from mtots.util.dataclasses import dataclass


class Type:
    def usable_as(self, other_type):
        return self is other_type


@typing.enforce
@dataclass(frozen=True)
class PrimitiveType(Type):
    name: str

    def __str__(self):
        return f'(primitive-type {self.name})'


VOID = PrimitiveType('void')
BOOL = PrimitiveType('bool')
INT = PrimitiveType('int')
DOUBLE = PrimitiveType('double')
STRING = PrimitiveType('string')


def get_reified_bindings(*, type_parameters, type_arguments):
    bindings = {}
    for param, arg in zip(type_parameters, type_arguments):
        bindings[param] = arg
    return bindings


def apply_reified_bindings(*, type, bindings):
    return _apply_reified_bindings(type, bindings)


class BaseVariableDeclaration:
    pass


@dataclass
class Markable:
    mark: typing.Optional[base.Mark] = dataclasses.field(
        compare=False,
        repr=False,
    )


@dataclass
class TypeParameter(Type, Markable):
    name: str
    base: typing.Optional[Type] = dataclasses.field(
        repr=False,
    )

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def __str__(self):
        if self.base is None:
            return f'(type-param {self.name})'
        else:
            return f'(type-param {self.name}: {self.base})'


@dataclass(frozen=True)
class Expression(base.Node):
    type: Type


@typing.enforce
@dataclass(frozen=True)
class Inline(base.Node):
    name: str
    type: str
    text: str


@typing.enforce
@dataclass
class Field(Markable):
    type: Type
    name: str


@dataclass
class Parameter(Markable, BaseVariableDeclaration):
    type: Type
    name: str
    mutable = True


@dataclass
class Function(Markable):
    cst: cst_.Function = dataclasses.field(repr=False, compare=False)
    scope: Scope
    native: bool
    return_type: Type
    name: str
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    generic: bool
    parameters: typing.List[Parameter]
    body: typing.Optional[Expression]


@typing.enforce
@dataclass
class Method(Markable):
    cst: cst_.Method = dataclasses.field(repr=False, compare=False)
    scope: Scope
    abstract: bool
    return_type: Type
    name: str
    parameters: typing.List[Parameter]
    body: typing.Optional[Expression]


@dataclass
class Class(Type, Markable):
    cst: cst_.Class = dataclasses.field(repr=False, compare=False)
    native: bool
    inheritable: bool
    scope: Scope
    name: str
    base: typing.Optional[Type]
    type_parameters: typing.Optional[typing.List[TypeParameter]]
    generic: bool
    own_fields: typing.Dict[str, Field]
    all_fields: typing.Dict[str, Field]
    own_methods: typing.Dict[str, Method]
    all_methods: typing.Dict[str, Method]

    def usable_as(self, other_cls):
        if not isinstance(other_cls, Class):
            return False

        while self is not None and self is not other_cls:
            self = self.base
        return self is other_cls

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return hash(self)

    def __str__(self):
        return f'(class {self.name})'


@typing.enforce
@dataclass(frozen=True)
class ReifiedType(Type, base.Node):
    class_: Class
    type_arguments: typing.Tuple[Type, ...]

    _base = None
    _bindings = None
    _all_fields = None

    def usable_as(self, other):
        return (
            isinstance(other, (ReifiedType, Class)) and
            (self == other or
                other.base is not None and self.usable_as(other.base))
        )

    @property
    def base(self):
        if self._base is None:
            if self.class_.base is not None:
                bindings = get_reified_bindings(
                    type_parameters=self.class_.type_parameters,
                    type_arguments=self.type_arguments,
                )
                self._base = apply_reified_bindings(
                    type=self.class_.base,
                    bindings=bindings,
                )
        return self._base

    @property
    def bindings(self):
        if self._bindings is None:
            self._bindings = get_reified_bindings(
                type_parameters=type_.class_.type_parameters,
                type_arguments=type_.type_arguments,
            )
        return self._bindings

    @property
    def all_fields(self):
        if self._all_fields is None:
            field_map = {}
            bindings = self.bindings
            for key, raw_field in class_.all_fields.items():
                field_type = apply_reified_bindings(
                    type=raw_field.type,
                    bindings=bindings,
                )
                field = Field(
                    mark=raw_field.mark,
                    type=field_type,
                    name=raw_field.name,
                )
                field_map[key] = raw_field
            self._all_fields = field_map
        return self._all_fields

    @property
    def all_methods(self):
        if self._all_methods is None:
            methods_map = {}
            bindings = self.bindings
            for key, raw_method in class_.all_methods.items():
                parameters = []
                for raw_parameter in raw_method.parameters:
                    parameters.append(Parameter(
                        mark=raw_parameter.mark,
                        type=apply_reified_bindings(
                            type=raw_parameter.type,
                            bindings=bindings,
                        ),
                        name=raw_parameter.name,
                    ))
                method = Method(
                    mark=raw_method.mark,
                    cst=raw_method.cst,
                    scope=raw_method.scope,
                    abstract=raw_method.abstract,
                    return_type=apply_reified_bindings(
                        type=raw_method.type,
                        bindings=bindings,
                    ),
                    name=raw_method.name,
                    parameters=parameters,
                    body=None,
                )
                methods_map[method.name] = method
            self._all_methods = methods_map
        return self._all_methods

##############################################################################
# Expressions
##############################################################################


@typing.enforce
@dataclass(frozen=True)
class LocalVariableDeclaration(base.Node, BaseVariableDeclaration):
    mutable: bool
    type: Type
    name: str
    expression: Expression


@typing.enforce
@dataclass(frozen=True)
class Block(Expression):
    expressions: typing.Tuple[typing.Union[
        Expression, LocalVariableDeclaration], ...]


@typing.enforce
@dataclass(frozen=True)
class Int(Expression):
    value: int


@typing.enforce
@dataclass(frozen=True)
class String(Expression):
    value: str


@typing.enforce
@dataclass(frozen=True)
class LocalVariable(Expression):
    declaration: typing.Union[Parameter, LocalVariableDeclaration]


@typing.enforce
@dataclass(frozen=True)
class New(Expression):
    pass


@typing.enforce
@dataclass(frozen=True)
class FunctionCall(Expression):
    function: Function
    type_arguments: typing.Optional[typing.Tuple[Type, ...]]
    arguments: typing.Tuple[Expression, ...]


@typing.enforce
@dataclass(frozen=True)
class MethodCall(Expression):
    owner: Expression
    method: Method
    arguments: typing.Tuple[Expression, ...]


@util.multimethod(1)
def _apply_reified_bindings(on):

    @on(PrimitiveType)
    def r(type_, bindings):
        return type_

    @on(Class)
    def r(type_, bindings):
        return type_

    @on(ReifiedType)
    def r(type_, bindings):
        return ReifiedType(
            mark=type_.mark,
            class_=type_.class_,
            type_arguments=[
                _apply_reified_bindings(t, bindings)
                for t in type_.type_arguments
            ],
        )

    @on(TypeParameter)
    def r(type_, bindings):
        if type_ in bindings:
            return bindings[type_]
        else:
            raise TypeError(f'FUBAR: Unbound type variable: {type_}')
