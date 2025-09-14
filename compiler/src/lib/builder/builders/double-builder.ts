import type { Slice } from "#lib/assembler/@";
import { Block } from "../block.js";
import { Builder } from "./builder.js";

export class DoubleBuilder extends Builder<"double"> {
	protected buildSlice({ delay, levels }: Slice<"double">) {
		const left = { delay, levels: levels.map((pair) => pair?.[0]) };
		const right = { delay, levels: levels.map((pair) => pair?.[1]) };

		this.withCursor(
			this.cursor.offset({
				dz: (this.size.width + 1) / 2,
				respectDirection: false,
			}),
			(self) => self.buildSingleSlice(right),
		);
		this.buildSingleSlice(left);
	}

	protected buildPlayButton() {
		const { height, width } = this.size;
		const cursor = this.cursor.at({ y: height - 2 }).offset({ dz: -2 });

		this.withCursor(cursor, (self) => {
			const midpoint = Math.ceil(width / 2);
			const junction = Math.ceil(midpoint / 2);

			// left connector
			self.useWireOffset((wire) => {
				for (let dz = junction - 1; dz >= 2; dz--) {
					wire.add([0, 0, dz]);
				}
				wire.add([0, -1, 1]);
				wire.add([0, -2, 2], null);
			});
			// right connector
			self.useWireOffset((wire) => {
				for (let dz = junction + 1; dz <= midpoint; dz++) {
					wire.add([0, 0, dz]);
				}
				wire.add([0, -1, midpoint + 1]);
				wire.add([0, -2, midpoint + 2], null);
			});

			if (this.hasPrevious) {
				self.setOffset([0, 0, junction], Block.Button);
			} else {
				self.setOffset([0, 0, junction], Block.Generic);
				self.useWireOffset((wire) => {
					for (let dz = midpoint - 1; dz >= junction; dz--) {
						wire.add([-2, 0, dz]);
					}
					wire.add([-1, 0, junction], "repeater");
				});
			}
		});
	}
}
