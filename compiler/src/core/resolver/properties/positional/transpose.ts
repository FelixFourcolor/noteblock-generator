import { match, P } from "ts-pattern";
import type { IPositional, Transpose as T_Transpose } from "#types/schema/@";
import { Positional } from "../positional.js";
import { parseNumericValue } from "../variable.js";

const Value = Positional({
	Default: 0,
	transform: (current, modifier: T_Transpose.Value) => {
		return match(modifier)
			.with(P.number, (modifier) => modifier)
			.otherwise((modifier) => {
				const { value } = parseNumericValue(modifier);
				return current + value;
			});
	},
});

const Auto = Positional({ Default: false });

export class Transpose {
	private readonly value: InstanceType<typeof Value>;
	private readonly auto: InstanceType<typeof Auto>;

	constructor(
		value?: InstanceType<typeof Value>,
		auto?: InstanceType<typeof Auto>,
	) {
		this.value = value ?? new Value();
		this.auto = auto ?? new Auto();
	}

	fork(modifier: IPositional<T_Transpose> | undefined) {
		const ctor = this.constructor as new (
			value?: InstanceType<typeof Value>,
			auto?: InstanceType<typeof Auto>,
		) => this;

		return new ctor(
			this.value.fork(modifier?.value),
			this.auto.fork(modifier?.auto),
		);
	}

	transform(modifier: IPositional<T_Transpose> | undefined) {
		this.value.transform(modifier?.value);
		this.auto.transform(modifier?.auto);
		return this;
	}

	resolve() {
		return {
			transpose: this.value.resolve(),
			autoTranspose: this.auto.resolve(),
		};
	}

	static default() {
		return {
			transpose: Value.default(),
			autoTranspose: Auto.default(),
		};
	}
}
