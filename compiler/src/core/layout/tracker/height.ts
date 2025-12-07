export class HeightTracker {
	minLevel = Number.MAX_SAFE_INTEGER;
	maxLevel = Number.MIN_SAFE_INTEGER;

	get height() {
		return Math.max(0, this.maxLevel - this.minLevel + 1);
	}

	registerLevel = (level: number) => {
		if (level < this.minLevel) {
			this.minLevel = level;
		}
		if (level > this.maxLevel) {
			this.maxLevel = level;
		}
	};
}
