import type { Slice } from "#core/assembler/@";
import { Block } from "../block.js";
import { Builder } from "./builder.js";

export class SingleBuilder extends Builder<"single"> {
	protected buildPlayButton() {
		const cursor = this.cursor
			.at({ y: this.size.height - 2 })
			.offset({ dz: -2 });

		if (this.hasPrevious) {
			this.withCursor(cursor, (self) => self.buildRecurringPlayButton());
		} else {
			this.withCursor(cursor, (self) => self.buildInitialPlayButton());
		}
	}

	private buildInitialPlayButton() {
		const midpoint = Math.ceil(this.size.width / 2);
		this.setOffset([0, 0, midpoint], Block.Button);
		this.useWireOffset((wire) => {
			let steps = 0;
			for (let dz = midpoint - 1; dz >= 2; dz--) {
				steps = (steps + 1) % 15;
				wire.add([0, 0, dz], steps === 0 ? "repeater" : "wire");
			}
			wire.add([0, -1, 1]);
			wire.add([0, -2, 2], null);
		});
	}

	private buildRecurringPlayButton() {
		this.setOffset([0, 0, 0], Block.Button);
		this.useWireOffset((wire) => {
			wire.add([0, 0, 0], null);
			wire.add([0, -1, 1]);
			wire.add([0, -2, 2], null);
		});
	}

	protected buildSlice(slice: Slice<"single">) {
		this.buildSingleSlice(slice);
	}
}
