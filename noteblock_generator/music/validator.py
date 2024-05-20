from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Iterable, Literal, TypeVar, final

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    NonNegativeInt,
    PositiveInt,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic.alias_generators import to_camel

from .loader import PATH_KEY, REF_KEY


def validate(raw_data: object):
    return T_Composition.model_validate(raw_data)  # TODO: error handling


@final
class T_MultiValue(tuple["T", ...]):
    def __add__(self, other: Iterable[T]):
        return T_MultiValue(super().__add__(tuple(other)))


T = TypeVar("T")
T_Reset = Literal["$reset"]
T_StaticProperty = T | T_Reset | None
if TYPE_CHECKING:
    T_Positional = T | T_MultiValue[T]
else:  # for pydantic
    T_Positional = T | Annotated[list[T], Field(min_length=1), AfterValidator(T_MultiValue)]
T_Delete = Literal["$del"]
T_PositionalProperty = T_Positional[T_StaticProperty[T] | T_Delete]
T_Tuple = tuple[T, ...]
T_Duration = int
T_NoteValue = int
T_Name = str
T_Time = (
    PositiveInt
    | Annotated[
        str,
        Field(
            pattern=(
                "^"
                "("  # begin repeat
                "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
                "[1-9]\\d*b?"  # number of ticks or of beats
                ")+"  # end repeat
                "$"
            )
        ),
    ]
)
T_Beat = Annotated[int, Field(ge=1, lt=12)]
T_BeatRate = Annotated[int, Field(ge=6, lt=2500)]
T_TickRate = Annotated[float, Field(ge=0.1, lt=500.0)]
T_Tempo = T_BeatRate | tuple[T_BeatRate, Literal["bpm"]] | tuple[T_TickRate, Literal["tps"]]
T_Instrument = Annotated[
    # Format: <instrument 1> / <instrument 2> / etc,
    # e.g. "harp/guitar/flute".
    # Meaning: try <instrument 1> for the note, if out of range try <instrument 2>, etc.
    str,
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            # a valid noteblock instrument
            "(bass|didgeridoo|guitar|banjo|bit|harp|iron_xylophone|pling|cow_bell|flute|bell|chime|xylophone|basedrum|hat|snare)"
            "(\\s*/\\s*|$)"  # "/" or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_StaticAbsoluteDynamic = Annotated[int, Field(ge=0, le=6)]
T_VariableAbsoluteDynamic = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "[0-6]"  # dynamic value: 0 to 6
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")+"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_StaticRelativeDynamic = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to raise, - to lower
            "[0-6]"  # a value from 0 to 6
            "$"
        )
    ),
]
T_VariableRelativeDynamic = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "[+-]?"  # optional: + to raise, - to lower
            "[0-6]"  # a value from 0 to 6
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")+"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_AbsoluteDynamic = T_StaticAbsoluteDynamic | T_VariableAbsoluteDynamic
T_RelativeDynamic = T_StaticRelativeDynamic | T_VariableRelativeDynamic
T_StaticDynamic = T_StaticAbsoluteDynamic | T_StaticRelativeDynamic
T_VariableDynamic = T_VariableAbsoluteDynamic | T_VariableRelativeDynamic
T_Dynamic = T_StaticDynamic | T_VariableDynamic
T_AbsoluteTranspose = (
    int
    | Annotated[
        str,
        Field(
            pattern=(
                "^"
                "\\{[+-]?\\d+\\}"  # a value in {}
                "[\\?|!]?"  # ? to turn on auto transpose, ! to turn off, omit to keep the same
                "$"
            )
        ),
    ]
)
T_AutoTranspose = (
    bool
    | Annotated[
        str,
        Field(pattern="^[\\?!]$"),  # ? to turn on auto transpose, ! to turn off
    ]
)
T_RelativeTranspose = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to raise, - to lower
            "\\d+"  # a value
            "[\\?|!]?"  # ? to turn on auto transpose, ! to turn off, omit to keep the same
            "$"
        )
    ),
]
T_Transpose = T_AutoTranspose | T_AbsoluteTranspose | T_RelativeTranspose
T_AbsoluteSustain = (
    bool
    | int
    | Annotated[
        str,
        Field(pattern=("^(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)$")),  # number of ticks or of beats
    ]
)
T_RelativeSustain = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to increase, - to decrease
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            "$"
        )
    ),
]
T_Sustain = T_AbsoluteSustain | T_RelativeSustain
T_BarDelimiter = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "\\|{1,2}"  # | to assert bar line, or || to also rest for the entire bar
            "(\\s*\\d+)?"  # optionally assert bar number
            "\\!?"  # optional "!" to force assertion
            "$"
        )
    ),
]
T_Rest = Annotated[
    str,  # format: R <duration>
    Field(
        pattern=(
            "^"
            "[rR]"  # R for rest
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")*"  # end duration
            "$"
        )
    ),
]
T_NoteName = Annotated[
    str,  # format: <note> <duration>
    Field(
        pattern=(
            "^"
            "[a-gA-G]"  # pitch A to G
            "(bb|b|s|ss)?"  # optional accidentals: double flats, flat, sharp, double sharps
            "("  # begin octave
            "[1-7]?"  # absolute: noteblock's octaves range from 1 to 7
            "|"  # or
            "(_*|\\^*)"  # relative to instrument's range: _ to lower, ^ to raise
            ")"  # end octave
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")*"  # end duration
            "$"
        )
    ),
]
T_MultipleNotes = Annotated[
    str,  # format: <note> <duration>, <note> <duration>, etc.
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "("  # begin note name
            "[rR]"  # R for rest
            "|"  # or
            "[a-gA-G]"  # pitch A to G
            "(bb|b|s|ss)?"  # optional accidentals: double flats, flat, sharp, double sharps
            "("  # begin octave
            "[1-7]?"  # absolute: noteblock's octaves range from 1 to 7
            "|"  # or
            "(_*|\\^*)"  # relative to instrument's range: _ to lower, ^ to raise
            ")"  # end octave
            ")"  # end note name
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")*"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            "){2,}"  # repeat at least 2x
            "$"
        )
    ),
]
T_CompoundNote = Annotated[
    str,  # format: T_MultipleNotes, but no rests allowed, and enclosed in parentheses
    Field(
        pattern=(
            "^"
            "\\("  # opening parenthesis
            "("  # begin repeat
            "[a-gA-G]"  # pitch A to G
            "(bb|b|s|ss)?"  # optional accidentals: double flats, flat, sharp, double sharps
            "("  # begin octave
            "[1-7]?"  # absolute: noteblock's octaves range from 1 to 7
            "|"  # or
            "(_*|\\^*)"  # relative to instrument's range: _ to lower, ^ to raise
            ")"  # end octave
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")*"  # end duration
            "(\\s*,\\s*|\\))"  # "," or closing parenthesis
            "){2,}"  # repeat at least 2x
            "$"
        )
    ),
]
T_TrillStyle = Literal["normal", "alt"]
T_StaticAbsoluteLevel = NonNegativeInt  # higher is closer to the player
T_VariableAbsoluteLevel = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "\\d+"  # level: higher is closer to the player
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")+"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_AbsoluteLevel = T_StaticAbsoluteLevel | T_VariableAbsoluteLevel
T_StaticRelativeLevel = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to raise, - to lower
            "\\d+"  # level: higher is closer to the player
            "$"
        )
    ),
]
T_VariableRelativeLevel = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "[+-]?"  # optional: + to raise, - to lower
            "\\d+"  # level: higher is closer to the player
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")+"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_RelativeLevel = T_StaticRelativeLevel | T_VariableRelativeLevel
T_StaticLevel = T_StaticAbsoluteLevel | T_StaticRelativeLevel
T_VariableLevel = T_VariableAbsoluteLevel | T_VariableRelativeLevel
T_Level = T_StaticLevel | T_VariableLevel
assert T_Level == T_AbsoluteLevel | T_RelativeLevel
T_AbsoluteDivision = Literal[  # which side relative to the player
    "M",  # middle (default)
    "L",  # left
    "R",  # right
    "LR",  # both sides
]
T_RelativeDivision = Literal["SW"]  # switch
T_Division = T_AbsoluteDivision | T_RelativeDivision
T_StaticAbsoluteCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "(M|L|R|LR)"  # which side relative to the player
            "\\s*"
            "\\d+"  # level: higher is closer to the player
            "$"
        )
    ),
]
T_StaticRelativeCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "(M|L|R|LR|SW)"  # which side relative to the player
            "\\s*"
            "[+-]?"  # optional: + to raise, - to lower
            "\\d+"  # level: higher is closer to the player
            "$"
        )
    ),
]
T_StaticCompoundPosition = T_StaticAbsoluteCompoundPosition | T_StaticRelativeCompoundPosition
T_VariableAbsoluteCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "(M|L|R|LR)"  # which side relative to the player
            "\\s*"
            "("  # begin repeat
            "\\d+"  # level: higher is closer to the player
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")+"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_VariableRelativeCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "(M|L|R|LR|SW)"  # 1 which side relative to the player
            "\\s*"
            "("  # begin repeat
            "[+-]?"  # optional: + to raise, - to lower
            "\\d+"  # level: higher is closer to the player
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of ticks or of beats
            ")+"  # end duration
            "(\\s*,\\s*|$)"  # "," or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_VariableCompoundPosition = T_VariableAbsoluteCompoundPosition | T_VariableRelativeCompoundPosition
T_AbsoluteCompoundPosition = T_StaticAbsoluteCompoundPosition | T_VariableAbsoluteCompoundPosition
T_RelativeCompoundPosition = T_StaticRelativeCompoundPosition | T_VariableRelativeCompoundPosition
T_CompoundPosition = T_AbsoluteCompoundPosition | T_RelativeCompoundPosition
assert T_CompoundPosition == T_StaticCompoundPosition | T_VariableCompoundPosition
T_StaticAbsolutePosition = T_StaticAbsoluteLevel | T_AbsoluteDivision | T_StaticAbsoluteCompoundPosition
T_StaticPosition = T_StaticLevel | T_Division | T_StaticCompoundPosition
T_VariablePosition = T_VariableLevel | T_VariableCompoundPosition
T_AbsolutePosition = T_AbsoluteLevel | T_AbsoluteDivision | T_AbsoluteCompoundPosition
T_RelativePosition = T_RelativeLevel | T_RelativeDivision | T_RelativeCompoundPosition
T_Position = T_StaticPosition | T_VariablePosition
assert T_Position == T_AbsolutePosition | T_RelativePosition


def to_dict(data: Any, *, key: str) -> dict[str, Any]:
    if isinstance(data, dict):
        if key in data:
            return data
        with suppress(KeyError):
            data[key] = data.pop(REF_KEY)
            return data
    return {key: data}


class T_Environment(BaseModel):
    class Config:
        frozen = True
        extra = "forbid"
        alias_generator = to_camel

    time: T_StaticProperty[T_Time] = None
    tempo: T_StaticProperty[T_Tempo] = None
    beat: T_StaticProperty[T_Beat] = None
    trill_style: T_StaticProperty[T_TrillStyle] = None
    position: T_PositionalProperty[T_Position] = None
    instrument: T_PositionalProperty[T_Instrument] = None
    dynamic: T_PositionalProperty[T_Dynamic] = None
    transpose: T_PositionalProperty[T_Transpose] = None
    sustain: T_PositionalProperty[T_Sustain] = None


class T_NotesModifier(T_Environment): ...


class _BaseNote(T_Environment):
    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        if isinstance(data, dict) and "notes" in data:
            data["note"] = data.pop("notes")
        return to_dict(data, key="note")


class T_RegularNote(_BaseNote):
    note: T_BarDelimiter | T_Rest | T_NoteName | T_MultipleNotes | T_CompoundNote


class T_TrilledNote(_BaseNote):
    note: T_NoteName
    trill: T_NoteName


T_SingleNote = T_RegularNote | T_TrilledNote


class T_ParallelNotes(_BaseNote):
    note: T_Tuple[T_SingleNote | T_SequentialNotes]

    def __iter__(self):
        yield from self.note


class T_SequentialNotes(_BaseNote):
    note: T_Tuple[T_SingleNote | T_ParallelNotes | T_NotesModifier]

    def __iter__(self):
        yield from self.note


T_Note = T_SingleNote | T_ParallelNotes | T_SequentialNotes
T_NoteMeta = T_NotesModifier | T_Note


class T_NamedEnvironment(T_Environment):
    path: Path | None = Field(alias=PATH_KEY, default=None, exclude=True)
    name: T_Name | None = None


class T_Voice(T_NamedEnvironment, T_SequentialNotes):
    notes: T_Tuple[T_SingleNote | T_ParallelNotes | T_NotesModifier]

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        data = to_dict(data, key="note")
        notes = data["note"]
        with suppress(KeyError, TypeError):
            data["note"] = notes.pop(REF_KEY)
            if PATH_KEY not in data:
                data[PATH_KEY] = notes.pop(PATH_KEY)
        return data


class T_Section(T_NamedEnvironment):
    voices: T_Tuple[T_Positional[T_Voice] | None]

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        data = to_dict(data, key="voices")
        with suppress(ValidationError):
            data["voices"] = [T_Voice.model_validate(data["voices"])]
        return data

    def __iter__(self):
        yield from self.voices


T_Movement = T_Positional[T_Section]


class T_Composition(T_NamedEnvironment):
    movements: T_Tuple[T_Movement | T_Composition]

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        data = to_dict(data, key="movements")
        with suppress(ValidationError):
            data["movements"] = [TypeAdapter(T_Movement).validate_python(data["movements"])]
        return data

    def __iter__(self):
        yield from self.movements
