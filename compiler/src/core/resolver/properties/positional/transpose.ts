import { match, P } from "ts-pattern";
import type { IPositional, Transpose as T_Transpose } from "#schema/@";
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

	constructor(args = { value: new Value(), auto: new Auto() }) {
		this.value = args.value;
		this.auto = args.auto;
	}

	fork(modifier: IPositional<T_Transpose> | undefined) {
		return new Transpose({
			value: this.value.fork(modifier?.value),
			auto: this.auto.fork(modifier?.auto),
		});
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
