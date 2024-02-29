from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar, Union

from pydantic import BaseModel, Field, GetCoreSchemaHandler, PositiveFloat, PositiveInt, model_validator
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import core_schema

T = TypeVar("T")


class T_MultiValue(list[T]):
    @classmethod
    def __get_pydantic_core_schema__(cls, src_type: Any, handler: GetCoreSchemaHandler):
        return core_schema.no_info_after_validator_function(cls, handler(list))


class _BaseModel(BaseModel):
    class Config:
        frozen = True
        extra = "forbid"


class T_Default(_BaseModel):
    pass


T_Optional = Union[T, T_Default]
T_Positional = T | Annotated[T_MultiValue[T], Field(min_length=1)]
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
T_AbsoluteDynamic = Annotated[int, Field(ge=0, le=4)]
T_TimedAbsoluteDynamic = Annotated[
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
            "(\\s*,\\s*|$)"  # ","  or end of string
            ")+"  # end repeat
            "$"
        )
    ),
]
T_RelativeDynamic = Annotated[
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
T_TimedRelativeDynamic = Annotated[
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
T_ConstantDynamic = T_AbsoluteDynamic | T_RelativeDynamic
T_TimedDynamic = T_TimedAbsoluteDynamic | T_TimedRelativeDynamic
T_GlobalDynamic = T_AbsoluteDynamic | T_TimedAbsoluteDynamic
T_LocalDynamic = T_ConstantDynamic | T_TimedDynamic
T_GlobalTranspose = T_AbsoluteTranspose = int
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
T_LocalTranspose = T_GlobalTranspose | T_RelativeTranspose
T_AbsoluteSustain = int
T_GlobalSustain = (
    bool
    | T_AbsoluteSustain
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
T_LocalSustain = T_GlobalSustain | T_RelativeSustain
T_BarDelimiter = Annotated[
    str,
    Field(
        pattern=(
            "^"
            "\\|{1,2}"  # | to assert bar line, or || to also rest for the entire bar
            "(\\s*\\d+)?"  # optionally assert bar number
            "\\!?"  # optionally disable compile-time check
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
            "(bb|b|s|ss)?"  # accidentals: flat, sharp, double flats, double sharps
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
T_CompoundNote = Annotated[
    str,  # format: <note> <duration>, <note> <duration>, etc.
    Field(
        pattern=(
            "^"
            "("  # begin repeat
            "[a-gA-G]"  # pitch A to G
            "(bb|b|s|ss)?"  # accidentals: flat, sharp, double flats, double sharps
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
T_TrillMode = Literal["main", "alt"]
T_AbsoluteLevel = PositiveInt
T_AbsoluteDivision = Literal["left", "right", "bothsides"]
T_AbsoluteCompoundPosition = Annotated[
    str,
    Field(
        pattern=(
            "^"  #
            "(left|right|bothsides)"  # which side relative to the player
            "\\s*"
            "\\d+"  # level: higher is closer to the player
            "$"
        )
    ),
]
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
T_RelativeDivision = Literal["switch"]
T_Division = T_AbsoluteDivision | T_RelativeDivision
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
T_SingleDivisionPosition = T_Level = T_AbsoluteLevel | T_RelativeLevel
T_DoubleDivisionPosition = T_Level | T_Division | T_CompoundPosition
T_Position = T_SingleDivisionPosition | T_DoubleDivisionPosition
T_Voice = Union["T_SingleDivisionVoice", "T_DoubleDivisionVoice"]

_DEFAULT = T_Default()


class T_NoteModel(_BaseModel):
    time: T_Optional[T_Time] | None = _DEFAULT
    delay: T_Optional[T_Delay] | None = _DEFAULT
    beat: T_Optional[T_Beat] | None = _DEFAULT
    trillStartsOn: T_Optional[T_TrillMode] | None = _DEFAULT
    position: T_Positional[T_Optional[T_Position]] | None = _DEFAULT
    instrument: T_Positional[T_Optional[T_Instrument]] | None = _DEFAULT
    dynamic: T_Positional[T_Optional[T_LocalDynamic]] | None = _DEFAULT
    transpose: T_Positional[T_Optional[T_LocalTranspose]] | None = _DEFAULT
    sustain: T_Positional[T_Optional[T_LocalSustain]] | None = _DEFAULT


class T_NotesModifier(T_NoteModel):
    pass


def _accept_data(data: Any, key: str):
    if isinstance(data, dict):
        if key in data:
            return data
        if "data" in data:
            return {key: data.pop("data")}
    return {key: data}


class _BaseNote(T_NoteModel):
    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        return _accept_data(data, key="note")


class T_SingleNote(_BaseNote):
    note: T_BarDelimiter | T_Rest | T_NoteName | T_CompoundNote


class T_TrilledNote(T_SingleNote):
    note: T_NoteName
    trill: T_NoteName


class _SingleDivisionNoteModel(T_NoteModel):
    position: T_Positional[T_Optional[T_SingleDivisionPosition]] | None = _DEFAULT


class _DoubleDivisionNoteModel(T_NoteModel):
    position: T_Positional[T_Optional[T_DoubleDivisionPosition]] | None = _DEFAULT


class T_SingleDivisionNotesModifier(T_NotesModifier, _SingleDivisionNoteModel):
    pass


class T_DoubleDivisionNotesModifier(T_NotesModifier, _DoubleDivisionNoteModel):
    pass


class T_SingleDivisionSingleNote(T_SingleNote, _SingleDivisionNoteModel):
    pass


class T_DoubleDivisionSingleNote(T_SingleNote, _DoubleDivisionNoteModel):
    pass


class T_SingleDivisionTrilledNote(T_TrilledNote, _SingleDivisionNoteModel):
    pass


class T_DoubleDivisionTrilledNote(T_TrilledNote, _DoubleDivisionNoteModel):
    pass


class T_SingleDivisionParallelNotes(_BaseNote, _SingleDivisionNoteModel):
    note: list[T_SingleDivisionSingleNote | T_SingleDivisionSequentialNotes]


class T_DoubleDivisionParallelNotes(_BaseNote, _DoubleDivisionNoteModel):
    note: list[T_DoubleDivisionSingleNote | T_DoubleDivisionSequentialNotes]


T_ParallelNotes = T_SingleDivisionParallelNotes | T_DoubleDivisionParallelNotes


class T_SingleDivisionSequentialNotes(_BaseNote, _SingleDivisionNoteModel):
    note: list[T_SingleDivisionSingleNote | T_SingleDivisionParallelNotes | T_SingleDivisionNotesModifier]


class T_DoubleDivisionSequentialNotes(_BaseNote, _DoubleDivisionNoteModel):
    note: list[T_DoubleDivisionSingleNote | T_DoubleDivisionParallelNotes | T_DoubleDivisionNotesModifier]


T_SequentialNotes = T_SingleDivisionSequentialNotes | T_DoubleDivisionSequentialNotes


class _BaseVoice(_BaseModel):
    path: SkipJsonSchema[T_Optional[Path]] = Field(default=_DEFAULT, exclude=True)
    name: T_Optional[T_Name] = _DEFAULT
    time: T_Optional[T_Time] = _DEFAULT
    beat: T_Optional[T_Beat] = _DEFAULT
    trillStartsOn: T_Optional[T_TrillMode] = _DEFAULT
    instrument: T_Positional[T_Optional[T_Instrument]] = _DEFAULT
    dynamic: T_Positional[T_Optional[T_LocalDynamic]] = _DEFAULT
    transpose: T_Positional[T_Optional[T_LocalTranspose]] = _DEFAULT
    sustain: T_Positional[T_Optional[T_LocalSustain]] = _DEFAULT

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        data = _accept_data(data, key="notes")
        if "path" not in data and "path" in data["notes"]:
            data["path"] = data["notes"].pop("path")
        return data


class T_SingleDivisionVoice(_BaseVoice):
    notes: T_SingleDivisionSequentialNotes
    position: T_Positional[T_Optional[T_SingleDivisionPosition]] = _DEFAULT


class T_DoubleDivisionVoice(_BaseVoice):
    notes: T_DoubleDivisionSequentialNotes
    position: T_Positional[T_Optional[T_DoubleDivisionPosition]] = _DEFAULT


class _BaseSection(_BaseModel):
    path: SkipJsonSchema[T_Optional[Path]] = Field(default=_DEFAULT, exclude=True)
    name: T_Optional[T_Name] = _DEFAULT
    time: T_Optional[T_Time] = _DEFAULT
    width: T_Optional[T_Width] = _DEFAULT
    delay: T_Optional[T_Delay] = _DEFAULT
    beat: T_Optional[T_Beat] = _DEFAULT
    tick: T_Optional[T_Tick] = _DEFAULT
    trillStartsOn: T_Optional[T_TrillMode] = _DEFAULT
    instrument: T_Optional[T_Instrument] = _DEFAULT
    dynamic: T_Optional[T_GlobalDynamic] = _DEFAULT
    transpose: T_Optional[T_GlobalTranspose] = _DEFAULT
    sustain: T_Optional[T_GlobalSustain] = _DEFAULT

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        return _accept_data(data, key="voices")


class T_SingleDivisionSection(_BaseSection):
    voices: list[T_Optional[T_SingleDivisionVoice]]


class T_DoubleDivisionSection(_BaseSection):
    voices: list[T_Optional[T_DoubleDivisionVoice]]


T_SingleSection = T_SingleDivisionSection | T_DoubleDivisionSection


class T_CompoundSection(_BaseSection):
    sections: list[T_Section]

    @model_validator(mode="before")
    @classmethod
    def _(cls, data):
        return _accept_data(data, key="sections")


T_Section = T_SingleSection | T_CompoundSection
