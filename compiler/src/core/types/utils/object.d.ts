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

export type DistributeOmit<T extends object, K extends keyof T> = T extends T
	? Omit<T, K>
	: never;

export type Cover<T extends object, Keys extends string> = T extends T
	? T & { [K in Keys]: K extends keyof T ? T[K] : undefined }
	: never;

export type Pretty<T extends object> = T extends T
	? { [K in keyof T]: T[K] }
	: never;
