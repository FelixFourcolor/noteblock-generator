import type { Lt, Subtract } from "ts-arithmetic";
import type { tags } from "typia";
import type { Tuplify } from "./array.js";

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
		strict?: boolean;
	},
	__separator extends string = options["separator"],
	__atLeast extends number = options["atLeast"] extends number
		? options["atLeast"]
		: 1,
	__wrappers extends [string, string] = options["wrapper"] extends [
		string,
		string,
	]
		? options["wrapper"]
		: options["wrapper"] extends string
			? [options["wrapper"], options["wrapper"]]
			: ["", ""],
	__open_wrapper extends string = __wrappers[0],
	__close_wrapper extends string = __wrappers[1],
	__strict extends boolean = options["strict"] extends boolean
		? options["strict"]
		: false,
> = Re<
	__open_wrapper,
	Pattern,
	Re<Re<Token<__separator>, Pattern>, `{${Subtract<__atLeast, 1>},}`>,
	Re<
		// dangling separator at the end
		Token<__separator>,
		// required if strict and atLeast <= 2 to distinguish repeated vs single pattern
		[__strict, Lt<__atLeast, 2>] extends [true, true] ? "" : "?"
	>,
	__close_wrapper
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
		schema: { pattern: `^\\s*(${Pattern})\\s*$` };
	}>;

type ReType = {
	"typia.tag"?: { value: string };
};

type PatternOf<T extends ReType> = Exclude<T["typia.tag"], undefined>["value"];
