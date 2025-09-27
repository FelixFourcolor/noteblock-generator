import type { Subtract } from "ts-arithmetic";
import type { tags } from "typia";
import type { Tuplify } from "./array.ts";

export type Re<A, B = "", C = "", D = "", E = ""> = [A] extends [string[]]
	? Regex<ReJoin<[...A, string & B, string & C, string & D, string & E]>>
	: Re<[string & A, string & B, string & C, string & D, string & E]>;

export type Token<
	T,
	sep extends string = "\\s*",
	actualSep extends string = sep extends "\\s*" ? sep : `\\s*${sep}\\s*`,
> = Re<[actualSep, Re<T>, actualSep]>;

export type Repeat<
	Pattern extends string,
	options extends {
		separator: string;
		atLeast?: number;
		wrapper?: string | [string, string];
	},
> = Re<
	// open wrapper
	Token<
		options["wrapper"] extends string[]
			? options["wrapper"][0]
			: options["wrapper"] extends string
				? options["wrapper"]
				: ""
	>,
	// head
	Pattern,
	// tail
	Re<Token<options["separator"]>, Pattern>,
	// repeat tail (atLeast - 1) times
	options["atLeast"] extends number
		? `{${Subtract<options["atLeast"], 1>},}`
		: "*",
	// close wrapper
	Token<
		options["wrapper"] extends string[]
			? options["wrapper"][1]
			: options["wrapper"] extends string
				? options["wrapper"]
				: ""
	>
>;

type ReJoin<T extends string[], sep extends string = ""> = T extends [
	infer Head extends string,
	...infer Tail extends string[],
]
	? `${Tuplify<Head> extends [Head]
			? Head extends ReType
				? PatternOf<Head>
				: Head
			: PatternOf<ReUnion<Head>>}${Tail["length"] extends 0
			? ""
			: `${sep}${ReJoin<Tail, sep>}`}`
	: "";

type ReUnion<U extends string> = Or<Tuplify<U>>;

type Or<T> = Regex<Join<T, "|">>;

type Join<T, sep extends string = ""> = T extends [
	infer Head extends string,
	...infer Tail extends string[],
]
	? `${Head extends ReType ? PatternOf<Head> : Head}${Tail extends []
			? ""
			: `${sep}${Join<Tail, sep>}`}`
	: "";

type Regex<Pattern extends string> = string &
	tags.TagBase<{
		target: "string";
		kind: "pattern";
		value: `(${Pattern})`;
		validate: `/^\\s*(${Pattern})\\s*$/i.test($input)`;
		exclusive: ["format", "pattern"];
		schema: {
			pattern: `^(?i)\\s*(${Pattern})\\s*$`;
		};
	}>;

type ReType = {
	"typia.tag"?: { value: string };
};

type PatternOf<T extends ReType> = Exclude<T["typia.tag"], undefined>["value"];
