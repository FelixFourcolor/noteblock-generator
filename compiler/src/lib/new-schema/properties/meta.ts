import { type Type, type } from "arktype";
import { mapValues } from "lodash";

export const Reset = "$reset";
export const Delete = "$delete";
export const Noop = null;

export const { Static, Positional } = type.module({
	"Static<T>": `T | "${Reset}"`,
	"Positional<T>": `Static<T> | (Static<T> | "${Delete}" | ${Noop})[] >= 1`,
});

type Schema = Record<string, Type>;
type IStaticSchema<S extends Schema> = Type<{
	[K in keyof S]: Static<S[K]["t"]>;
}>;
type IPositionalSchema<S extends Schema> = Type<{
	[K in keyof S]: Positional<S[K]["t"]>;
}>;

export function IStatic<S extends Schema>(schema: S): IStaticSchema<S> {
	const mappedSchema = mapValues(schema, (v) =>
		Static(v as Type),
	) as unknown as Schema;
	return type(mappedSchema) as unknown as IStaticSchema<S>;
}

export function IPositional<S extends Schema>(schema: S): IPositionalSchema<S> {
	const mappedSchema = mapValues(schema, (v) =>
		Positional(v as Type),
	) as unknown as Schema;
	return type(mappedSchema) as unknown as IPositionalSchema<S>;
}

export type Reset = typeof Reset;
export type Delete = typeof Delete;
export type Noop = typeof Noop;
export type Static<T> = T | Reset;
export type Positional<T> = Static<T> | (Static<T> | Delete | Noop)[];
export type IStatic<T> = { [K in keyof T]?: Static<T[K]> };
export type IPositional<T> = { [K in keyof T]?: Positional<T[K]> };
