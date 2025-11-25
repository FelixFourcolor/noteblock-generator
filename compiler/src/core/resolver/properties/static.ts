import { is } from "typia";
import type { Reset, Static as T_Static } from "#schema/@";

type ProtoStatic<T> = {
	readonly Default: T;
};

interface Static<T> {
	fork(modifier: T_Static<T> | undefined): this;
	transform(modifier: T_Static<T> | undefined): this;
	resolve(): T;
}

export interface StaticClass<T> {
	new (): Static<T>;
	Default(): T;
}

export function Static<T>({ Default }: ProtoStatic<T>): StaticClass<T> {
	return class StaticImpl {
		static Default() {
			return Default;
		}

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
			return new StaticImpl(this.getTransformedCurrent(modifier));
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
