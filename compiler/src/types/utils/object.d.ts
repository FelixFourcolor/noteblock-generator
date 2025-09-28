export type OneOf<T, K extends keyof T = keyof T> = K extends K
	? Override<{ [KT in keyof T]?: undefined }, Pick<T, K>>
	: never;

export type AtLeastOneOf<Object extends object> = Object extends unknown
	? {
			[K in keyof Object]-?: Required<Pick<Object, K>> &
				Partial<Pick<Object, Exclude<keyof Object, K>>>;
		}[keyof Object]
	: never;

export type AtMostOneOf<Object extends object> = Partial<OneOf<Object>>;

export type Override<A extends object, B extends object> = A extends A
	? Omit<A, keyof B> & B
	: never;

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
	| ({ [K in string & keyof Target]: Target[K] } & Modifier);
