import type { Name as T_Name } from "#types/schema/@";

export class Name {
	private readonly value: string | undefined;

	constructor(name?: T_Name | undefined) {
		this.value = name;
	}

	fork(name: string | undefined) {
		if (!name) {
			return this;
		}
		return new Name(this.value ? `${this.value} / ${name}` : name);
	}

	resolve() {
		return this.value ?? "Unnamed";
	}
}
