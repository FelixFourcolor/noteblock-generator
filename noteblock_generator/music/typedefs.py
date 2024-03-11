from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Annotated, Any, Iterable, Literal, TypeVar

from pydantic import BaseModel, Field, GetCoreSchemaHandler, NonNegativeInt, PositiveFloat, PositiveInt, model_validator
from pydantic.alias_generators import to_camel
from pydantic_core import core_schema


class T_MultiValue(tuple["T", ...]):
    @classmethod
    def __get_pydantic_core_schema__(cls, src_type: Any, handler: GetCoreSchemaHandler):
        return core_schema.no_info_after_validator_function(cls, handler(tuple))

    def __add__(self, other: Iterable[T]):
        return T_MultiValue(super().__add__(tuple(other)))


T = TypeVar("T")
T_Reset = Literal["$reset"]
T_StaticProperty = T | T_Reset | None
T_Positional = T | Annotated[T_MultiValue[T], Field(min_length=1)]
T_Delete = Literal["$del"]
T_PositionalProperty = T_Positional[T_StaticProperty[T] | T_Delete]
T_Array = tuple[T, ...]
T_LevelIndex = int
T_DivisionIndex = Literal[0, 1]
T_DoubleIndex = tuple[T_DivisionIndex, T_LevelIndex]
T_Index = T_LevelIndex | T_DoubleIndex
T_Duration = int
T_NoteValue = int
T_Name = str
T_Time = PositiveInt
T_Width = Annotated[int, Field(ge=8, le=16)]
T_Delay = Annotated[int, Field(ge=1, le=4)]
T_Beat = PositiveInt
T_Tick = PositiveFloat
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
T_StaticAbsoluteDynamic = Annotated[int, Field(ge=0, le=4)]
T_VariableAbsoluteDynamic = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "[0-4]"  # dynamic value: 0 to 4
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
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
            "[0-4]"  # a value from 0 to 4
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
            "[+-]?"  # optionally relative: + to raise, - to lower
            "[0-4]"  # a value from 0 to 4
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
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
T_AbsoluteTranspose = int
T_RelativeTranspose = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to raise, - to lower
            "\\d+"  # a value
            "$"
        )
    ),
]
T_Transpose = T_AbsoluteTranspose | T_RelativeTranspose
T_AbsoluteSustain = (
    bool
    | int
    | Annotated[
        str,
        Field(pattern=("^(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)$")),  # number of pulses or of beats
    ]
)
T_RelativeSustain = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to increase, - to decrease
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
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
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
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
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
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
            "[rR]"  # R for rest
            "|"  # or
            "[a-gA-G]"  # pitch A to G
            "(bb|b|s|ss)?"  # optional accidentals: double flats, flat, sharp, double sharps
            "("  # begin octave
            "[1-7]?"  # absolute: noteblock's octaves range from 1 to 7
            "|"  # or
            "(_*|\\^*)"  # relative to instrument's range: _ to lower, ^ to raise
            ")"  # end octave
            "("  # begin duration
            "(\\s+[+-]?|\\s*[+-])"  # multiple values separated by spaces or signs
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
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
            "(([1-9]\\d*b?)?\\.|[1-9]\\d*b?\\.?)"  # number of pulses or of beats
            ")*"  # end duration
            "(\\s*,\\s*|\\))"  # "," or closing parenthesis
            "){2,}"  # repeat at least 2x
            "$"
        )
    ),
]
T_TrillStyle = Literal["normal", "alt"]
T_AbsoluteLevel = NonNegativeInt
T_RelativeLevel = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "[+-]"  # + to raise, - to lower
            "\\d+"  # value
            "$"
        )
    ),
]
T_Level = T_AbsoluteLevel | T_RelativeLevel
T_AbsoluteDivision = Literal["left", "right", "bothsides"]
T_RelativeDivision = Literal["switch"]
T_Division = T_AbsoluteDivision | T_RelativeDivision
T_AbsoluteCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "(left|right|bothsides)"  # which side relative to the player
            "\\s*"
            "\\d+"  # level: higher is closer to the player
            "$"
        )
    ),
]
T_RelativeCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "(left|right|bothsides|switch)"  # which side relative to the player
            "\\s*"
            "[+-]?"  # optionally relative level: + to raise, - to lower
            "\\d+"  # value
            "$"
        )
    ),
]
T_CompoundPosition = T_AbsoluteCompoundPosition | T_RelativeCompoundPosition
T_SingleDivisionPosition = T_Level
T_DoubleDivisionPosition = T_Level | T_Division | T_CompoundPosition
T_Position = T_SingleDivisionPosition | T_DoubleDivisionPosition


def _to_dict(data: Any, *, key: str) -> dict:
    if isinstance(data, dict):
        if key in data:
            return data
        with contextlib.suppress(KeyError):
            return {key: data.pop("data")}
    return {key: data}


class _BaseModel(BaseModel):
    class Config:
        frozen = True
        extra = "forbid"
        alias_generator = to_camel


class _BaseNoteModel(_BaseModel):
    time: T_StaticProperty[T_Time] = None
    delay: T_StaticProperty[T_Delay] = None
    beat: T_StaticProperty[T_Beat] = None
    trill_style: T_StaticProperty[T_TrillStyle] = None
    instrument: T_PositionalProperty[T_Instrument] = None
    dynamic: T_PositionalProperty[T_Dynamic] = None
    transpose: T_PositionalProperty[T_Transpose] = None
    sustain: T_PositionalProperty[T_Sustain] = None


class T_SingleDivisionNotesModifier(_BaseNoteModel):
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionNotesModifier(_BaseNoteModel):
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class _BaseNote(_BaseNoteModel):
    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        return _to_dict(data, key="note")


class _BaseRegularNote(_BaseNote):
    note: T_BarDelimiter | T_Rest | T_NoteName | T_MultipleNotes | T_CompoundNote


class T_SingleDivisionRegularNote(_BaseRegularNote):
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionRegularNote(_BaseRegularNote):
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class _BaseTrilledNote(_BaseNote):
    note: T_NoteName
    trill: T_NoteName


class T_SingleDivisionTrilledNote(_BaseTrilledNote):
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionTrilledNote(_BaseTrilledNote):
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class T_SingleDivisionParallelNotes(_BaseNote):
    note: T_Array[T_SingleDivisionRegularNote | T_SingleDivisionTrilledNote | T_SingleDivisionSequentialNotes]
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionParallelNotes(_BaseNote):
    note: T_Array[T_DoubleDivisionRegularNote | T_DoubleDivisionTrilledNote | T_DoubleDivisionSequentialNotes]
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class T_SingleDivisionSequentialNotes(_BaseNote):
    note: T_Array[
        T_SingleDivisionRegularNote
        | T_SingleDivisionTrilledNote
        | T_SingleDivisionParallelNotes
        | T_SingleDivisionNotesModifier
    ]
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionSequentialNotes(_BaseNote):
    note: T_Array[
        T_DoubleDivisionRegularNote
        | T_DoubleDivisionTrilledNote
        | T_DoubleDivisionParallelNotes
        | T_DoubleDivisionNotesModifier
    ]
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class _BaseVoice(_BaseModel):
    path: Path | None = Field(default=None, exclude=True)
    name: T_Name | None = None
    time: T_StaticProperty[T_Time] = None
    beat: T_StaticProperty[T_Beat] = None
    trill_style: T_StaticProperty[T_TrillStyle] = None
    instrument: T_PositionalProperty[T_Instrument] = None
    dynamic: T_PositionalProperty[T_Dynamic] = None
    transpose: T_PositionalProperty[T_Transpose] = None
    sustain: T_PositionalProperty[T_Sustain] = None

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        data = _to_dict(data, key="notes")
        if "path" not in data:
            notes = data["notes"]  # guarantee valid key by _to_dict
            with contextlib.suppress(TypeError, KeyError):
                # try setting voice's path to notes' path, if it exists
                data["path"] = notes.pop("path")
        return data


class T_SingleDivisionVoice(_BaseVoice):
    notes: T_SingleDivisionSequentialNotes
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionVoice(_BaseVoice):
    notes: T_DoubleDivisionSequentialNotes
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class _BaseSection(_BaseModel):
    path: Path | None = Field(default=None, exclude=True)
    name: T_Name | None = None
    width: T_Width | None = None
    time: T_StaticProperty[T_Time] = None
    delay: T_StaticProperty[T_Delay] = None
    beat: T_StaticProperty[T_Beat] = None
    tick: T_StaticProperty[T_Tick] = None
    trill_style: T_StaticProperty[T_TrillStyle] = None
    instrument: T_StaticProperty[T_Instrument] = None
    dynamic: T_StaticProperty[T_Dynamic] = None
    transpose: T_StaticProperty[T_Transpose] = None
    sustain: T_StaticProperty[T_Sustain] = None

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        return _to_dict(data, key="voices")


class T_SingleDivisionSection(_BaseSection):
    voices: T_Array[T_Positional[T_SingleDivisionVoice] | None]
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionSection(_BaseSection):
    voices: T_Array[T_Positional[T_DoubleDivisionVoice] | None]
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class _BaseCompoundSection(_BaseSection):
    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        return _to_dict(data, key="sections")


class T_SingleDivisionCompoundSection(_BaseCompoundSection):
    sections: T_Array[T_SingleDivisionSection | T_SingleDivisionCompoundSection]
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


class T_DoubleDivisionCompoundSection(_BaseCompoundSection):
    sections: T_Array[T_DoubleDivisionSection | T_DoubleDivisionCompoundSection]
    position: T_PositionalProperty[T_DoubleDivisionPosition] = None


class T_MixedCompoundSection(_BaseCompoundSection):
    sections: T_Array[T_Section]
    position: T_PositionalProperty[T_SingleDivisionPosition] = None


T_NotesModifier = T_SingleDivisionNotesModifier | T_DoubleDivisionNotesModifier
T_RegularNote = T_SingleDivisionRegularNote | T_DoubleDivisionRegularNote
T_TrilledNote = T_SingleDivisionTrilledNote | T_DoubleDivisionTrilledNote
T_SingleNote = T_RegularNote | T_TrilledNote
T_ParallelNotes = T_SingleDivisionParallelNotes | T_DoubleDivisionParallelNotes
T_SequentialNotes = T_SingleDivisionSequentialNotes | T_DoubleDivisionSequentialNotes
T_Note = T_SingleNote | T_ParallelNotes | T_SequentialNotes
T_NoteMeta = T_NotesModifier | T_Note
T_Voice = T_SingleDivisionVoice | T_DoubleDivisionVoice
T_SingleSection = T_SingleDivisionSection | T_DoubleDivisionSection
T_CompoundSection = T_SingleDivisionCompoundSection | T_DoubleDivisionCompoundSection | T_MixedCompoundSection
T_Section = T_SingleSection | T_CompoundSection
