import type { Compare } from "ts-arithmetic";

export enum Direction {
	north,
	south,
	east,
	west,
}

export namespace Direction {
	const coords = [
		[0, -1], // north
		[0, 1], //  south
		[1, 0], //  east
		[-1, 0], // west
	] as const;

	export function get(dir: Direction) {
		return coords[dir]!;
	}

	export function name(direction: Direction) {
		return Direction[direction] as "north" | "south" | "east" | "west";
	}

	export function revert(direction: Direction): Direction {
		switch (direction) {
			case Direction.north:
				return Direction.south;
			case Direction.south:
				return Direction.north;
			case Direction.east:
				return Direction.west;
			case Direction.west:
				return Direction.east;
		}
	}

	type DirectionOf<X extends number, Z extends number> = X extends 0
		? Z extends 0
			? undefined
			: Compare<Z, 0> extends -1
				? Direction.north
				: Compare<Z, 0> extends 1
					? Direction.south
					: Direction.north | Direction.south
		: Z extends 0
			? Compare<X, 0> extends -1
				? Direction.west
				: Compare<X, 0> extends 1
					? Direction.east
					: Direction.west | Direction.east
			: Direction | undefined;

	export function fromCoords<X extends number, Z extends number>(
		x: X,
		z: Z,
	): DirectionOf<X, Z>;
	export function fromCoords(x: number, z: number): Direction | undefined {
		if (!x && !z) {
			return undefined;
		}
		if (!x) {
			return z < 0 ? Direction.north : Direction.south;
		}
		if (!z) {
			return x < 0 ? Direction.west : Direction.east;
		}
	}
}
