import type { ExtractDoc, WithDoc } from "./doc.ts";

export type DistributiveOmit<T extends object, K extends string> = T extends T
	? Omit<T, K>
	: never;

export type Cover<T extends object, Keys extends string> = T extends T
	? T & { [K in Exclude<Keys, keyof T>]?: undefined }
	: never;

export type Modified<
	Target extends Record<string, unknown>,
	Modifier extends object,
> =
	| Target[keyof Target]
	| WithDoc<
			{ [K in string & keyof Target]: Target[K] } & Modifier,
			ExtractDoc<Target[keyof Target]>
	  >;
