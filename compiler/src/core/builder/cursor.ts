import type { Coord } from "./block-placer.js";
import { Direction } from "./direction.js";

export class Cursor {
	constructor(
		private x = 0,
		private y = 0,
		private z = 0,
		private zSign: 1 | -1 = 1,
	) {}

	get direction() {
		return Direction.fromCoords(0, this.zSign);
	}

	at({ x = this.x, y = this.y, z = this.z }): Cursor {
		return new Cursor(x, y, z, this.zSign);
	}

	getOffset({ dx = 0, dy = 0, dz = 0, respectDirection = true }): Coord {
		const newX = this.x + dx;
		const newY = this.y + dy;
		const newZ = this.z + dz * (respectDirection ? this.zSign : 1);
		return [newX, newY, newZ];
	}

	offset({ dx = 0, dy = 0, dz = 0, respectDirection = true }): Cursor {
		const [newX, newY, newZ] = this.getOffset({ dx, dy, dz, respectDirection });
		return this.at({ x: newX, y: newY, z: newZ });
	}

	flipDirection(): this {
		this.zSign *= -1;
		return this;
	}

	move({ dx = 0, dy = 0, dz = 0, respectDirection = true }): this {
		const [newX, newY, newZ] = this.getOffset({ dx, dy, dz, respectDirection });
		this.x = newX;
		this.y = newY;
		this.z = newZ;
		return this;
	}
}
