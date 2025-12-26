import type { Slice } from "@/core/layout";
import { Builder } from "./builder";
import { Block } from "./utils/block";
import { Direction } from "./utils/direction";

export class SingleBuilder extends Builder<"single"> {
	protected override buildSlice(slice: Slice<"single">) {
		this.buildSingleSlice(slice);
	}

	protected buildPlayButton() {
		this.at({ y: this.size.height - 2 }, (self) => {
			if (this.rowCounter === 0) {
				self.at({ z: 0 }, (self) => self.initialPlayButton());
			} else {
				self.offset({ dz: -2 }, (self) => self.recurringPlayButton());
			}
		});
	}

	private initialPlayButton() {
		const midpoint = this.size.width / 2 - 1;

		this.setOffset([0, -1, midpoint], "glass");
		this.setOffset([0, 0, midpoint], Block.Button);

		this.useWireOffset((wire) => {
			for (let dz = midpoint - 1; dz >= 2; dz--) {
				wire.add([0, 0, dz]);
			}
			wire.add([0, -1, 1]);
			wire.add([0, -2, 1], null);
		});
	}

	private recurringPlayButton() {
		this.setOffset([0, 0, 0], Block.Button);
		this.setOffset([0, -1, 0], Block.Generic);
		this.setOffset([0, -1, 1], Block.Redstone(Direction.fromCoords(0, 1)));
		this.setOffset([0, -2, 1], Block.Generic);
	}
}
