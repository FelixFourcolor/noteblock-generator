import { type Type, type } from "arktype";

type TypeOf<T extends Type<unknown>> = T extends Type<infer U> ? U : never;

export type Modified<
	Target extends Record<string, Type>,
	Modifier extends Type,
> =
	| TypeOf<Target[keyof Target]>
	| ({ [K in string & keyof Target]: TypeOf<Target[K]> } & TypeOf<Modifier>);

export function Modified<
	const Target extends Record<string, Type>,
	const Modifier extends Type,
>(target: Target, modifier: Modifier) {
	const unmodified = type.or(...Object.values(target));
	const modified = type.and(target as any, modifier as any);
	return type.or(unmodified, modified) as unknown as Type<
		Modified<Target, Modifier>
	>;
}
