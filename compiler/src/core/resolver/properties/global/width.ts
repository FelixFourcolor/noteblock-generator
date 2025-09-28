import type { Time } from "#core/resolver/properties/@";
import type { Width as T_Width } from "#types/schema/@";
import type { ResolveType } from "../properties.js";

export class Width {
	private readonly value: number | undefined;

	static Default() {
		return 16;
	}

	constructor(width?: T_Width | undefined) {
		this.value = width;
	}

	fork({ time }: { time: ResolveType<typeof Time> }) {
		return time && !this.value ? new Width(time) : this;
	}

	resolve() {
		if (this.value) {
			if (8 <= this.value && this.value <= 16) {
				return this.value;
			}
			for (let candidate = 16; candidate >= 8; candidate--) {
				if (this.value % candidate === 0) {
					return candidate;
				}
			}
		}
		return Width.Default();
	}
}
