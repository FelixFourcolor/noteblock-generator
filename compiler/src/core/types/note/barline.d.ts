import type { Re, Token } from "#core/types/utils/@";

export type Barline = Re<BarNumber, "?", Line, UnsafeFlag, "?">;

type BarNumber = Token<"\\d+">;
type Line = Re<"\\|{1,2}">; // a bar line, optionally 2 lines to rest the entire bar
type UnsafeFlag = Re<"\\!">; // ignore any barline errors
