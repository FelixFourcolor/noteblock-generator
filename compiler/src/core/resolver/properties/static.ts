import { is } from "typia";
import type { Reset, Static as T_Static } from "#types/schema/@";

type ProtoStatic<T> = {
	readonly Default: T;
};

export interface Static<T> {
	fork(modifier: T_Static<T> | undefined): this;
	transform(modifier: T_Static<T> | undefined): this;
	resolve(): T;
}
export interface StaticClass<T> {
	new (): Static<T>;
	readonly default: T;
}

export function Static<T>({ Default }: ProtoStatic<T>): StaticClass<T> {
	return class {
		static readonly default = Default;

		private current: T;
		private readonly original: T;

		constructor(value: T = Default) {
			this.current = this.original = value;
		}

		private getTransformedCurrent(modifier: T_Static<T> | undefined) {
			if (modifier === undefined) {
				return this.current;
			}
			return is<Reset>(modifier) ? this.original : modifier;
		}

		fork(modifier: T_Static<T> | undefined) {
			const ctor = this.constructor as new (value: T) => this;
			return new ctor(this.getTransformedCurrent(modifier));
		}

		transform(modifier: T_Static<T> | undefined) {
			this.current = this.getTransformedCurrent(modifier);
			return this;
		}

		resolve(): T {
			return this.current;
		}
	};
}
