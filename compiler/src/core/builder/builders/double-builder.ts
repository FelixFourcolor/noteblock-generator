import type { Slice } from "#core/assembler/@";
import { Block } from "../block.js";
import { Builder } from "./builder.js";

export class DoubleBuilder extends Builder<"double"> {
	protected override buildSlice({ delay, levels }: Slice<"double">) {
		const left = { delay, levels: levels.map((pair) => pair?.[0]) };
		const right = { delay, levels: levels.map((pair) => pair?.[1]) };

		this.offset(
			{ dz: (this.size.width - 1) / 2, respectDirection: false },
			(self) => self.buildSingleSlice(right),
		);
		this.buildSingleSlice(left);
	}

	protected override buildWalkSpace() {
		const { height, width, length } = this.size;
		const midpoint = (width - 1) / 2;

		for (let x = 0; x < length - 1; x++) {
			this.set([x, height - 3, midpoint], "glass");
			this.set([x, height - 2, midpoint], "air");
			this.set([x, height - 1, midpoint], "air");
		}
	}

	protected override buildPlayButton(index: number) {
		const isFirst = index === 0;
		const isLeftSide = index % 2 === 0;
		const isRightSide = !isLeftSide;

		const { height, width } = this.size;
		const midpoint = (width - 1) / 2;
		const junction = Math.ceil(midpoint / 2);

		const cursor = isLeftSide
			? this.cursor.at({ y: height - 2 }).offset({ dz: -2 })
			: this.cursor.at({ y: height - 2, z: midpoint - 1 }).flipDirection();

		this.withCursor(cursor, (self) => {
			// left connector
			const zLeft = isLeftSide ? 1 : 0;
			self.useWireOffset((wire) => {
				for (let dz = junction - 1; dz > zLeft; dz--) {
					wire.add([0, 0, dz]);
				}
				wire.add([0, -1, zLeft]);
				wire.add([0, -2, zLeft], null);
			});

			// right connector
			const zRight = isRightSide ? midpoint : midpoint + 1;
			self.useWireOffset((wire) => {
				for (let dz = junction + 1; dz < zRight; dz++) {
					wire.add([0, 0, dz]);
				}
				wire.add([0, -1, zRight]);
				wire.add([0, -2, zRight], null);
			});

			// button
			if (isFirst) {
				self.setOffset([0, 0, junction], Block.Generic);
				self.useWireOffset((wire) => {
					for (let dz = midpoint; dz >= junction; dz--) {
						wire.add([-2, 0, dz]);
					}
					wire.add([-1, 0, junction], "repeater");
				});
				self.setOffset([-2, 0, midpoint], Block.Button);
			} else {
				self.setOffset([0, 0, junction], Block.Button);
				self.setOffset([0, -1, junction], "glass");
			}
		});
	}
}
